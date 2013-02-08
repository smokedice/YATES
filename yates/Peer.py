from Domain.States import PeerState, TestState
from Utils.Logging import LogManager
from Utils.Network import getIPAddressByInterface, syncGetHTTPFile
from Utils.Envcat import EnvCat, envcatRequest
from Utils.Configuration import ConfigurationManager
from Network.SSH import SSHClient
from RecoveryWorker import RecoveryWorker
from Results.ResultStatus import ResultDefiner
from Results.PeerStatus import ReactionDefiner
from events import get_event_handler

import tempfile, urllib2, os, time
from subprocess import Popen

class Peer(object):
    HEARTBEAT_TIMEOUT = 300
    DEATH_TIMEOUT = 600
    TEST_TIMEOUT = 60
    TEST_GRACE = 3

    DEAD_STATES = [PeerState.UNRESPONSIVE(), PeerState.DEAD()]
    DONE_STATES = [PeerState.ACTIVE(), PeerState.DEAD()]
    REBOOT_STATES = [PeerState.REBOOTING(), PeerState.DEAD()]
    LOCKED_STATES = [PeerState.LOCKED(), PeerState.PENDING()]
    REQUIRED_CONF = ['user', 'password', 'tmpdir', 'envserver', 'envserverport', 'rebootcmd']
    
    IGNORED_PEER_EVENT = get_event_handler('ignored_peer')
    NEW_PEER_EVENT = get_event_handler('new_peer')
    PEER_STATE_CHANGE_EVENT = get_event_handler('peer_state_change')
    PEER_STAGE_CHANGE_EVENT= get_event_handler('peer_stage_change')
    TEST_RESULT_EVENT = get_event_handler('test_result')
    PEER_SLEEPING_EVENT = get_event_handler('peer_sleeping')

    @staticmethod
    def createPeer(ipAddr, port, macAddr, randomBits, testDistributor, resultWorker):
        config = ConfigurationManager().getConfiguration('routes').configuration
        routes = config.route if isinstance(config.route, list) else [config.route]

        for route in routes:
            if route.macAddr.PCDATA != macAddr: continue
            if route.enabled == 'false': continue
            return Peer(ipAddr, port, macAddr, randomBits, testDistributor, resultWorker)
        Peer.IGNORED_PEER_EVENT(ipAddr, port, macAddr, randomBits)
 
    def __init__(self, ipAddr, port, macAddr, randomBits, testDistributor, resultWorker):
        self.STAGES = [
            self.__retrieveConfigFile,
            self.__processConfigFile,
            self.__checkForLockedBox,
            self.__initRebootPeer,
            self.__syncCode,
            self.__executeTest,
            self.__archiveLogFiles,
            self.__retrieveLogFiles,
            self.__defineResults,
            self.__reportResults,
            self.__reaction,
            self.__gracePeriod,
            self.__postRebootPeer,
        ]

        self.recoverIndex = self.STAGES.index(self.__archiveLogFiles)
        self.graceIndex = self.STAGES.index(self.__gracePeriod)
        self.STAG_LEN = len(self.STAGES)
    
        self.testDistributor = testDistributor
        self.resultWorker = resultWorker

        self.config = {}
        self.ipAddr = ipAddr
        self.macAddr = macAddr
        self.randomBits = randomBits
        self.capabilities = ''
        self.gracePeriod = self.recoveries = 0
        self.timeJoined = time.time()
        self.envServer = ''
        self.envServerPort = 0

        execConf = ConfigurationManager().getConfiguration('execution').configuration
        resConf = ConfigurationManager().getConfiguration('resultWorker').configuration

        self.customLogFilters = resConf.customLogFilters.customLogFilter \
            if hasattr(resConf.customLogFilters, 'customLogFilter') else []
        self.customLogFilters = self.customLogFilters  \
            if isinstance(self.customLogFilters, list) else [self.customLogFilters]

        self.logger = LogManager().getLogger('Peer-%s' % self.macAddr)
        self.hostIP = getIPAddressByInterface()
        self.masterHTTPLoc = 'http://%s:%s/' % (self.hostIP, port)
        self.httpLoc = 'http://%s:5005/' % ipAddr
        self.tmpDir = os.environ['TAS_TMP']
        self.peerDir = '%s/peer-%s' % (self.tmpDir, self.macAddr)
        self.resultLoc = '%s/results' % self.peerDir

        if not os.path.exists(self.resultLoc):
            os.makedirs(self.resultLoc)

        execution = ConfigurationManager()\
            .getConfiguration('execution').configuration
        self.initReboot = execution.rebootNewBoxes.PCDATA == 'true'
        self.postReboot = execution.rebootPerTest.PCDATA == 'true'
        self.state = PeerState.ACTIVE()
        self.__changeState(PeerState.PENDING())
        self.stage = 0
 
        self.lastHeartBeat = time.time()
        self.currentTest = self.testTimeout = None
        self.failureCodes = []
        self.processResults = []
        self.longRunningProcesses = []

        Peer.NEW_PEER_EVENT(self)

    def __retrieveConfigFile(self):
        """ Retrieve the configuration file from the peer """
        if not os.path.exists(self.peerDir):
            os.makedirs(self.peerDir)

        self.longRunningProcesses.append(syncGetHTTPFile(
            '%sconfig' % self.httpLoc, self.peerDir))

    def __processConfigFile(self):
        """ Process the configuration file as a key/value pair """
        configLoc = '%s/config' % self.peerDir
        if not os.path.exists(configLoc):
            self.logger.warn('Could not find a configuration file')
            return self.__changeState(PeerState.DEAD())

        with open(configLoc, 'r') as lf:
            for line in lf.readlines():
                key, value = line.strip().split('=', 1)
                self.config[key.lower()] = value

        self.envServer = self.config['envserver'].strip()
        self.envServerPort = self.config['envserverport'].strip()
        if self.envServerPort.isdigit():
            self.envServerPort = int(self.envServerPort)

        if self.config['rebootcmd'] == '':
            self.postReboot = self.initReboot = False

        self.capabilities = envcatRequest(self.envServer,
            self.envServerPort, 'capabilities')

        if self.__configIsMissingKeys():
            return self.__changeState(PeerState.DEAD(), 'Invalid config')

        cmd = 'mkdir -p %(T)s; cd %(T)s; if [ ! -f locked ]; then echo "%(I)s" > locked; sleep 2; fi; ' \
              'if [ "%(I)s" != `cat locked` ]; then echo `cat locked`; else echo "UNLOCKED"; fi;' \
              % { 'T' : self.config['tmpdir'], 'I' : self.hostIP }

        self.longRunningProcesses.append(SSHClient(self.config['user'],
            self.config['password'], self.ipAddr, cmd))

    def __checkForLockedBox(self):
        """ Check for a locked box """
        output = self.processResults[0].updateOutput().strip()

        if 'UNLOCKED' in output:
            self.lastHeartBeat = time.time()
        elif not self.testDistributor.peekTest(self):
            self.stage = 0
            self.__changeState(PeerState.ACTIVE())
        else:
            self.gracePeriod = 5
            self.stage = self.graceIndex - 1
            self.__changeState(PeerState.LOCKED(), 
                'current user %s' % output)

    def __initRebootPeer(self):
        """ Pre testing reboot if required """
        if not self.initReboot: return False
        self.initReboot = False

        self.__changeState(PeerState.REBOOTING())
        self.longRunningProcesses.append(RecoveryWorker(self))

    def __syncCode(self):
        """ Sync the source code the the peer """
        self.status = self.__changeState(PeerState.SYNC_CODE())
        cmd = 'mkdir -p %(T)s; for x in `ls %(T)s | grep -vE "(config|locked|scripts.%(J)s.tar.gz)"`; do rm -rf %(T)s/$x; done; ' \
          'if [ ! -f %(T)s/scripts.%(J)s.tar.gz ]; then wget %(H)sscripts.tar.gz -O %(T)s/scripts.%(J)s.tar.gz -q; fi; ' \
          'tar -xzf %(T)s/scripts.%(J)s.tar.gz -C %(T)s' %{'T' : self.config['tmpdir'], 'J' : self.timeJoined, 'H' : self.masterHTTPLoc}

        self.longRunningProcesses.append(SSHClient(
            self.config['user'], self.config['password'],
            self.ipAddr, cmd))

    def __executeTest(self):
        """ Execute a test script on the peer """
        test = self.testDistributor.getTest(self)
        if test == None:
            self.stage = 0
            self.longRunningProcesses.append(self.__unlockBox())
            return self.__changeState(PeerState.ACTIVE())

        test.testTimeout += Peer.TEST_GRACE
        self.__changeState(PeerState.TESTING(), 'while running test %s' % test.testId)
        self.currentTest = test

        cmd = 'cd %s; bash -x %s >execution.log 2>&1' %(self.config['tmpdir'], self.currentTest.getExecutionString())
        self.longRunningProcesses.append(SSHClient(
            self.config['user'], self.config['password'],
            self.ipAddr, cmd))

        self.currentTest.startTime = time.time()

    def __archiveLogFiles(self):
        """ Archive logs and cleanup on the peer """
        endTime = time.time()
        startTime = self.currentTest.startTime
        if len(self.processResults) > 0:
            endTime = self.processResults[0].endTime.value
            startTime = self.processResults[0].startTime.value
        self.currentTest.duration = endTime - startTime
        self.__changeState(PeerState.SYNC_LOGS())
        
        cmd =''
        for customLogFilter in self.customLogFilters:
            cmd +='cp -r %s %s/logs; ' % (customLogFilter.PCDATA, self.config['tmpdir'])
        cmd += 'cd %s/logs; tar -czf ../logs.tar.gz *;' % self.config['tmpdir']

        self.longRunningProcesses.append(SSHClient(
            self.config['user'], self.config['password'],
            self.ipAddr, cmd))

    def __retrieveLogFiles(self):
        """ Retrieve the log files from the peer """
        self.lastResultLoc = "%s-%s-%s" %(self.resultLoc, time.time(), self.currentTest.testId)
        os.makedirs(self.lastResultLoc)

        self.longRunningProcesses.append(syncGetHTTPFile(
            '%slogs.tar.gz' % self.httpLoc, self.lastResultLoc, True))
        self.longRunningProcesses.append(EnvCat(self.envServer, self.envServerPort,
            '%s/envlog.txt' % self.lastResultLoc, 'getlogs'))

    def __defineResults(self):
        """ Define the result for the test result """
        self.lastResultFiles = [ os.path.join(self.lastResultLoc, fileName)
            for fileName in os.listdir(self.lastResultLoc) ]

        self.longRunningProcesses.append(ResultDefiner(
            self.lastResultFiles, self.currentTest))

    def __reportResults(self):
        """ From the log files define a result """
        testState, errorMsg = self.processResults[0].getResult()
        self.currentTest.state = testState
        self.currentTest.error = errorMsg
        Peer.TEST_RESULT_EVENT(self.currentTest, self.lastResultFiles, self)
        #TODO: replace me, self.resultWorker.report(self.currentTest, self.lastResultFiles, self)

        self.longRunningProcesses.append(
            ReactionDefiner(self.lastResultFiles, self.currentTest))

    def __reaction(self):
        """ React appon the current test results """
        peerState, gracePeriod = self.processResults[0].getResult()
        self.__changeState(peerState)
        self.gracePeriod = gracePeriod
        self.currentTest = None

    def __gracePeriod(self):
        """ Allow for a grace period """
        if self.gracePeriod == 0: return False
        Peer.PEER_SLEEPING_EVENT(self)
        self.longRunningProcesses.append(Popen(
            'sleep %d' % self.gracePeriod, shell = True))
        self.gracePeriod = 0

    def __postRebootPeer(self):
        """ Pre testing reboot if required """
        if not self.postReboot or self.state in Peer.LOCKED_STATES:
            return False

        self.initReboot = False
        self.__changeState(PeerState.REBOOTING())
        self.longRunningProcesses.append(RecoveryWorker(
            self, removeLock = True))

    def __changeState(self, state, comment = None):
        """ Change the peer state and report """
        if self.state == state or not state:
            return

        self.state = state
        Peer.PEER_STATE_CHANGE_EVENT(self, comment)

    def __hasDied(self, heartBeatFelt):
        """
        States if the peer hasn't been sending heartbeats.
        The state will be set to either DEAD or UNRESPONSIVE
        depending on how much time has passed.
        @return True if heartbeat timeout has not occured else false
        """
        now = time.time()
        timePassed = now - self.lastHeartBeat

        if timePassed > Peer.DEATH_TIMEOUT \
        and self.state != PeerState.DEAD():
            self.__changeState(PeerState.DEAD())

        elif timePassed > Peer.HEARTBEAT_TIMEOUT \
        and self.state not in Peer.DEAD_STATES:
            self.__changeState(PeerState.UNRESPONSIVE(), 'within stage %d' % self.stage)

        else:
            if heartBeatFelt: self.lastHeartBeat = time.time()
            return False

        return True

    def checkState(self, heartBeatFelt):
        """
        Check the overall state
        @param heartBeat: True if a heart was felt else False
        @return: Result, State. Either can be None if they have not changed
        """
        self.failureCodes = [ p for p
            in self.longRunningProcesses
            if self.__getExitCode(p) not in [None, 0]
            and not isinstance(p, RecoveryWorker) ] \
        + self.failureCodes

        self.processResults = [ p for p
            in self.longRunningProcesses
            if not self.__isAlive(p) 
            and not isinstance(p, RecoveryWorker) ] \
        + self.processResults

        self.longRunningProcesses = [ p for p
            in self.longRunningProcesses
            if self.__isAlive(p) ]

        # Box doesn't belong to us yet. Try again
        if len(self.failureCodes) > 0 and self.state == PeerState.PENDING():
            self.gracePeriod = 5
            self.stage = self.graceIndex
            self.__clearProcessHistory()

        if self.state not in Peer.LOCKED_STATES:
            hasDied = self.__hasDied(heartBeatFelt)
            if len(self.longRunningProcesses) > 0: return

            if len(self.failureCodes) > 0 or hasDied:
                hasConfig = not any(x not in self.config.keys() for x in Peer.REQUIRED_CONF)
                if self.state not in Peer.DEAD_STATES:
                    objNames = ','.join([ x.__class__.__name__ for x in self.failureCodes])
                    funcName = self.STAGES[self.stage].im_func.func_name
                    self.__changeState(PeerState.UNRESPONSIVE(), 'on stage %s, %s' % (funcName, objNames))
                if hasConfig and self.recoveries < 5:
                    self.longRunningProcesses.append(RecoveryWorker(self))
                    self.recoveries += 1
                return

            if self.state == PeerState.TESTING() \
            and time.time() - self.currentTest.startTime > self.currentTest.testTimeout \
            and self.currentTest.state != TestState.TIMEOUT():
                self.currentTest.state = TestState.TIMEOUT()
                for process in self.longRunningProcesses + self.processResults:
                    if hasattr(process, 'shutdown'): process.shutdown()

        if len(self.longRunningProcesses) > 0 or \
        self.state in Peer.REBOOT_STATES + Peer.DONE_STATES: 
            return # Still running processes # TODO: timeout?

        if self.STAGES[self.stage]() == False:
           # Go to the next stage if asked to skip
           self.__incStage()
           self.checkState(heartBeatFelt)
        else:
            self.recoveries = 0
            self.__incStage()
            self.__clearProcessHistory()

    def __incStage(self):
        """ Increment the current stage """
        if self.state == PeerState.ACTIVE(): return
        self.stage = (self.stage + 1) * (self.stage + 1 < self.STAG_LEN)
        Peer.PEER_STAGE_CHANGE_EVENT(self)

    def __getExitCode(self, process):
        """
        Returns the exit code from a process
        @param process: Popen or Process object
        @return: exit code of process
        """
        if isinstance(process, Popen):
            return process.poll()
        return process.exitcode

    def __isAlive(self, process):
        """ 
        Returns true if the process or Popen is
        still executing code else false
        @param process: Process or Popen
        @return True if executing else false
        """
        if isinstance(process, Popen):
            return process.poll() == None
        return process.is_alive()
 
    def __killAllProcesses(self):
        """ Kill all running processes """
        for process in self.longRunningProcesses:
            try: process.terminate()
            except OSError: pass

        self.longRunningProcesses = []
        self.__clearProcessHistory()       

    def __clearProcessHistory(self):
        """ Clear all process history """
        processes = self.failureCodes + self.processResults
        for process in processes:
            if not hasattr(process, 'cleanup'):
                continue
            process.cleanup()

        self.failureCodes = []
        self.processResults = []

    def checkIP(self, ipAddr, randomBits):
        """
        Check if the IP address has changed
        @param ipAddr: New IP address
        """
        # IP address has changed
        if ipAddr != self.ipAddr:
            self.logger.warn('IP address for peer %s has changed to %s from %s!'
                %(self.macAddr, ipAddr, self.ipAddr))
            # TODO: restart SSH ? What does this mean? Recovery?

        # Box rebooted randomly
        elif randomBits != self.randomBits and self.currentTest:
            self.logger.warn('Peer (%s,%s) has rebooted! Random bits have changed: %s - %s'
                %(self.ipAddr, self.macAddr, self.randomBits, randomBits))

            self.__changeState(PeerState.RECOVER_LOGS())
            self.__killAllProcesses()
            self.stage = self.recoverIndex
            self.currentTest.state = TestState.CRASH()
            self.lastHeartBeat = time.time()
 
        # Expected and controlled rebooted
        if self.randomBits != randomBits and self.state in Peer.REBOOT_STATES:
            self.__changeState(PeerState.PENDING())

        self.ipAddr = ipAddr
        self.randomBits = randomBits

    def __configIsMissingKeys(self):
        """ Configuration is missing keys """
        return any(k not in self.config.keys() for k in Peer.REQUIRED_CONF)

    def __unlockBox(self):
        """ Remove the lock from the box and reboot """
        if self.__configIsMissingKeys(): return

        return SSHClient(self.config['user'], self.config['password'],
          self.ipAddr, 'if [ "`cat %(T)s/locked`" == "%(H)s" ]; then touch %(T)s/unlock; %(R)s; fi'
          % { 'H': self.hostIP, 'T': self.config['tmpdir'], 'R': self.config['rebootcmd'] },
          timeout = 2)

    def shutdown(self):
        """ Shutdown all operations that are related to this peer """
        self.__killAllProcesses()
        if self.currentTest and self.state == PeerState.DEAD(): 
            self.currentTest.state = TestState.DEADBOX()
            self.resultWorker.report(self.currentTest, [], self)
            self.currentTest = None

        processes = [ EnvCat(self.envServer,
            self.envServerPort, '/dev/null', 'play') ]

        if self.state not in Peer.LOCKED_STATES:
            processes.append(self.__unlockBox())
        return processes

    def isDone(self):
        """
        State if the peer has finished all required work
        @return: True if all work has been completed else false
        """
        return self.state in Peer.DONE_STATES
