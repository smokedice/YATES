from Results.Loggers.FileSystemLogger import FileSystemLogger
from Results.Loggers.SQLLiteLogger import SqlLiteLogger
from Results.Loggers.LogFileLogger import LogFileLogger
from Results.Loggers.CSVFileLogger import CSVFileLogger
from Results.Loggers.TRMSLogger import TrmsLogger
from Utils.Configuration import ConfigurationManager
from Utils.Logging import LogManager
from Utils.Singleton import Singleton

from threading import RLock
import os, time

class ResultWorker(Singleton):
    _instance = None
    _instanceLock = RLock()
    
    RESULT_PREFIX = "results"

    def _setup(self, desc, source):
        self._logger = LogManager().getLogger(self.__class__.__name__)
        self.config = ConfigurationManager() \
            .getConfiguration('resultworker').configuration.output

        self.desc = desc
        self.source = source
        self.loggers = []
        self.trmsLogger = None
        self.uniqueID = 0
       
        resdir = "%s-%s-%s" % (ResultWorker.RESULT_PREFIX, 
            time.strftime("%Y%m%d%H%M"), str(os.getegid()))

        self.location = os.path.join(self.config.location, resdir)
        if not os.path.exists(self.location):
            os.makedirs(self.location)

        self.__createLoggers()

    def __createLoggers(self):
        # Enable the TRMS Loggers
        if hasattr(self.config.trmsLoggers, 'trms'):
            trmsLoggers = self.config.trmsLoggers.trms
            trmsLoggers = trmsLoggers if isinstance(trmsLoggers, list) \
                else [trmsLoggers]

            for trmsLoggerConfig in trmsLoggers:
                if trmsLoggerConfig.enabled == 'true':
                    self.loggers.append(TrmsLogger(trmsLoggerConfig))

        if self.config.fileSystem.enabled == 'true':
            self.loggers.append(FileSystemLogger(self.config.fileSystem, self.location, self.trmsLogger))

        if self.config.sqlLite.enabled == 'true':
            sqllogger = SqlLiteLogger(self.config.sqlLite, self.location, self.desc, self.source)
            self.loggers.append(sqllogger)

        if self.config.logFile.enabled == 'true':
            logFile = LogFileLogger(self.config.logFile, self.location, self.desc, self.source)
            self.loggers.append(logFile)

        if self.config.csvFile.enabled == 'true':
            csvFile = CSVFileLogger(self.config.csvFile, self.location, self.desc, self.source)
            self.loggers.append(csvFile)

    def reportIteration(self, iteration):
        for logger in self.loggers:
            logger.logIteration(iteration)

    def reportState(self, peer, comment = None):
        for logger in self.loggers:
            logger.logPeerState(peer, comment)
 
    def report(self, test, files, peer):
        """ Store a tests content onto the file system """
        test.uniqueId = str(self.uniqueID)
        self.uniqueID += 1
        test.peer = peer

        for logger in self.loggers:
            logger.logResult(test, files)

    def shutdown(self):
        """ Shutdown this singleton """
        while len(self.loggers):
            self.loggers.pop().shutdown()
