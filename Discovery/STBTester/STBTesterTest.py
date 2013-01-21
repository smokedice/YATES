from Domain.States import TestState
from Utils import Network
from Utils.Configuration import ConfigurationManager

import os, sys, time, traceback
from multiprocessing import Queue
from multiprocessing.queues import Empty

class STBTesterTest(object):
    REQUIRED_DOCS = ['testid', 'teststatus']

    def __init__(self, sourceLoc, path, docs):
        if not all(x in docs.keys() for x in self.REQUIRED_DOCS):
            raise Exception('Invalid test configuration: %s' % path)

        self.description = docs.get('summary', '')
        self.iterations = int(docs.get('iterations', 1))
        self.environment = docs.get('environment', '') # TODO: Append STBTester ?
        self.srcLoc = sourceLoc
        self.testName = path.split(sourceLoc)[1][1:]
        self.testFile = os.path.join(path, 'test.py')
        self.testId = int(docs.get('testid'))
        self.testStatus = docs.get('teststatus')
        self.testTimeout = int(docs.get('testtimeout', 600))
        self.invalid = docs.get('invalid', '').lower() == 'true'
        self.manualInspection = docs.get('manualinspection', '').lower() == 'true'
        self.docstrings = [docs.get('summary', '')]

        self.startTime = 0
        self.duration = 0
        self.state = TestState.NORESLT()
        self.error = ''
        self.executed = False
        self.uniqueId = None
        self.testStage = False # Used for reboot helper
        self.iteration = 1
        self.peer = None
        self.namespace = None

        self.__items = [
            "description", "iterations", "environment", "testFile", "testId",
            "testStatus", "testTimeout", "peer", "invalid", "manualInspection",
            "docstrings", "startTime", "duration", "state", "error", "executed",
            "uniqueId", "testStage"
        ]

    def __eq__(self, other):
        for item in self.__items:
            if not hasattr(other, item) or \
            getattr(other, item) != getattr(self, item):
                return False
        return True

    def combineClassMethod(self):
        return self.testName

    def getExecutionString(self):
        return "STBTesterScript STBTesterTests %s" % self.testName
