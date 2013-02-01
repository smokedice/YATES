from Domain.States import TestState
from Utils.Configuration import ConfigurationManager
from Utils.Logging import LogManager
from Utils import Network

import re, copy, tempfile, traceback

class TestDistributor(object):
    DISTR_CFG = 'execution'

    def __init__(self, peers, source):
        self.logger = LogManager().getLogger(self.__class__.__name__)
        self.scheduledTests = {}
        self.source = source
        self.peers = peers

        # Check if there are any tests to distribute
        groups = [ group for group in self.source.groups ]
        testCount = sum([ len(group.tests) for group in groups ])
        if testCount  ==  0: raise Exception("No tests to execute")
            
        conf = ConfigurationManager().getConfiguration(self.DISTR_CFG).configuration
        self.distributionModule = "TestDistribution.DistributionAlgorithms"
        self.distributionAlgorithmCls = conf.distributionAlgorithm.PCDATA
        self.currentIteration = 1

        try: self.iterations = int(conf.iterations.PCDATA)
        except ValueError: self.iterations = 1
        self.testDistributor = self.__getDistributor()

    def continueIterations(self):
        """ Returns true if more iterations should follow """
        if self.currentIteration > 0: self.currentIteration += 1
        if 0 < self.iterations < self.currentIteration: return False
        self.testDistributor = self.__getDistributor()
        return True
        
    def __getDistributor(self):
        mod = __import__(self.distributionModule, fromlist = [ self.distributionAlgorithmCls ])
        return getattr(mod, self.distributionAlgorithmCls)(copy.deepcopy(self.source))

    def getNonFinishedTests(self):
        """
        Get all the tests that have not been
        executed and mark them as insuffient environment
        @return: List of non executed tests
        """
        nonExecutedTests = []
    
        for test in self.source.getTests():
            if self.testDistributor.executed(self.peers, test):
                continue

            test.state = TestState.INSUFFICIENT_ENV()
            nonExecutedTests.append(test)
        return nonExecutedTests

    def getTest(self, peer):
        '''
        The private method handler, which is executed, when the 
        peer update signal is received. If the peer is active and
        the source exists, the method sends the test to the
        received peer.
        @param peer: the peer which acquired the new state
        '''
        return self.__getScheduledTestForPeer(peer) or self.__assignTestForPeer(peer)

    def peekTest(self, peer):
        """ Check to see if any tests need executing """
        return  self.testDistributor.peekSuitableTest(peer, self.peers, self.source)

    def __getScheduledTestForPeer(self, peer):
        """ Find next stage for peer, if it exists """
        return self.scheduledTests.pop(peer.macAddr, None)

    def __assignTestForPeer(self, peer):
        """ Assign a test that matches the capabilities of the given peer """
        if len(self.source.groups or []) == 0: return None
        test, _ = self.testDistributor.assignSuitableTest(peer, self.peers, self.source)
        return test

    def getDistributionHistory(self):
        '''
        The method returns the dictionary, which contains peers
        as the keys and the tests, which have been distributed
        to the peer as values.
        @return {peer.macAddress:[tests]}
        '''
        return self.testDistributor.execMap
