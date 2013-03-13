from yates.Utils.Configuration import ConfigurationManager
from yates.Utils.Network import getIPAddressByInterface

from multiprocessing.process import Process
from multiprocessing.queues import Queue
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
import thread, time
from Queue import Empty
from threading import RLock

class HolaListener(DatagramProtocol):
    def __init__(self, queue):
        self.queue = queue

    def startProtocol(self):
        """ Called when transport is connected """
        self.transport.setTTL(5)
        self.transport.joinGroup('224.6.6.6')

    def datagramReceived(self, data, (host, port)):
        macAddr, randomBits = data.split(':', 1)
        self.queue.put((host, macAddr, randomBits))

class UDPServer(Process):
    def __init__(self, queue):
        Process.__init__(self, name = "UDPServer")
        #self.daemon = True
        self.queue = queue
        self.shutdownQueue = Queue()
        self.start()

    def __checkShutdown(self):
        try:
            self.shutdownQueue.get(block = False)
        except Empty, _e:
            return self.reactor.callLater(1, self.__checkShutdown)
        self.shutdownQueue.close()

        if self.reactor.running:
            self.reactor.stop()
            self.queue.close()

    def run(self):
        from twisted.internet import reactor
        from twisted.python import log

        reactor.listenMulticast(8005,
            HolaListener(self.queue),
            listenMultiple = True)

        self.reactor = reactor
        reactor.callLater(1, self.__checkShutdown)
        log.defaultObserver.stop()
        reactor.run()

    def getHeartBeats(self, count = 2):
        """
        Retrieve a unique set of heartbeats
        @param count: Count of heartbeats to get
        @return: List of heartbeats
        """
        heartBeats = []
        history = set()

        i = 0
        while i < count:
            try:
                data = self.queue.get(timeout=0.1)
                if str(data) in history: continue
                history.add(str(data))
                heartBeats.append(data)
                i += 1
            except Empty: break
        return list(heartBeats)

    def shutdown(self):
        if not self.shutdownQueue._closed:
            self.shutdownQueue.put(None)
            self.shutdownQueue.close()
