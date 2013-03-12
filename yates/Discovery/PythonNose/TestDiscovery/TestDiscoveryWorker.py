from Discovery.PythonNose.PythonNoseTest import PythonNoseTest
from Discovery.PythonNose.TestDiscovery.docstring import process_docstr, \
    parse_test_file, find_python_files, gather_doc_str
from Utils.Logging import LogManager

from multiprocessing import Queue, Process, cpu_count
import os
import sys
import time
import traceback


class TestDiscoveryWorker(object):
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
        if not self.enabled:
            return []

        tests = []
        output_Q, input_Q = Queue(), Queue()
        processes, alive, work_avail = [], 0, True
        fullPath = os.path.join(self.testRoot, self.testPath)

        for path in find_python_files(fullPath):
            input_Q.put(path, block=False)

        while work_avail or alive > 0 or not output_Q.empty():
            time.sleep(0.1)

            work_avail = not input_Q.empty()
            alive = [p.is_alive() for p in processes].count(True)
            if alive == cpu_count() or not work_avail:
                while not output_Q.empty():
                    tests.append(output_Q.get())
                continue

            process = Process(
                target=self.__processTest,
                args=(self.testRoot, output_Q, input_Q))
            process.daemon = True
            process.start()
            processes.append(process)

        input_Q.close()
        output_Q.close()
        return tests

    def __processTest(self, test_root, output_Q, input_Q):
        ''' Convert a given file location into test objects '''
        os.chdir(test_root)
        if test_root not in sys.path:
            sys.path.insert(0, test_root)

        while not input_Q.empty():
            file_path = input_Q.get(timeout=0.5)
            test_methods = parse_test_file(test_root, file_path)

            for cls, method in test_methods:
                raw_doc = gather_doc_str(cls, method)
                doc_dict = process_docstr(raw_doc)

                try:
                    newTest = self.__createTestCase(
                        cls, method, file_path, raw_doc,
                        doc_dict, self.iterations)
                    if newTest:
                        output_Q.put(newTest)
                except:
                    self.logger.warn(
                        "Cannot create object from %s, \n%s\n%s\n\n"
                        % (file_path, doc_dict, traceback.format_exc()))

        output_Q.close()
        input_Q.close()

    def __createTestCase(self, cls, method, test_file, raw_doc, doc_dict, iterations):
        description = doc_dict.get('summary', '')
        testId = doc_dict.get('test', '')
        environment = doc_dict.get('environment', '')
        testStatus = doc_dict.get('status', '')
        testTimeout = doc_dict.get('timeout', self.defaultTestTimeout)

        # Check whether the test is function, or it is within class
        testFile = test_file.replace('%s/' % os.getcwd(), '')
        test_method = method.im_func.func_name if cls else method.func_name
        test_class = cls.__name__ if cls else None

        missing_data = []
        manditory_data = {'test method': test_method,
                          'test file': testFile,
                          'test id': testId}

        for key in manditory_data.keys():
            if manditory_data[key] in ['', None]:
                missing_data.append(key)

        if len(missing_data) > 0:
            raise Exception('Cannot create test for %s:%s.%s as %s is missing'
                % (testFile, test_class, test_method, ', '.join(missing_data)))

        return PythonNoseTest(
            description, iterations, environment, test_class,
            testMethod=test_method, testFile=testFile,
            testId=testId, testStatus=testStatus,
            testTimeout=testTimeout, docstrings=raw_doc,
            srcLoc=self.srcLoc)
