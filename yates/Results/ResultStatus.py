from yates.Domain.States import TestState

from StringIO import StringIO
from gnosis.xml.objectify._objectify import make_instance
from multiprocessing import Queue, Process
from Queue import Empty
import re, os

regexChecks = [
    (re.compile('^Traceback [^,]+, line [0-9]+, in run self\.setUp\(\) File.+$'), TestState.CLASS_SETUP()),
    (re.compile('^Traceback [^,]+, line [0-9]+, in run self\.tearDown\(\) File.+$'), TestState.CLASS_TEARDOWN()),
    (re.compile('^.*Scan failed : channel scan failed at.*'), TestState.CHANNELSCAN_FAILED()),
    (re.compile('^.*Service list is empty.*'), TestState.NO_SERVICE_LIST()),
    (re.compile('^.*Current time source =.*'), TestState.ERROR_TIMESOURCE()),
    (re.compile('envutils/envcontrol\.py'), TestState.ENV_SERVER()),
    (re.compile('org\.freedesktop\.dbus\.error\.noreply', re.I), TestState.DBUS_NO_REPLY_ERROR()),
    (re.compile('org\.freedesktop\.dbus\.error', re.I), TestState.DBUS_ERROR()),
]

class UnknownErrorType(Exception): pass
class EmptyLogFile(Exception): pass

class ResultDefiner(Process):
    def __init__(self, fileLocs, test):
        self.fileLocs = fileLocs
        self.test = test
        self.queue = Queue()

        Process.__init__(self, target = self.__defineResult, name = "ResultDefiner")
        self.start()

    def __loadXMLFiles(self, xmlLocation):
        with open(xmlLocation, 'r') as xmlFile:
            xml = xmlFile.read()
            if xml == '': raise EmptyLogFile('%s is empty' % xmlLocation)

        obj = make_instance(xml)
        del xml # Release memory
        return obj

    def __defineResult(self):
        """
        Define a result based on the log files. This process will return
        the error type and a text blob that explains the error.
        @param fileLocations: Dictionary containing locations of the log files. \
        Key value relationship should be file name to file location. The keys should
        follow the same naming scheme that is defined with the Test object
        @self.queue.put((: Tuple with error type and error message))
        @raise EmptyLogFile: Raised if the xml log is empty
        """
        if self.test.state != TestState.NORESLT():
            return self.queue.put((self.test.state, 'Result defined by TAS'))

        files = {}
        for fileLoc in self.fileLocs:
            fullName = fileLoc.split(os.path.sep)[-1]
            name = fullName.split('.')[0].lower()
            files[name] = fileLoc

        if 'xunit' not in files.keys():
            return self.queue.put((TestState.NO_XML(), 'No XUnit file provided!'))

        try:
            result = self.__loadXMLFiles(files['xunit'])
        except Exception, e:
            return self.queue.put((TestState.INVALID_XML(), str(e)))

        tests = int(result.tests)
        errors = int(result.errors)
        failures = int(result.failures)
        skip = int(result.skip)
        problems = errors + failures + skip

        if problems == 0: # No problems here
            return self.queue.put((TestState.PASS(), ''))

        # There must be a problem
        errorMsgBuffer = StringIO()
        testcases = result.testcase \
            if isinstance(result.testcase, list) \
            else [result.testcase]

        # Combine all error messages
        for testcase in testcases:
            if not hasattr(testcase, 'error'): continue
            errorMsgBuffer.write(testcase.error.PCDATA)
        errorMsg = errorMsgBuffer.getvalue()
        errorMsgBuffer.close()

        # Module SetUp/TearDown
        if testcases[0].name.endswith('>:setup'):
            return self.queue.put((TestState.MODULE_INST(), errorMsg))
        elif tests == 2 and errors == 1:
            return self.queue.put((TestState.MODULE_TEARDOWN(), errorMsg))

        for regex, testState in regexChecks:
            if re.search(regex, errorMsg):
                return self.queue.put((testState, errorMsg))

        if errors > 0: return self.queue.put((TestState.ERROR(), errorMsg))
        elif skip > 0: return self.queue.put((TestState.SKIP(), errorMsg))
        elif failures > 0: return self.queue.put((TestState.FAILURE(), errorMsg))
        return self.queue.put((TestState.PASS(), errorMsg))

    def getResult(self):
        """
        Retrieve the Test Status and Error blob
        @self.queue.put(( Test status and error blob))
        """
        if self.is_alive():
            return (None, None)

        result = self.queue.get()
        self.queue.close()
        return result
