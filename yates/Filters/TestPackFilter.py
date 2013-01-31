from StringIO import StringIO
from Utils.Configuration import ConfigurationManager
from sets import Set
import os
import re

class TestPackFilter(object):
    ID_PATTERN = re.compile('^[ \t]*([0-9]+).*$')

    def __init__(self):
        self.testIDs = Set()
        self.enabled = True
        self.desc = ''

        # Get test pack file location
        config = ConfigurationManager().getConfiguration('filters').configuration

        if not hasattr(config, 'TestPackFilter') or \
        config.TestPackFilter.enabled != 'true':
            self.enabled = False
            return

        self.testPackLocations = config.TestPackFilter.locations.location
        if not isinstance(self.testPackLocations, list):
            self.testPackLocations = [ self.testPackLocations ]

        descBuffer = StringIO("Test Pack Filter (%s): " %
            ", ".join([ x.PCDATA for x in self.testPackLocations]))

        for testPackLocation in self.testPackLocations:
            testPackLocation = testPackLocation.PCDATA

            if not os.path.exists(testPackLocation) or \
            not os.path.isfile(testPackLocation):
                print 'Test Pack Location doesn\'t exist: %s' % testPackLocation
                continue

            # Load test pack file
            with open(testPackLocation, 'r') as testPackFile:
                testPackLines = testPackFile.readlines()
            testPackLength = len(testPackLines)

            # Find integers on each line
            for index, testPackLine in enumerate(testPackLines):
                match = re.search(TestPackFilter.ID_PATTERN, testPackLine)
                if not match: continue

                testID = match.groups()[0]
                if testID <= 0: continue
                self.testIDs.add(testID)
                descBuffer.write(testID)

                if index + 1 < testPackLength:
                    descBuffer.write(', ')

            self.desc = descBuffer.getvalue()
            descBuffer.close()

        if len(self.testIDs) == 0:
            raise Exception(
                'TestPackFilter : Could not find any test IDs within ' +
                'configured test packs')

    def isEnabled(self):
        return self.enabled

    def filterTests(self, source):
        if not self.enabled or len(self.testIDs) == 0:
            return source

        for group in source.groups:
            tests = group.tests[:]
            print len(group.tests), 'tests'
            for test in group.tests:
                if str(test.testId) not in self.testIDs:
                    tests.remove(test)
                else: 'ha!', test.testId
            group.tests = tests

        return source

    def getAppliedFilterDescription(self):
        return self.desc
