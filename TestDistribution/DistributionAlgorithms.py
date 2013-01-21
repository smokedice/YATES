from Utils.Configuration import ConfigurationManager
from Utils.Logging import LogManager

from StringIO import StringIO
from itertools import permutations, izip
import copy

class AbstractDistributor(object):
    def __init__(self, source):
        self.execMap = {}
        self.logger = LogManager().getLogger(
            self.__class__.__name__)

    def recordExecution(self, peer, test):
        """
        Add the test to the map, which contains the history of
        the test distribution to the peers
        """
        if not peer.macAddr in self.execMap.keys():
            self.execMap[peer.macAddr] = []
        self.execMap[peer.macAddr].append(test)

    def assignSuitableTest(self, peer, peers, source):
        '''
        Method, which finds the suitable test for the given peer
        @param peer: the peer, which is active and awaits the test
        @param souce: the source object with groups of tests
        @return: found test and modified source
        '''
        for gi in range(0, len(source.groups)):
            for ti in range(0, len(source.groups[gi].tests)):
                test = source.groups[gi].tests[ti]

                if not self.useTest(peer, peers,
                source, source.groups[gi], test, True):
                    continue

                self.recordExecution(peer, test)
                return copy.deepcopy(test), source

        self.logger.warn('Could not find any test for peer %s' % peer.ipAddr)
        return None, source

    def peekSuitableTest(self, peer, peers, source):
        '''
        Method, which finds the suitable test for the given peer
        @param peer: the peer, which is active and awaits the test
        @param souce: the source object with groups of tests
        @return: found test and modified source
        '''
        for gi in range(0, len(source.groups)):
            for ti in range(0, len(source.groups[gi].tests)):
                test = source.groups[gi].tests[ti]

                if not self.useTest(peer, peers,
                source, source.groups[gi], test, False):
                    continue
                return copy.deepcopy(test)

        return None

    def isSuitable(self, has, requires):
        '''
        Method copied from envutils/caps.py module
        @param requires: modulators required by test
        @param has: modulators provided by the box
        @return: True or False depending on the box capability
        '''
        has = [ set(c.split('/')) for c in has.split() ]
        requires = [ set((r,)) for r in requires.split() ]
        if len(has) < len(requires): return False

        return any(
            all(h >= r for r, h in izip(requires, perm))
            for perm in permutations(has, len(requires)))

    def whatsMissing(self, has, requires):
        has = [ set(c.split('/')) for c in has.split() ]
        requires = [ set((r,)) for r in requires.split() ]

        for r in requires[:]:
            for h in has:
                if not any(x in h for x in r):
                    continue

                has.remove(h)
                requires.remove(r)
                break

        strBuffer = StringIO()
        for r in requires:
            strBuffer.write(' %s' % '/'.join(list(r)))

        result = strBuffer.getvalue()
        strBuffer.close()
        return result

    def useTest(self, peer, peers, source, group, test, alterSource):
        raise NotImplementedError()

    def executed(self, peers, test):
        raise NotImplementedError()

class SingleExecution(AbstractDistributor):
    def useTest(self, peer, peers, source, group, test, alterSource): 
        """ Execute one test on one box """
        if not self.isSuitable(peer.capabilities, test.environment):
            return False

        # Do not alter the source, just peaking
        if not alterSource: return True

        group.tests.pop(group.tests.index(test))
        if len(group.tests) == 0:
            source.groups.pop(source.groups.index(group))
        return True

    def executed(self, peers, test):
        for peer in peers.values():
            if peer.macAddr not in self.execMap.keys():
                continue
            if test in self.execMap[peer.macAddr]:
                return True
        return False

class ExecutionOnEachBox(AbstractDistributor):
    def useTest(self, peer, peers, source, group, test, alterSource):
        """ Execute all tests on all boxes where possible """
        if not self.isSuitable(peer.capabilities, test.environment):
            return False

        # Check if this test has already been executed once by this peer
        if peer.macAddr in self.execMap.keys() and \
        test in self.execMap[peer.macAddr]:
            return False

        # Do not alter the source, just peaking
        if not alterSource: return True

        # Find out if any other box still requires this test
        for otherPeer in peers.values():
            if otherPeer == peer: continue
            noPeerHistory = otherPeer.macAddr not in self.execMap.keys()
            noTestHistory = True if noPeerHistory else test not in self.execMap[otherPeer.macAddr]
            isSuitable = self.isSuitable(otherPeer.capabilities, test.environment)

            if isSuitable and (noPeerHistory or noTestHistory):
                return True # Another peer still needs to execute the test

        # Remove test as it is not needed
        group.tests.pop(group.tests.index(test))

        if len(group.tests) == 0:
            source.groups.pop(source.groups.index(group))
        return True

    def executed(self, peers, test):
        for peer in peers.values():
            if peer.macAddr not in self.execMap.keys():
                return False    
            elif test not in self.execMap[peer.macAddr]:
                return False
        return True

class ExecutionOnEachBoxEvenly(ExecutionOnEachBox):
    def __init__(self, source):
        ExecutionOnEachBox.__init__(self, source)
        self.runningTests = {}
        self.tests = []

        for group in source.groups:
            for test in group.tests:
                self.tests.append([0, test, group])

    def __sortTests(self):
        self.tests = sorted(self.tests, key = lambda test: test[0])

    def recordExecution(self, peer, index):
        ExecutionOnEachBox.recordExecution(self, peer, self.tests[index][1])
        self.runningTests[peer.macAddr] = self.tests[index][1].testId
        self.tests[index][0] += 1
        self.__sortTests()

    def assignSuitableTest(self, peer, peers, source):
        '''
        Method, which finds the suitable test for the given peer
        @param peer: the peer, which is active and awaits the test
        @param souce: the source object with groups of tests
        @return: found test and modified source
        '''
        index, test = self.__findTest(peer, peers, source)
        if not test: return None, source

        self.recordExecution(peer, index)
        return copy.deepcopy(test), source

    def __findTest(self, peer, peers, source):
        rIndex = rExCount = rTest = rGroup = None

        for index, testDetails in enumerate(self.tests):
            exCount, test, group = testDetails
            isRunning = test.testId in self.runningTests.values()
            useTest = self.useTest(peer, peers, source, group, test, False)

            if not useTest: continue
            elif isRunning and rTest: continue
            elif isRunning:
                rExCount, rTest, _ = testDetails
                rIndex = index
            elif not rTest: return index, test
            elif exCount <= rExCount: return index, test

        return rIndex, rTest

    def peekSuitableTest(self, peer, peers, source):
        '''
        Method, which finds the suitable test for the given peer
        @param peer: the peer, which is active and awaits the test
        @param souce: the source object with groups of tests
        @return: found test and modified source
        '''
        for testDetails in self.tests: 
            test = testDetails[1]
            group = testDetails[2]

            if self.useTest(peer, peers,
            source, group, test, False):
                return copy.deepcopy(test)

        return None
    
    def executed(self, peers, test):
        if len(peers.keys()) == 0: return False
        for peer in peers.values():
            if peer.macAddr not in self.execMap.keys():
                return False    
            elif test not in self.execMap[peer.macAddr]:
                return False
        return True
