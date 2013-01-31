from Domain.States import TestState as TestStateValues
from Utils import Network
from Domain.States import PeerState

import time, os, math, datetime
from Queue import Empty

class LogFileLogger(object):
    LOG_FILENAME = "log.txt"
    """ Log results and states to a log file """
    def __init__(self, config, loc, description, source):
        base = LogFileLogger.LOG_FILENAME
        logFileLoc = os.path.join(loc, base)
        self.startTime = time.time()

        if not os.path.exists(base):
            os.makedirs(base)

        if config.clear == 'false' or \
        os.path.exists(logFileLoc):
            mode = 'a'
        else: mode = 'w'
           
        self.logFile = open(logFileLoc, mode, 0)
        self.logFile.write("TAS Version: %s\n" % os.environ['TAS_VERSION'])
        self.logFile.write("Current Time: %s\n" % datetime.datetime.now())
        self.logFile.write("Execution Description: %s\n" % ",".join(description))
        self.logFile.write("Selected Tests:\n")

        self.logFile.write(
            ", ".join([ "\n\t%s" % str(y.testId).zfill(4)
            if x % 5 == 0
            else str(y.testId).zfill(4)
            for x,y in enumerate(source.getTests())]))

        self.logFile.write("\n\n")

    def logPeerState(self, peer, comment = None):
        """ Log a peer state change """
        now = datetime.datetime.now()
        comment = '' if not comment else ', %s' % comment
        self.logFile.write("%s: Peer %s (%s) has changed state to %s%s\n"
            %(now, peer.ipAddr, peer.macAddr, peer.state, comment))

    def logResult(self, test, files):
        """ When a test result has been processed update the database """
        now = datetime.datetime.now()
        if test.peer:
            self.logFile.write("%s: Peer %s (%s) has completed test %s, result %s\n"
                %(now, test.peer.ipAddr, test.peer.macAddr, test.testId, test.state))
        else:
           
            self.logFile.write('Test %s has been completed, result %s\n' %(now, test.testId))

    def logIteration(self, iteration):
        self.logFile.write('Executing iteration %d' % iteration)

    def shutdown(self):
        """ Stop all logging of results """
        # TODO: BUG: if execution is over 31 days this will fail
        sec = datetime.timedelta(0, time.time() - self.startTime)
        d = datetime.datetime(1,1,1) + sec
        taken = ('%d day(s), %d hour(s), %d minute(s) and %d second(s)' 
            %(d.day-1, d.hour, d.minute, d.second))
    
        self.logFile.write('Execution finished at %s, taking %s'
            %(datetime.datetime.now(), taken))
        self.logFile.close()
