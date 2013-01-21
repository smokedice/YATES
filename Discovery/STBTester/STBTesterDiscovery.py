from Discovery.STBTester.STBTesterTest import STBTesterTest
import os

class STBTesterDiscovery(object):
    TEST_FILES = ['test.py', 'test.info']

    def __init__(self, config, path, defaultTimeout, iterations):
        self.execScriptName = 'STBTesterScript'
        self.execScriptLocation = os.path.join(path, 'STBTesterScript')
        self.srcName = 'STBTesterTests'
        self.srcLocation = os.path.abspath(config.SourceLocation.testRoot.PCDATA)
        self.config = config
        self.defaultTimeout = defaultTimeout
        self.iterations = iterations

    def createTests(self):
        """ Create tests based on the STBTester tests """
        if not os.path.exists(self.srcLocation):
            raise Exception('%s does not exist!' % self.srcLocation)

        tests = []
        for path, _, files in os.walk(self.srcLocation):
            if not all(f in files for f in self.TEST_FILES): continue
            path = os.path.abspath(path)
            docInfo = self._parseInfo(os.path.join(path, 'test.info'))
            tests.append(STBTesterTest(self.srcLocation, path, docInfo))
        return tests

    def _parseInfo(self, infoLoc):
        """ Create a dict with key/value pairs gathered from test.info """
        docData = { 'summary' : '' }
        lastKey = None

        with open(infoLoc, 'r') as infoFile:
            for line in infoFile.readlines():
                index = line.find('=')
                if index > -1:
                    lastKey, line = line.split('=', 1)
                    lastKey = lastKey.lower()
                oldValue = docData.get(lastKey or 'summary', '')
                docData[lastKey or 'summary'] = oldValue + line
        return docData
