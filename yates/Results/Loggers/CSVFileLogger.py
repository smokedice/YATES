from Domain.States import TestState as TestStateValues
from Utils import Network
from Domain.States import PeerState

import time, os, math, datetime
from Queue import Empty

class CSVFileLogger(object):
    CSV_FILENAME = "results.csv"

    """ Log results and states to a log file """
    def __init__(self, config, loc, description, source):
        base = CSVFileLogger.CSV_FILENAME
        logFileLoc = os.path.join(loc, base)
        self.startTime = time.time()

        if not os.path.exists(base):
            os.makedirs(base)

        if config.clear == 'false' or \
        os.path.exists(logFileLoc):
            self.logFile = open(logFileLoc, 'a', 0)
        else: 
            self.logFile = open(logFileLoc, 'w', 0)
            self.logFile.write("ipAddr,macAddr,testId,startTime,duration,now,result\n")

    def logPeerState(self, peer, comment = None):
        """ Log a peer state change """
        pass

    def logResult(self, test, files):
        """ When a test result has been processed update the database """
        ipAddr = macAddr = None
        if test.peer:
            ipAddr = test.peer.ipAddr
            macAddr = test.peer.macAddr

        self.logFile.write("%s,%s,%s,%s,%s,%s,%s\n"
            %(ipAddr, macAddr, test.testId,
            test.startTime, test.duration, time.time(), test.state))

    def logIteration(self, iteration):
        pass

    def shutdown(self):
        """ Stop all logging of results """
        self.logFile.close()
