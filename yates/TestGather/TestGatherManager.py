from yates.Test.Group import Group
from yates.Test.Source import Source
from yates.Filters.PriorityFilter import PriorityFilter
from yates.Filters.TestPackFilter import TestPackFilter
from yates.Filters.TestFilter import TestFilter
from yates.Utils import Network
from yates.Utils.Configuration import ConfigurationManager

from StringIO import StringIO
from datetime import datetime
import os
import time
import tarfile

import yates
YPATH = os.path.abspath(os.path.split(
    yates.__file__)[0])
IPATH = os.path.sep.join(YPATH.split(os.path.sep)[:-1])


class TestGatherManager(object):
    DEFAULT_GROUP_NAME = 'DefaultGroup'
    DEFAULT_GROUP_DESC = 'Default Group'
    DEFAULT_LOCATION = 'Default Location'
    TAR_NAME = 'scripts.tar.gz'

    def __init__(self, tmpDir):
        self.tmpDir = tmpDir
        self.__testFilters = [TestPackFilter(), TestFilter(), PriorityFilter()]
        self.__testCreators = []

        items = ConfigurationManager().getConfiguration('discovery').configuration
        configs = [c for c in dir(items) if hasattr(getattr(items, c), 'enabled')]

        execution = ConfigurationManager().getConfiguration('execution').configuration
        defaultTestTimeout = int(execution.defaultTimeout.PCDATA)
        iterations = int(execution.iterations.PCDATA)

        for name in configs:
            path = os.path.join('yates', 'Discovery', name)
            config = getattr(items, name)

            if config.enabled == 'false':
                continue

            self.__testCreators.append(self.__loadTestCreator(
                path, config, defaultTestTimeout, iterations))

    def __loadTestCreator(self, path, config, defaultTestTimeout, iterations):
        """ Load test creator from a given path """
        name = os.path.basename(path)
        modulePath = path.replace('/', '.')
        clsName = modName = '%sDiscovery' % name
        full_path = os.path.join(IPATH, path)

        mod = __import__(modulePath, fromlist=[clsName])
        return getattr(getattr(mod, modName), clsName)(
            config, full_path, defaultTestTimeout, iterations)

    def gatherTests(self):
        """ Discover all tests from all sources """
        tests, content = [], {}
        execution = ConfigurationManager().getConfiguration('execution').configuration

        if execution.scripts.enabled == 'true':
            if not os.path.exists(execution.scripts.PCDATA):
                raise Exception('Invalid configuration. Executions scripts do not exist')
            content['tools'] = execution.scripts.PCDATA

        if len(self.__testCreators) == 0:
            raise Exception('No enabled test creators found')

        for creator in self.__testCreators:
            newTests = creator.createTests()
            if len(newTests) == 0:
                raise Exception('%s provided no tests!' % creator.__class__.__name__)

            tests += newTests
            content[creator.execScriptName] = creator.execScriptLocation
            content[creator.srcName] = creator.srcLocation

        defGroup = Group(self.DEFAULT_GROUP_NAME,
                         self.DEFAULT_GROUP_DESC, tests)
        source = Source(self.DEFAULT_LOCATION, defGroup)

        descBuffer = StringIO()
        for testFilter in self.__testFilters:
            testFilter.filterTests(source)
            descBuffer.write(testFilter.getAppliedFilterDescription())
        desc = descBuffer.getvalue()
        descBuffer.close()

        if len(tests) == 0:
            raise Exception('No tests found!')

        testIds = set()
        for test in tests:
            if test.testId in testIds:
                raise Exception('Duplicate test ID %s' % test.testId)
            testIds.add(test.testId)

        # TODO: where does this come from?
        testSuiteName = "FIXME"
        dateTime = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S')
        macAddress = Network.getMacAddress()
        executionName = "%s_%s_%s" % (testSuiteName, dateTime, macAddress)

        self.__packDetails = (
            testSuiteName,
            str(desc),
            self.__getShortFilterDesc(),
            executionName,
            dateTime)

        self.__makeTar(**content)
        return source, desc

    def getPackDetails(self):
        return self.__packDetails

    def __makeTar(self, **paths):
        tarName = os.path.join(self.tmpDir, self.TAR_NAME)
        tar = tarfile.open(tarName, 'w:gz')

        for name, path in paths.items():
            tar.add(path, name)

        tar.close()
        return tar.name

    def __getShortFilterDesc(self):
        filters = [tFilter.isEnabled() for tFilter in self.__testFilters]
        testPackFiltered = filters[0]
        otherFilters = any(filters[1:])

        if not testPackFiltered and not otherFilters:
            # No filters
            return 'all'
        elif not testPackFiltered and otherFilters:
            # Some filters, but no testpacks
            return 'filtered'
        elif testPackFiltered and not otherFilters:
            # Just a testpack filter
            return 'testpack'

        # Testpack and filters
        return 'testpack_filtered'
