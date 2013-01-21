from Discovery.PythonNose.PythonNoseTest import PythonNoseTest
from Results.Model import ModelUtils
from TestGather.DBReader.Model.Tests import Tests
from Utils.Configuration import ConfigurationManager
import os

class SAPIDatabaseReader(object):
    def __init__(self, config, defaultTimeout, iterations, srcLoc):
        self.databaseWorkerConfig = config.DatabaseReader
        self.enabled = self.databaseWorkerConfig.enabled == 'true'

        databaseLocation = ''
        if hasattr(self.databaseWorkerConfig, 'location'):
            databaseLocation = self.databaseWorkerConfig.location.PCDATA

        self.defaultTimeout = defaultTimeout
        self.iterations = iterations
        self.srcLoc = srcLoc

        if self.enabled and not os.path.isfile(databaseLocation):
            raise Exception("SAPIDatabaseReader, Cannont find database: %s" % databaseLocation)
        elif self.enabled:
            ModelUtils.MasterBaseModel.Meta.database.init(databaseLocation)

    def createTests(self):
        if not self.isEnabled():
            return []

        tests = []
        for test in Tests.select():
            nameParts = test.testName.split('.')
            if len(nameParts) == 2:
                className = nameParts[0]
                methodName = nameParts[1]
            elif len(nameParts) == 1:
                className = None
                methodName = nameParts[0]
            else:
                raise Exception('Invalid test name')

            tests.append(PythonNose(
                iterations = self.iterations,
                environment = test.environment,
                testClass = className,
                testMethod = methodName,
                testFile = test.relativePath,
                testId = test.testId,
                testStatus = test.status,
                testTimeout = test.timeout or self.defaultTimeout,
                manualInspection = test.manual,
                srcLoc = self.srcLoc
            ))

        return tests
