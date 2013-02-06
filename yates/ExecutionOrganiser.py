from Peer import Peer
from Network.UDP import UDPServer
from Utils.Configuration import ConfigurationManager 
from Utils.Logging import LogManager
from TestDistribution.TestDistributor import TestDistributor
from TestGather.TestGatherManager import TestGatherManager
from Results.ResultWorker import ResultWorker

import os, subprocess, signal, tempfile, time, sys, traceback, shutil, threading, multiprocessing
from multiprocessing import Queue

class ExecutionOrganiser(object):
    def __init__(self, version):
        self.udpQueue = Queue()
        self.udpServer = UDPServer(self.udpQueue)
        self.tmpDir = tempfile.mkdtemp('tmpTAS')

        os.environ['TAS_TMP'] = self.tmpDir
        os.environ['TAS_VERSION'] = version

        self.logger = LogManager().getLogger('Main')
        self.peers = {}
        self.root = os.getcwd()
        os.chdir(self.tmpDir)

        self.httpServer = subprocess.Popen(['python', '-m', 'SimpleHTTPServer', '0'],
            stdout = open('/dev/null', 'w'), stderr = open('/dev/null', 'w'),
            preexec_fn = os.setsid)
        time.sleep(1)

        pid = str(self.httpServer.pid)
        httpPort = subprocess.Popen("netstat -tulpn | awk ' /"+ pid +"\/python/ { gsub(/^[^:]+:/, \"\", $4); print $4 } '",
            shell = True, stdout = subprocess.PIPE, stderr = open('/dev/null', 'w'))
        self.httpPort = int(httpPort.stdout.readline().strip())

        os.chdir(self.root)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        self.shutdownLock =  threading.Lock()
        self.closed = False

    def _process(self):
        """ Monitor the overall progress and exchange data """
        heartBeats = self.udpServer.getHeartBeats(self.udpQueue.qsize())
        self.__processHeartBeats(heartBeats)
        if len(self.peers.keys()) == 0: return False
        
        if all(self.__processPeers(heartBeats)):
            toContinue = self.testDistributor.continueIterations()
            if not toContinue: return True
            self.resultWorker.reportIteration(self.testDistributor.currentIteration)
            self.peers = {}
            return False
        return False

    def __processPeers(self, heartbeats):
        """ Process all peer states """
        states = []
        for macAddr, peer in self.peers.items():
            hasHeartBeat = any(m == macAddr for h, m, r in heartbeats)
            peer.checkState(hasHeartBeat)
            states.append(peer.isDone())
        return states

    def __processHeartBeats(self, heartbeats):
        """ Process all new peer discoveries """
        for ipAddr, macAddr, randomBits in heartbeats:
            if macAddr in self.peers.keys():
                self.peers[macAddr].checkIP(ipAddr, randomBits)
            else:
                peer = Peer.createPeer(ipAddr, self.httpPort, macAddr, randomBits,
                    self.testDistributor, self.resultWorker)
                if peer: self.peers[macAddr] = peer
 
    def _go(self):
        self.testGather = TestGatherManager(self.tmpDir)
        source, description = self.testGather.gatherTests()
        self.testDistributor = TestDistributor(self.peers, source)
        self.resultWorker = ResultWorker(self.testGather.getPackDetails(), source)
   
    def _shutdown(self, *args):
        """ Teardown all components and a graceful shutdown """
        with self.shutdownLock:
            if self.closed: return
            self.closed = True

        self.logger.info('Shutdown called')

        processes = []
        peers = self.peers.values() if hasattr(self, 'peers') else []
        for peer in peers: processes += peer.shutdown()

        while any( process.is_alive() for process in processes if process ):
            time.sleep(1)

        if hasattr(self, 'httpServer'):
            os.killpg(self.httpServer.pid, signal.SIGTERM)
        for component in ['udpServer', 'resultWorker']:
            if not hasattr(self, component): continue
            getattr(self, component).shutdown()

        ConfigurationManager.destroySingleton()
        if os.path.exists(self.tmpDir):
            shutil.rmtree(self.tmpDir)

        os._exit(0)
