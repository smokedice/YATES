from multiprocessing import Process
from Network.SSH import SSHClient, Status
from Utils.Logging import LogManager
import sys, time

class RecoveryWorker(Process):
    def __init__(self, peer, rebootAttempts = 1, removeLock = False):
        self.peer = peer
        self.removeLock = removeLock
        self.stages = [self.__rebootSSH, self.__rebootPWR] * rebootAttempts
        self.logger = LogManager().getLogger('RecoveryWorker-%s' % peer.ipAddr)
        Process.__init__(self, target = self.__restartPeer)
        self.start()

    def __restartPeer(self):
        """
        Reboot a given peer
        @param peer: Peer to reboot
        @return: Process.exitcode will be 0 if successful else -99
        """
        for stage in self.stages:
            try: stage()
            except KeyError, e:
                self.logger.warn("Ignoring stage %s, invalid config: %s"
                    % (stage.__name__, e))

            time.sleep(10)
        sys.exit(-99)

    def __rebootSSH(self):
        """ Reboot the peer using the SSH service """
        if self.removeLock:
            cmd =  'touch %s/unlock; ' % self.peer.config['tmpdir']
        else: cmd = ''

        sshClient = SSHClient(
            self.peer.config['user'],
            self.peer.config['password'],
            self.peer.ipAddr,
            '%s%s' % (cmd, self.peer.config['rebootcmd']),
        )

        sshClient.join()
        if sshClient.exitcode == Status.CLOSED:
            sys.exit(0)
            return

        self.logger.warn('Cannot reboot peer using SSH (%s)' 
            %(sshClient.exitcode))

    def __rebootPWR(self):
        """ Reboot the peer using a power controller """
        # TODO: define PWR type (SSH, Telnet, etc)
        sshClient = SSHClient(
            self.peer.config['pwr_user'],
            self.peer.config['pwr_password'],
            self.peer.config['pwr_ip'],
            self.peer.config['pwr_rebootCmd'],
            port = 22,
            exitCmd = self.peer.config['pwr_exitCmd']
        )

        sshClient.join()
        if sshClient.exitcode == Status.CLOSED:
            sys.exit(0)
            return

        self.logger.warn('Cannot reboot peer %s(%s) using the Power Controller (%d)' 
            %(self.peer.ipAddr, self.peer.macAddr, sshClient.exitcode))
