from Discovery.PythonNose.DBReader.DatabaseReader import SAPIDatabaseReader
from Discovery.PythonNose.TestDiscovery.TestDiscoveryWorker import TestDiscoveryWorker
import os

class PythonNoseDiscovery(object):
    def __init__(self, config, path, defaultTimeout, iterations):
        self.execScriptName = 'PythonNoseScript'
        self.execScriptLocation = os.path.join(path, 'PythonNoseScript')
        self.srcName = 'PythonNoseTests'
        self.srcLocation = os.path.abspath(config.SourceLocation.testRoot.PCDATA)
        self.config = config
        self.defaultTimeout = defaultTimeout
        self.iterations = iterations

    def createTests(self):
        """ Create PythonNose tests from the database or discovery mechs """
        for creator in [SAPIDatabaseReader, TestDiscoveryWorker]:
            inst = creator(self.config, self.defaultTimeout, self.iterations, self.srcName)
            if inst.enabled: return inst.createTests()
        return []
