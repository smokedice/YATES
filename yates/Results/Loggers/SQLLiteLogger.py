from yates.Domain.States import TestState as TestStateValues
from yates.Results.Model import ModelUtils
from yates.Results.Model.ModelUtils import ResultBaseModel
from yates.Results.Model.Peer import Peer
from yates.Results.Model.PeerStates import PeerStates
from yates.Results.Model.TestDetails import TestDetails
from yates.Results.Model.TestExecutionDetails import TestExecutionDetails
from yates.Results.Model.TestResults import TestResults
from yates.Results.Model.TestStates import TestStates
from yates.Utils import Network
from yates.Domain.States import PeerState

import time, os, math
from Queue import Empty

class SqlLiteLogger(object):
    """
    Log results and states to a SqlLite database

    Expectations:
     * TestMetadata is received first
     * Source object is then received
    """
    SQL_FILENAME = "results.sqlite3"

    def __init__(self, config, loc, description, source):
        self.filesWaitingForTests = {}
        self.testsWaitingForFiles = {}
        clearTables = config.clear == 'true'

        databaseLocation = os.path.join(loc, SqlLiteLogger.SQL_FILENAME)
        ModelUtils.ResultBaseModel.Meta.database.init(databaseLocation)

        tables = [
            Peer,
            TestDetails,
            TestExecutionDetails,
            PeerStates,
            TestResults,
            TestStates ]

        # Recreate tables
        for table in tables:
            if table.table_exists() and clearTables:
                table.drop_table()
                time.sleep(0.1)

            if not table.table_exists():
                table.create_table()

        for name, properties in TestStateValues.VALUES.items():
            TestStates.create(
                name = name,
                **properties
            ).save()

        self.__setTestSuiteName(description)
        self.__setSourceObject(source)
        self.__setupStage()

    def __setTestSuiteName(self, packDetails):
        """ Receive the test suite name """
        self.testSuiteName, self.packFilterDesc, self.shortFilterDesc, \
            self.executionName, self.startTime = packDetails

    def __setSourceObject(self, source):
        """ Receive the source object """
        self.source = source

    def __setupStage(self):
        """ Create all objects within the database with defaults """
        self.executionDetails = TestExecutionDetails.create(
            testSuiteName = self.testSuiteName,
            executionName = self.executionName, #TODO: make me!
            scmidentifier = 'N/A',
            shortFilterDesc = self.shortFilterDesc,
            testPackDescriptor = self.packFilterDesc,
            startTime = time.time(),
            endTime = -1,
            duration = -1,
            envservExecutionModeName = 'automated', # FIXME: read from config
            hostNetAddress = Network.getIPAddressByInterface(),
            hostMacAddress = Network.getMacAddress(),
            tasVersion = os.environ['TAS_VERSION'])
        self.executionDetails.save()

        if not hasattr(self, 'source'):
            raise Exception("SQLLiteLogger: Source object has not been set")

        ResultBaseModel.Meta.database.set_autocommit(False)
        for group in self.source.groups:
            for test in group.tests:

                testDetails = TestDetails.get_or_create(
                    testId = str(test.testId),
                    module = str(test.testFile),
                    testName = test.combineClassMethod(),
                    invalid = test.invalid,
                    manualInspection = test.manualInspection,
                    docstrings = "\n".join(test.docstrings),
                    timeout = test.testTimeout)

                testState = TestStates.filter(sequenceId = test.state.index).get()
                testResults = TestResults.create(
                    testDetailsRef = testDetails,
                    executed = False,
                    invalid = test.invalid,
                    result = testState,
                    error = test.error,
                    startTime = -1,
                    duration = -1,
                    manualInspection = test.manualInspection,
                    testExecutionDetailsRef = self.executionDetails,
                    peerRef = None,
                    iterationId = None)

                testResults.save()
                testDetails.save()

        ResultBaseModel.Meta.database.commit()
        ResultBaseModel.Meta.database.set_autocommit(True)

    def logPeerState(self, peer, comment = None):
        """ Log a peer state change """
        dbPeer = self.__getPeer(peer)
        capabilityValues = None

        if peer.state == PeerState.PENDING():
            capabilityValues = peer.capabilities

        peerState = PeerStates.create(
            peerRef = dbPeer,
            state = str(peer.state),
            timestamp = time.time(),
            capabilities = capabilityValues)

        dbPeer.save()
        peerState.save()

    def logResult(self, test, files):
        """ When a test result has been processed update the database """
        peer = None
        if test.peer:
            peer = Peer.get(macAddress = test.peer.macAddr)

        testDetails = TestDetails.get(testId = test.testId)
        testState = TestStates.filter(sequenceId = test.state.index).get()

        values = {
            'testDetailsRef'         : testDetails,
            'executed'               : test.executed,
            'invalid'                : test.invalid,
            'result'                 : testState,
            'error'                  : test.error,
            'startTime'              : test.startTime,
            'duration'               : math.ceil(test.duration),
            'manualInspection'       : test.manualInspection,
            'peerRef'                : peer,
            'iterationId'            : test.uniqueId }

        testResult = None
        if testDetails.testresults_set.count() == 1:
            testResult = testDetails.testresults_set.get()
            if TestStateValues.NORESLT().index != testResult.result.sequenceId:
                testResult = None

        if testResult: # Update object
            for name, value in values.items():
                setattr(testResult, name, value)
        else: # Create new object
            testResult = TestResults.create(**values)
            testResult.testExecutionDetailsRef = self.executionDetails
        testResult.save()

    def logIteration(self, iteration):
        pass

    def __getPeer(self, peer):
        """ Retrieve peer details from the database by a peer object """
        try:
            return Peer.get(macAddress = peer.macAddr)
        except Peer.DoesNotExist:
            peer = Peer.create(
                macAddress = peer.macAddr,
                netAddress = "%s:%s" % (peer.ipAddr, '5005'))
            peer.save()
            return peer

    def shutdown(self):
        """ Stop all logging of results """
        if self.testSuiteName and hasattr(self, 'executionDetails'):
            endTime = time.time()
            duration = int(endTime - self.executionDetails.startTime)
            self.executionDetails.endTime = endTime
            self.executionDetails.duration = duration
            self.executionDetails.save()

        if hasattr(ModelUtils.ResultBaseModel.Meta.database, 'conn'):
            ModelUtils.ResultBaseModel.Meta.database.close()
