from Master.Domain.CheckPeerState import CheckPeerState
from Master.Domain.ComponentCommand import ComponentCommand
from Common.CommonSignals.Enums.ActivePeerState import ActivePeerState
from Common.CommonSignals.FServiceInfo import FServiceInfo
from Common.CommonSignals.PeerStateUpdate import PeerStateUpdate
from Common.CommonSignals.TeardownStage import TeardownStage
from Common.CommonSignals.TeardownComplete import TeardownComplete
from Common.CommonSignals.ComponentSetupResult import ComponentSetupResult
from Master.MasterBusinessLogic.TestEnvironment.PeerState import PeerState
from Common.SignalExchangeHub.SignalExchangeHub import SignalExchangeHub
from Common.TASUtils.Singleton import Singleton
from threading import Thread, RLock
import time

class TestEnvironmentWorker(Singleton, Thread):
    _instance = None
    _instanceLock = RLock()
    CHECK_STATUS_DELAY = 0.5 # TODO: configure me!

    def _setup(self):
        Thread.__init__(self,
            name = self.__class__.__name__)

        self.peerStates = {}
        self.monitor = True
        self.activelyProcess = True

        SignalExchangeHub().addListener(
            PeerStateUpdate.createListener(self.__peerStateUpdate))

        SignalExchangeHub().addListener(
            ComponentCommand.createListener(self.__command))

        SignalExchangeHub().addListener(FServiceInfo.createListener(
            self.__fileServiceInfo))

        SignalExchangeHub().addListener(TeardownStage.createListener(
            self.stop, 1))

    def __fileServiceInfo(self, fServiceInfo):
        self.fServiceHost = fServiceInfo.host
        self.fServicePort = fServiceInfo.port

    def run(self):
        while self.monitor:
            time.sleep(self.CHECK_STATUS_DELAY)
            if not self.activelyProcess: continue
            SignalExchangeHub().propagateSignal(CheckPeerState())

    def start(self): # Cannot restart once stopped!
        if not self.monitor: return

        self.activelyProcess = True
        if not self.is_alive():
            Thread.start(self)

    def stop(self):
        self.shutdown()
        SignalExchangeHub().propagateSignal(TeardownComplete(
            ComponentSetupResult('TestEnvironmentWorker', True)))

    def pause(self):
        self.activelyProcess = False

    def reset(self): # TODO: Threading problem?
        for peerState in self.peerStates.values():
            peerState.reset()

    def shutdown(self):
        for peerState in self.peerStates.values():
            peerState.shutdown()
        self.monitor = False
        if self.is_alive():
            self.join()

    def __peerStateUpdate(self, signal):
        peer = signal.peer
        state = signal.state

        if state != ActivePeerState.PENDING() or \
        peer.macAddress in self.peerStates.keys():
            return

        self.peerStates[peer.macAddress] = PeerState(peer,
            self.fServiceHost, self.fServicePort)

    def __command(self, cmd):
        cmd = cmd.lower()
        if cmd in ("start", "stop", "pause", "reset"):
            getattr(self, cmd)()
