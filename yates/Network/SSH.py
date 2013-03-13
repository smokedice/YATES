from yates.Utils.Logging import LogManager

import time, sys, subprocess, re
from Queue import Empty
from multiprocessing import Value
from multiprocessing.process import Process
from multiprocessing.queues import Queue

from twisted.conch.ssh import transport, userauth, connection, channel, common
from twisted.internet import defer, protocol, reactor, task
from twisted.python import log

class Status(object):
    CLOSED = 0
    SENT = -1
    CHANNEL = -2
    STARTED = -3
    PASSWORD = -4
    SECURED = -5
    VERIFIED = -6
    FAILURE = -7

class ClientTransport(transport.SSHClientTransport):
    def __init__(self, details):
        self.details = details

    def verifyHostKey(self, hostKey, fingerprint):
        self.details.status = Status.VERIFIED
        return defer.succeed(1)

    def connectionSecure(self):
        self.requestService(
            ClientUserAuth(self.details,
                ClientConnection(self.details)))
        self.details.status = Status.SECURED

    def connectionLost(self, reason):
        if self.details.status == Status.SENT:
            self.details.status = Status.CLOSED
        if reactor.running: reactor.stop()

class SSHFactory(protocol.ClientFactory):
    def __init__(self, details):
        self.protocol = ClientTransport
        self.details = details

    def buildProtocol(self, addr):
        p = self.protocol(self.details)
        p.factory = self
        return p

class ClientUserAuth(userauth.SSHUserAuthClient):
    def __init__(self, details, options):
        userauth.SSHUserAuthClient.__init__(self, details.username, options)
        self.details = details

    def getPassword(self, prompt = None):
        self.details.status = Status.PASSWORD
        return defer.succeed(self.details.password)

class ClientConnection(connection.SSHConnection):
    def __init__(self, details):
        connection.SSHConnection.__init__(self)
        self.details = details

    def serviceStarted(self):
        self.openChannel(CatChannel(self.details, conn = self))
        self.details.status = Status.STARTED

class CatChannel(channel.SSHChannel):
    name = 'session'

    def __init__(self, details, localWindow = 0, localMaxPacket = 0,
        remoteWindow = 0, remoteMaxPacket = 0,
        conn = None, data = None, avatar = None):

        channel.SSHChannel.__init__(self, localWindow = localWindow,
            localMaxPacket = localMaxPacket, remoteWindow = remoteWindow,
            remoteMaxPacket = remoteMaxPacket, conn = conn, data = data,
            avatar = avatar)
        self.details = details

    def channelOpen(self, data):
        self.details.msg = ""
        self.details.status = Status.CHANNEL
        cmd = str("; ".join([ x for x in self.details.cmdsToSend ]))
        d = self.conn.sendRequest(self, 'exec',
            common.NS(cmd), wantReply = 1)
        d.addCallback(self.dataSent)

    def dataSent(self, d):
        self.details.status = Status.SENT
        for cmd in self.details.cmdsToSend:
            self.write("%s\r" % str(cmd))
        self.details.cmdsSend = True

    def dataReceived(self, data):
        self.details.queue.put(data)
        self.receivedData = time.time()
        reactor.callLater(2, self.close)

    def close(self):
        if time.time() - 2 > self.receivedData:
            try: self.write("%s\r" % self.details.exitCmd)
            except: pass
            self.loseConnection()

    def closed(self):
        if reactor.running: reactor.stop()
        self.details.status = Status.CLOSED

class SSHClient(Process):
    TIMEOUT = 10
    PING_RECEIVED = re.compile("1 received")

    def __init__(self, username, password, host, cmdsToSend, port = 22, exitCmd = "exit", timeout = None):
        Process.__init__(self, name = "SSHClient")

        self.logger = LogManager().getLogger('SSHClient-%s' % host)
        self.username = username
        self.password = password
        self.host = host
        self.port = int(port)
        self.cmdsToSend = cmdsToSend if isinstance(cmdsToSend, list) else [cmdsToSend]
        self.exitCmd = exitCmd

        self.queue = Queue()
        self.msg = ""
        self.status = Status.FAILURE
        self.startTime = Value('d', 0.0)
        self.endTime = Value('d', 0.0)
        self.timeout = timeout or SSHClient.TIMEOUT
        self.cmdsSend = False
        self.start()

    def isFinished(self):
        """ True if the process has finished """
        return not self.is_alive()

    def updateOutput(self):
        """
        Update the msg to include the latest
        output from the given commands
        """
        try:
            while True:
                msg = self.queue.get(timeout = 0.5)
                self.msg += msg
        except Empty: pass
        except IOError: pass

        if self.isFinished():
            self.queue.close()
        return self.msg

    def run(self):
        factory = SSHFactory(self)
        factory.protocol = ClientTransport
        reactor.connectTCP(self.host, self.port, factory)

        self.startTime.value = time.time()
        check = task.LoopingCall(self.__ping)
        check.start(2.0)
        reactor.callLater(self.timeout, self.__timeout)
        log.defaultObserver.stop()
        reactor.run()
        self.endTime.value = time.time()
        self.queue.close()
        sys.exit(self.status)

    def __timeout(self):
        """ Timeout checker """
        if self.status != Status.FAILURE:
            return

        self.logger.error('Connection timeout to peer %s:%s'
            %(self.host, self.port))
        reactor.stop()

    def __ping(self):
        with open('/dev/null') as null:
            ping = subprocess.Popen(["ping", "-c1", "-W1", self.host],
                stdout = null, stderr = null)
            ping.wait()

        if ping.returncode != 0 and reactor.running:
            if self.cmdsSend == False:
                self.status = Status.FAILURE
            reactor.stop()

    def cleanup(self):
        self.queue.close()

    def shutdown(self):
        """ Terminate the SSH process """
        self.terminate()
        self.join()
        self.endTime.value = time.time()
