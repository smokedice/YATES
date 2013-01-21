from Discovery.PythonNose.PythonNoseTest import PythonNoseTest
from Test.YVDocstring import YVDocstring
from TestGather.TestDiscovery.TestCaseParser import TestCaseParser
from Utils.Logging import LogManager

import nose, os, pickle, sys, tempfile, time
from glob import glob

class TestDiscoveryWorker(object):
    '''
    Class creates the source object using the tests discovered
    in the filesystem using nose API. If the DiscoveryWorker
    is disabled in the configuration, then the source with the
    empty test list is returned
    '''
    NOSE_ARGS = ["", "--collect-only", "--exe", "--with-id", "--quiet"]
    CONFIG_ENABLED_TRUE = 'true'

    def __init__(self, config, defaultTimeout, iterations, srcLoc):
        self.test = 0
        self.config = config
        self.logger = LogManager().getLogger('TestDiscoveryWorker')

        self.enabled = self.config.DiscoveryWorker.enabled == 'true'
        self.testRoot = os.path.abspath(self.config.SourceLocation.testRoot.PCDATA)
        self.testPath = self.config.SourceLocation.testPath.PCDATA or ""
        self.defaultTestTimeout = defaultTimeout
        self.iterations = iterations
        self.srcLoc = srcLoc

    def createTests(self):
        '''
        Method creates the Source object, default group and the list 
        of tests. If the discovery worker is disabled, then the 
        empty list of tests is stored in the Source object
        @return: the source object with the list of tests
        '''
        if self.enabled:
            return self.__discoverTests()
        return []

    def __discoverTests(self):
        '''
        Creates the list of Test() objects, which contain the information
        about the tests, stored at the certain path relative to root
        @param root: the root of the testpacks
        @param path: the path to the certain test files relative to root
        @return: the list of test objects
        '''
        #TODO: convert the path to list
        testDocs = {}

        #Get the nosetest ID data
        testIds = self.__collectTestInfo()
        parser = TestCaseParser()

        #Parse the ids data and generate the testDocs list
        oldPath = os.getcwd()
        os.chdir(self.testRoot)

        try:
            for testCaseData in testIds.values():
                parser.parseTestCase(testCaseData, testDocs)
            #Convert textual docs into objects, for easier access
            testDocs = YVDocstring.convertToYVDocstring(testDocs)
            return self.__generateTestList(testDocs)
        finally:
            os.chdir(oldPath)

    def __collectTestInfo(self):
        '''
        Method collects the information about tests using
        the nose framework. 
        @param root: the root of the testpacks
        @param path: the path to the certain test files relative to root
        @return: the information about tests
        '''
        #    Must do this here otherwise impossible to unittest:
        self.testRoot = os.path.realpath(self.testRoot)

        oldPath = os.getcwd()

        try:
            if os.path.exists(self.testRoot):
                os.chdir(self.testRoot)

            sys.path.insert(0, self.testRoot)

            args = self.NOSE_ARGS
            #TODO: make this more safe, potentially this is still
            #unsafe, as the function returns only the unique name
            #file is not created
            tmpFile = tempfile.mktemp()
            tmpFile = tmpFile + str(time.time())
            args.append("--id-file=%s" % tmpFile)

            fullPath = os.path.join(self.testRoot, self.testPath)
            dirContents = glob('%s/*' % fullPath) + [ fullPath ]

            # TODO: not sure why we need to do this, but the soak
            # tests do not work without it
            # Load all surrounding modules
            for dirContent in dirContents:
                if not os.path.isdir(dirContent): continue
                sys.path.insert(1, dirContent)
                modulePath = dirContent[len(self.testRoot):]

                modulePath = os.path.relpath(dirContent, self.testRoot)
                if modulePath.startswith('/'):
                    #    TODO: This probably isn't needed anymore:
                    modulePath = modulePath[1:]

                if len(modulePath) == 0: continue
                pkgName = modulePath.replace('/', '.')

                try:
                    __import__(pkgName)
                except ImportError:
                    self.logger.warn('Failed to load the module, %s' % pkgName)

            fullPath = os.path.join(self.testRoot, self.testPath)
            nose.run(defaultTest = str(fullPath), argv = args)
        finally:
            os.chdir(oldPath)

        testInfo = pickle.loads(file(tmpFile).read())["ids"]

        if os.path.exists(tmpFile):
            os.remove(tmpFile)
        return testInfo

    def __generateTestList(self, testDocs):
        '''
        Creates the list of Test() objects from dictionary of tests
        @param testDocs: the dictionary in the format
                         {path:{testClass.testMethod:{YVDocstring}}
        @return: the list of Test() objects
        '''
        tests = []
        for tfile, tcases in testDocs.items():
            for tcase in tcases:
                try:
                    test = self.__createTestCase(tcase, tfile,
                       testDocs, self.iterations)
                    if test: tests.append(test)
                except Exception, e:
                    self.logger.warn('Could not parse: %s:%s, %s' % (tfile, tcase, e))
        return tests

    def __createTestCase(self, tcase, tfile, testDocs, iterations):
        doc = testDocs[tfile][tcase]
        description = doc.getFieldOrDefault(YVDocstring.SUMMARY)
        testId = doc.getFieldOrDefault(YVDocstring.TEST)
        environment = doc.getFieldOrDefault(YVDocstring.ENVIRONMENT, '')
        testStatus = doc.getFieldOrDefault(YVDocstring.STATUS)
        testTimeout = doc.getFieldOrDefault(YVDocstring.TIMEOUT, self.defaultTestTimeout)
        docstrings = doc._docStrings
        # the path to the file is relative to the testpack

        fullPath = os.getcwd()
        if not fullPath.endswith('/'):
            fullPath = "%s/" % fullPath
        testFile = tfile.replace(fullPath, '')
        testFile = os.path.realpath(testFile)
        testFile = testFile.replace("%s/" % os.path.realpath(self.testRoot), '')

        # Check whether the test is function, or it is within class
        splitTcase = tcase.split('.')

        if len(splitTcase) == 2:
            testClass = splitTcase[0]
            testMethod = splitTcase[1]
        else:
            testClass = None
            testMethod = splitTcase[0]

        testClass = testClass if not testClass else str(testClass.decode('utf-8', errors = "ignore"))
        testMethod = str(testMethod.decode('utf-8', errors = "ignore"))
        testFile = str(testFile.decode('utf-8', errors = "ignore"))
        testId = str(testId.decode('utf-8', errors = "ignore"))
        testStatus = str(testStatus.decode('utf-8', errors = "ignore"))
        docstrings = [ str(x.decode('utf-8', errors = "ignore")) for x in docstrings ]

        if '' in [ testMethod, testFile, testId ]:
            return self.logger.warn('Cannot create test for %s, %s, %s' %(tcase, tfile, self.testPath))

        return PythonNoseTest(description, iterations, environment,
            testClass, testMethod = testMethod, testFile = testFile,
            testId = testId, testStatus = testStatus,
            testTimeout = testTimeout, docstrings = docstrings,
            srcLoc = self.srcLoc)
