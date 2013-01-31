from Test.Group import Group
from Test.Source import Source
from Filters.PriorityFilter import PriorityFilter
from Filters.TestPackFilter import TestPackFilter
from Filters.TestFilter import TestFilter
from Utils import Network
from Utils.Configuration import ConfigurationManager

from StringIO import StringIO
from datetime import datetime
import os, time, traceback, tarfile

class TestGatherManager(object):
    DEFAULT_GROUP_NAME = 'DefaultGroup'
    DEFAULT_GROUP_DESC = 'Default Group'
    DEFAULT_LOCATION = 'Default Location'
    TAR_NAME = 'scripts.tar.gz'

    def __init__(self, tmpDir):
        self.tmpDir = tmpDir
        self.__testFilters = [ TestPackFilter(), TestFilter(), PriorityFilter() ]
        self.__testCreators = [ ]

        items = ConfigurationManager().getConfiguration('discovery').configuration
        configs = [ c for c in dir(items) if hasattr(getattr(items, c), 'enabled') ]

        execution = ConfigurationManager().getConfiguration('execution').configuration
        defaultTestTimeout = int(execution.defaultTimeout.PCDATA)
        iterations = int(execution.iterations.PCDATA)

        for name in configs:
            path = "Discovery/%s" % name
            config = getattr(items, name)
            if config.enabled == 'false': continue
            if not os.path.exists(path): raise Exception('Cannot find %s' % path)
            self.__testCreators.append(self.__loadTestCreator(path, config, defaultTestTimeout, iterations)) 
          
    def __loadTestCreator(self, path, config, defaultTestTimeout, iterations):
        """ Load test creator from a given path """
        name = os.path.basename(path)
        modulePath = path.replace('/', '.')
        clsName = modName = '%sDiscovery' % name

        mod = __import__(modulePath, fromlist = [ clsName ])
        return getattr(getattr(mod, modName), clsName)(config, path, defaultTestTimeout, iterations)

    def gatherTests(self):
        """ Discover all tests from all sources """
        tests, content = [], {}
        #content = { 'PythonNoseSrc' : testLoc, execName : self.__execScript }

        if len(self.__testCreators) == 0:
            raise Exception('No enabled test creators found')

        for creator in self.__testCreators:
            newTests = creator.createTests()
            if len(newTests) == 0:
                raise Exception('%s provided no tests!' % creator.__class__.__name__)

            tests += newTests
            content[creator.execScriptName] = creator.execScriptLocation
            content[creator.srcName] = creator.srcLocation

        testIds = []
        for test in tests:
            if test.testId not in testIds: continue
            raise Exception('Duplicate test ID %s' % test.testId)
        if len(tests) == 0: raise Exception('No tests found!')
        del testIds

        defGroup = Group(self.DEFAULT_GROUP_NAME,
            self.DEFAULT_GROUP_DESC, tests)
        source = Source(self.DEFAULT_LOCATION, defGroup)

        descBuffer = StringIO()
        for testFilter in self.__testFilters:
            source = testFilter.filterTests(source)
            descBuffer.write(testFilter.getAppliedFilterDescription())
        desc = descBuffer.getvalue()
        descBuffer.close()
 
        testSuiteName = "FIXME"
        dateTime = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S')
        macAddress = Network.getMacAddress()
        executionName = "%s_%s_%s" % (testSuiteName, dateTime, macAddress)
   
        self.__packDetails = (testSuiteName, str(desc),
            self.__getShortFilterDesc(), executionName, dateTime)

        self.__makeTar(**content)
        return source, desc

    def getPackDetails(self):
        return self.__packDetails

    def __makeTar(self, **paths):
        tarName = os.path.join(self.tmpDir,self.TAR_NAME)
        tar = tarfile.open(tarName, 'w:gz')

        for name, path in paths.items():
            tar.add(path, name)
        tar.close()

        return tar.name

    def __getShortFilterDesc(self):
        filters = [ tFilter.isEnabled() for tFilter in self.__testFilters ]
        testPackFiltered = filters[0]
        otherFilters = any(filters[1:])

        if not testPackFiltered and not otherFilters:
            return 'all' # No filters
        elif not testPackFiltered and otherFilters:
            return 'filtered' # Some filters, but no testpacks
        elif testPackFiltered and not otherFilters:
            return 'testpack' # Just a testpack filter
        return 'testpack_filtered' # Testpack and filters
