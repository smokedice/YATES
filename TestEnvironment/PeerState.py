from Common.CommonSignals.Enums.ActivePeerState import ActivePeerState
from Common.CommonSignals.ExpectReboot import ExpectReboot
from Common.CommonSignals.LogFilesTransfered import LogFilesTransfered
from Common.CommonSignals.FileServiceStateUpdate import FileServiceStateUpdate
from Common.CommonSignals.Enums.FileServiceState import FileServiceState
from Common.SignalExchangeHub.SignalExchangeHub import SignalExchangeHub
from Common.TASUtils.Configuration.ConfigurationManager import ConfigurationManager
from Common.TASUtils.LogManager import LogManager

from Master.Domain.CheckPeerState import CheckPeerState
from Master.Domain.PeerHeartBeat import PeerHeartBeat
from Master.Domain.PeerReboot import PeerReboot
from Master.Domain.PeerRecovery import PeerRecovery
from Master.Domain.PeerTestState import PeerTestState
from Master.Domain.TestCompleted import TestCompleted
from Master.Domain.Test.TestStates import TestState

import threading
import time

# TODO: configure me
# TODO: removed cannot be updated unless user adds peer
# TODO: forced remove, graceful remove

class PeerState(object):
    HEART_BEAT_TIMEOUT = 300
    TESTSTATES = [TestState.DEADBOX(), TestState.SLAVE_CRASH()]
    TEST_TIMEOUT_GRACE = 300 

    def __init__(self, peer, fServiceHost, fServicePort):
        self.logger = LogManager().getLogger(self.__class__.__name__)
        self.peer = peer
        self.beatCounter = 0
        self.fServiceHost = fServiceHost
        self.fServicePort = fServicePort
        self.reset()
        self.sLock = threading.RLock()
        self.__gatherTestLogs = False
        self.waiterThread = None
        self.stime = None
        self.shuttingDown = False

        exc = ConfigurationManager().getConfiguration("execution")
        self.__rebootPeer = exc.configuration.rebootNewBoxes.PCDATA == "true"
        self.REBOOT_PER_TEST = exc.configuration.rebootPerTest.PCDATA == "true"

        SignalExchangeHub().addListener(CheckPeerState.createListener(
            self.__checkState))

        SignalExchangeHub().addListener(PeerHeartBeat.createListener(
            self.__heartBeat, self.peer.macAddress))

        SignalExchangeHub().addListener(PeerTestState.createListener(
            self.__testState, peer.macAddress))

        SignalExchangeHub().addListener(ExpectReboot.createListener(
            self.__expectReboot, namespace = "*.%s" % peer.macAddress))

        SignalExchangeHub().addListener(LogFilesTransfered.createListener(
            self.__logFilesReceived, namespace = "*"))

        SignalExchangeHub().addListener(FileServiceStateUpdate.createListener(
            self.__fileServiceStateUpdate, peer.ipAddress))

    def reset(self):
        """ Reset state to defaults """
        self.__heartBeat()
        self.testStarted = False
        self.testCompletionBefore = -1
        self.currentTest = None
        self.beatCounter = 0

    def __checkState(self):
        """ Check that the current states are all of good order """
        if self.peer.state >= ActivePeerState.PENDING():
            now = time.time()
            if self.peer.state == ActivePeerState.PENDING():
                self.__clarifyTestResult()

            if self.__heartBeatChecker(now):
                self.__testTimeoutChecker(now)
        elif self.peer.state == ActivePeerState.CANNOT_REVIVE():
            self.__markDeath()

    def __clarifyTestResult(self):
        """ Clarify what the state of a box should be after a reboot """
        if self.currentTest:
            if self.currentTest.state == TestState.DEADBOX() or \
            self.currentTest.state != TestState.SLAVE_CRASH():
                self.currentTest.state = TestState.CRASH()

            SignalExchangeHub().propagateSignal(
                TestCompleted(self.peer.macAddress, self.currentTest))
            self.__gatherTestLogs = True

        elif self.peer.state == ActivePeerState.PENDING() and self.__rebootPeer:
            self.__rebootPeer = False
            SignalExchangeHub().propagateSignal(PeerReboot(self.peer))
        elif self.peer.state == ActivePeerState.PENDING():
            self.peer.setState(ActivePeerState.SYNC_CODE())

        if self.__gatherTestLogs:
            jobCleanupSignal = self.currentTest.getCleanupSignal(self.peer, self.fServiceHost, self.fServicePort)
            SignalExchangeHub().propagateSignal(jobCleanupSignal)
            self.__gatherTestLogs = False
            self.currentTest = None
            self.testStarted = False
        self.__heartBeat() # Reset the heartbeats

    def __heartBeat(self):
        """ Receive heart beats for this peer """
        self.heartBeatBefore = self.HEART_BEAT_TIMEOUT + time.time()

    def __testState(self, testcase, signal):
        """
        Receive test states for this peer
        @param testcase: Testcase & it's state
        """
        if testcase.testStage and testcase.state == TestState.NORESLT():
            return # We are already running a multi part test

        if testcase.state == TestState.NORESLT():
            self.peer.setState(ActivePeerState.TESTING())
            self.logsReceived = False
            testcase.peer = self.peer
            self.peer.addMessage("Starting testcase %s" % testcase.testId)
            self.testCompletionBefore = time.time() + \
                testcase.testTimeout + PeerState.TEST_TIMEOUT_GRACE
            self.testStarted = True
            self.currentTest = testcase
            self.currentTest.peer = self.peer
            self.startTime = time.time()
            self.logsReceived = False
            return

        if not self.testStarted and self.currentTest:
            print 'LATE started', self.testStarted, 'current id', self.currentTest.testId, \
                'incoming id', testcase.testId, 'state', testcase.state
            return 

        elif not self.testStarted and not self.currentTest:
            print 'LATE!! no current test,', testcase.testId, testcase.state
            return

        elif self.testStarted and self.currentTest.testId != testcase.testId:
            print 'PeerState: Was not expecting test', self.testStarted, \
                'current id', self.currentTest.testId, 'incoming id', testcase.testId
            return

        if testcase.testStage and testcase.state != TestState.NORESLT():
            testcase.testFile = self.currentTest.testFile
            testcase.testClass = self.currentTest.testClass
            testcase.testMethod = self.currentTest.testMethod
            testcase.testStage = False

        self.testStarted = False
        testcase.startTime = self.startTime
        self.__completeTest(testcase)
        testcase.peer = self.peer
        self.currentTest = None

        self.waiterThread = threading.Thread(target = self.__logFilesWaiter, args = [testcase])
        self.waiterThread.start()

    def __logFilesWaiter(self, testcase):
        self.stime = time.time()

        print ' **> LogFilesWaiter is waiting, %d, %s, %s' \
            % (self.stime, self.logsReceived, self.peer.ipAddress)

        # FIXME: hack to allow the files to be sent.
        # This disables the protection from the slave
        # failing to send the files.
        while self.stime == None or \
        (time.time() - self.stime < 1800000000000000000000 and \
        not self.logsReceived):
            if self.shuttingDown:
                return
            time.sleep(1)

        print ' **> LogFilesWaiter has stopped waiting, %d, %s, %s, %s, %s' \
            % (time.time() - self.stime, self.stime, self.logsReceived, time.time(), self.peer.ipAddress)
   
        if self.logsReceived and self.REBOOT_PER_TEST:
            print ' **> Rebooting peer as test has completed, %s' % self.peer.ipAddress
            SignalExchangeHub().propagateSignal(PeerReboot(self.peer))
        elif self.logsReceived and not self.REBOOT_PER_TEST:
            print ' **> Test has completed, no need for reboot, %s' % self.peer.ipAddress
            self.peer.setState(ActivePeerState.ACTIVE())
        elif self.logsReceived == False:
            print ' **> Didn\'t receive log files for %s' % self.peer.ipAddress
            SignalExchangeHub().propagateSignal(PeerRecovery(self.peer)) 
            logSig = LogFilesTransfered(self.peer.macAddress, testcase.testId, {}, testcase.iteration)
            logSig.removePeerNamespace()
            SignalExchangeHub().propagateSignal(logSig)
            testcase.state = TestState.SLAVE_CRASH()
        SignalExchangeHub().propagateSignal(
            TestCompleted(self.peer.macAddress, testcase))

    def __fileServiceStateUpdate(self, state):
        """ @noLocking """
        # Allow the log files to transfer within unlimited time
        print ' **> FileServiceStateUpdate: %s,%s' %(state, self.peer.ipAddress)
        if state  == FileServiceState.RECEIVING():
            self.stime = None # Stop the timer
        elif state in [ FileServiceState.RECEIVED(), FileServiceState.FAILED() ]:
            self.stime = time.time()

    def __logFilesReceived(self, signal):
        """ @noLocking """
        if signal.peerMac != self.peer.macAddress: return
        print ' **> LogFilesReceived %s' % self.peer.ipAddress
        self.logsReceived = True

    def __heartBeatChecker(self, now):
        """
        Check to see if a heart beat is overdue
        @param now: Current Unix time (seconds)
        """
        # Cause a heart beat
        if self.beatCounter == 8:
            self.beatCounter = 0
            SignalExchangeHub().propagateSignal(PeerHeartBeat(
                self.peer.macAddress))
        else: self.beatCounter += 1

        # Heart beat isn't expected yet
        if self.heartBeatBefore > now:
            return True

        # Heart beat has timed out
        if self.peer.state >= ActivePeerState.ACTIVE():
            SignalExchangeHub().propagateSignal(PeerRecovery(self.peer))
            self.peer.addMessage("Heart beat failed: %s - %s"
                % (self.heartBeatBefore, now))

        if self.currentTest: # Fail the current test
            self.currentTest.state = TestState.DEADBOX()
            self.__completeTest(self.currentTest)
        return False

    def __testTimeoutChecker(self, now):
        """
        Check to see if a test has timed out
        @param now: Current Unix time (seconds) 
        """
        if not self.testStarted or self.testCompletionBefore > now:
            return True

        test = self.currentTest
        self.testStarted = False
        self.testCompletionBefore = -1

        SignalExchangeHub().propagateSignal(PeerRecovery(self.peer))
        test.state = TestState.SLAVE_CRASH()
        self.testStarted = False
        self.currentTest.startTime = self.startTime
        self.__completeTest(test)

        self.peer.addMessage("Test Timeout failed: %s - %s (%s)"
            % (self.testCompletionBefore, now, self.testStarted))
        return False

    def __completeTest(self, testcase):
        """
        Update the test duration and end time. Set the peer value
        Propagate a signal reflecting the completion
        """
        testcase.startTime = self.startTime
        testcase.duration = time.time() - testcase.startTime
        testcase.endTime = testcase.startTime + testcase.duration
        self.peer.addMessage("Finished testcase %s" % testcase.testId)

    def __markDeath(self):
        """
        Check if the box hasn't recovered after the recovery process.
        If the box hasn't recovered then the last test state is clarified
        to show that the box has died
        """
        self.peer.addMessage("Death recorded at: %s" % time.time())
        deadStates = [TestState.SLAVE_CRASH(), TestState.DEADBOX()]

        if self.currentTest and self.currentTest.state in deadStates:
            if self.currentTest.state == TestState.SLAVE_CRASH():
                self.currentTest.state = TestState.DEAD_SLAVE_CRASH()
            elif self.currentTest.state == TestState.DEADBOX():
                self.currentTest.state = TestState.DEAD_CRASH()

            SignalExchangeHub().propagateSignal(
                TestCompleted(self.peer.macAddress, self.currentTest))

            SignalExchangeHub().propagateSignal(LogFilesTransfered(
                self.peer.macAddress, self.currentTest.testId, {},
                self.currentTest.iteration))

            self.currentTest = None

        self.peer.setState(ActivePeerState.DEAD())

    def __expectReboot(self, signal):
        """ Related peer's test is requesting a reboot """
        self.__gatherTestLogs = True
        self.heartBeatBefore = time.time() + self.peer.getRebootTimeout()
        self.peer.setState(ActivePeerState.REBOOTING())

    def shutdown(self):
        if self.waiterThread and self.waiterThread.is_alive():
            self.shuttingDown = True
            self.waiterThread.join()
