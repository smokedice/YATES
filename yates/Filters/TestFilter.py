from Utils.Configuration import ConfigurationManager
import re

class TestFilter(object):
    '''
    Test filter performs the filtering of the tests in the groups
    It may leave the specified tests in the list or exclude those
    from the list depending on the direction specified
    '''
    TEST_FILTER_CONFIG_ATTR = 'TestFilter'
    CONFIG_DIRECTION_EXCLUDE = 'exclude'
    CONFIG_ENABLED_FALSE = 'false'

    class FilterDirection(object):
        '''
        The enumeration class, which specifies the direction of the
        filtering. EXCLUDE defines that the tests which contain
        filtering values will be removed from the test list. INCLUDE
        value defines that only tests which contain filtering values
        will be left in the test list
        '''
        EXCLUDE = False
        INCLUDE = True

    def __init__(self):
        ''' @param filterName: the name of the filter XML configuration '''
        self.attr = ''
        self.direction = self.FilterDirection.INCLUDE
        self.values = []
        self.configurationManager = ConfigurationManager()
        self.config = self.configurationManager.getConfiguration('filters')
        self.__filterString = ""

    def filterTests(self, source):
        '''
        Filters the tests in the source object.
        @param source: the source object
        @return: the source object with filtered test list
        '''

        if not hasattr(self.config.getConfiguration(),
        self.TEST_FILTER_CONFIG_ATTR):
            return source

        for testFilter in self.config.getConfiguration().TestFilter:
            if testFilter.enabled == self.CONFIG_ENABLED_FALSE:
                continue

            if not hasattr(testFilter.values, 'value'):
                continue

            self.attr = testFilter.parameter.PCDATA
            direct = testFilter.direction.PCDATA

            self.__filterString += "Filter: %s, Direction: %s, Values:" % (self.attr, direct)
            self.values = []

            if direct == self.CONFIG_DIRECTION_EXCLUDE:
                self.direction = self.FilterDirection.EXCLUDE
            else: self.direction = self.FilterDirection.INCLUDE

            self.globalFilter = self.__matchesLiteral
            if hasattr(testFilter.values, 'type') and \
            testFilter.values.type == 'regex':
                self.globalFilter = self.__matchesRegex

            for val in testFilter.values.value:
                self.__filterString += " %s" % (val.PCDATA)
                self.values.append(val)
            self.__filterString += "\n"

            for group in source.groups:
                group.tests = filter(self.__filterContent, group.tests)

        return source

    def isEnabled(self):
        if not hasattr(self.config.getConfiguration(),
        self.TEST_FILTER_CONFIG_ATTR):
            return False

        for testFilter in self.config.getConfiguration().TestFilter:
            if testFilter.enabled == 'true':
                return True
        return False

    def __filterContent(self, test):
        """ Filter content based on the values """
        matches = []
        for value in self.values:
            matches.append(self.__getResult(value, test))

        if True in matches: return self.direction
        return not self.direction

    def __getResult(self, value, test):
        """ Test if a test attribute matches a value """
        content = getattr(test, self.attr, "")
        if hasattr(value, 'type'): # Use the value filter type
            return self.__getFilter(value.type)(value, test, content)
        return self.globalFilter(value, test, content)

    def __getFilter(self, name):
        """ Get the filter by name """
        if name == 'regex': return self.__matchesRegex
        return self.__matchesLiteral

    def __matchesLiteral(self, value, test, content):
        '''
        Method is used for filter() function
        @return: True or False depending on whether the test attribute value
            is in the configured value list
        '''
        return str(content) == str(value.PCDATA)

    def __matchesRegex(self, value, test, content):
        """ Matches the value against a regex pattern """
        if re.match(str(value.PCDATA), str(content)):
            return True
        return False

    def getAppliedFilterDescription(self):
        return self.__filterString
