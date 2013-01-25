from Domain.States import TestState
from Utils.Envcat import envcatRequest
from Utils import Network
from Utils.Configuration import ConfigurationManager

import os, sys, time, traceback
from multiprocessing import Queue
from multiprocessing.queues import Empty

class PythonNoseTest(object):
    __STOP_ENV_SERVER_CMD = 'play'

    def __init__(self   , description = '' , iterations = 0  , environment = '',
        testClass = None, testMethod = ''  , testFile = ''   , testId = 0,
        testStatus = '' , testTimeout = 500, invalid = False ,
        manualInspection = False, docstrings = [''], srcLoc = None):

        self.description = description
        self.iterations = int(iterations)
        self.environment = environment
        self.testClass = testClass
        self.testMethod = testMethod
        self.testFile = testFile
        self.testId = int(testId)
        self.testStatus = testStatus
        self.testTimeout = int(testTimeout)
        self.peer = None
        self.invalid = bool(invalid)
        self.manualInspection = bool(manualInspection)
        self.docstrings = docstrings if isinstance(docstrings, list) else [docstrings]
        self.startTime = 0
        self.duration = 0
        self.state = TestState.NORESLT()
        self.error = ''
        self.executed = False
        self.uniqueId = None
        self.testStage = False # Used for reboot helper
        self.iteration = 1
        self.srcLoc = srcLoc

        self.namespace = None

        self.__items = [
            "description", "iterations", "environment", "testClass",
            "testMethod", "testFile", "testId", "testStatus", "testTimeout",
            "peer", "invalid", "manualInspection", "docstrings", "startTime",
            "duration", "state", "error", "executed", "uniqueId", "testStage"
        ]

    def __eq__(self, other):
        for item in self.__items:
            if not hasattr(other, item) or \
            getattr(other, item) != getattr(self, item):
                return False
        return True

    def combineClassMethod(self):
        return self.testMethod if not self.testClass \
            else "%s.%s" % (self.testClass, self.testMethod)

    def getExecutionString(self):
        return "PythonNoseScript %s:%s" %(self.testFile, self.combineClassMethod())

    def __stopEnvServer(self):
        envcatRequest(self.__envServerHost,
            self.__envServerPort, self.__STOP_ENV_SERVER_CMD)
