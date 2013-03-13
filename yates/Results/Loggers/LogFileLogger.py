from yates.Domain.States import TestState as TestStateValues
from yates.Utils import Network
from yates.Domain.States import PeerState

import time, os, math, datetime, sys, StringIO
from Queue import Empty

class LogFileLogger(object):
    """ Log results and states to a log file """
    LOG_FILENAME = "log.txt"

    def __init__(self, config, loc, description, source):
        base = LogFileLogger.LOG_FILENAME
        logFileLoc = os.path.join(loc, base)
        self.startTime = time.time()
        self.other_logs = []

        self.total_tests, self.successful_tests = 0, 0
        self.base_count = {}

        if config.verbose == 'true':
            self.other_logs.append(sys.stdout)

        if not os.path.exists(base):
            os.makedirs(base)

        if config.clear == 'false' or \
        os.path.exists(logFileLoc):
            mode = 'a'
        else: mode = 'w'

        self.logFile = open(logFileLoc, mode, 0)
        self._log_message("TAS Version: %s\n" % os.environ['TAS_VERSION'])
        self._log_message("Execution Description: %s\n" % ",".join(description))
        self._log_message("Selected Tests:\n")

        self.logFile.write(
            ", ".join([ "\n\t%s" % str(y.testId).zfill(4)
            if x % 5 == 0
            else str(y.testId).zfill(4)
            for x,y in enumerate(source.getTests())]))

        self._log_message("\n\n")

    def logPeerState(self, peer, comment = None):
        """ Log a peer state change """
        comment = '' if not comment else ', %s' % comment
        self._log_message("Peer %s (%s) has changed state to %s%s\n"
            %(peer.ipAddr, peer.macAddr, peer.state, comment))

    def logResult(self, test, files):
        """ When a test result has been processed update the database """
        if test.peer:
            self._log_message("Peer %s (%s) has completed test %s, result %s\n"
                %(test.peer.ipAddr, test.peer.macAddr, test.testId, test.state))
        else:
            self._log_message('Test %s has been completed, result %s\n' %(test.testId, test.status))

        self.total_tests += 1
        if test.state == TestStateValues.PASS():
            self.successful_tests += 1

        base_type = test.state.baseType
        count = self.base_count.get(base_type, 0) + 1
        self.base_count[base_type] = count

        if self.total_tests % 10 == 0:
            average = (100 / self.total_tests) * self.successful_tests
            self._log_message('Average Pass Rate: %f%s, Total Tests %d\n'
                % (average, '%', self.total_tests))

            buff = StringIO.StringIO('Results Breakdown: ')
            length = len(self.base_count.keys())
            for i, values in enumerate(self.base_count.items()):
                base_type, count = values
                buff.write(base_type)
                buff.write(': ')
                buff.write(count)

                if i + 1 < length: buff.write(', ')
                elif i + 1 == length: buff.write('\n')

            self._log_message(buff.getvalue())
            buff.close()

    def logIteration(self, iteration):
        self._log_message('Executing iteration %d\n' % iteration)

    def _log_message(self, msg):
        msg = '%s: %s' % (datetime.datetime.now(), msg)
        self.logFile.write(msg)
        for log in self.other_logs:
            log.write(msg)

    def shutdown(self):
        """ Stop all logging of results """
        # TODO: BUG: if execution is over 31 days this will fail
        sec = datetime.timedelta(0, time.time() - self.startTime)
        d = datetime.datetime(1,1,1) + sec
        taken = ('%d day(s), %d hour(s), %d minute(s) and %d second(s)'
            %(d.day-1, d.hour, d.minute, d.second))

        self._log_message('Execution finished, taking %s\n' % taken)
        self.logFile.close()
