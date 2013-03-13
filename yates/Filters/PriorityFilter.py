from yates.Test.Group import Group
from yates.Utils.Configuration import ConfigurationManager

from StringIO import StringIO
import re

class PriorityFilter(object):
    '''
    Priority filter performs the division of list of tests into
    priority groups, or a simple sorting
    '''

    class PriorityDirection(object):
        ''' Enumeration class which defines the direction of sorting '''
        DESCENDING = 1
        ASCENDING = 0

    def __init__(self):
        ''' @param filterName: The name of the filter XML configuration '''
        self.configurationManager = ConfigurationManager()
        self.config = self.configurationManager.getConfiguration('filters')
        self.__filterString = ""

        if not hasattr(self.config.getConfiguration(), 'PriorityFilter'):
            self.enabled = False
            return

        self.priorityFilterCfg = self.config.getConfiguration().PriorityFilter
        if self.priorityFilterCfg.enabled != "true":
            self.enabled = False
        else: self.enabled = True

    def filterTests(self, source):
        '''
        If the values of priority are specified in the configuration, then
        the method divides the default group into priority groups according
        to specified values. If the values are not specified, then the
        method performs sorting of the existing groups
        @param source: the source object
        @return the modified source object with applied priority
        '''
        if not self.enabled:
            return source

        self.__filterString = self.__createDescription(self.priorityFilterCfg)
        self.attr = self.priorityFilterCfg.parameter.PCDATA

        self.__sort(source, self.attr, self.priorityFilterCfg.direction.PCDATA)
        if hasattr(self.priorityFilterCfg.values, 'value'):
            self.__group(source, self.attr, self.priorityFilterCfg.values)
        return source

    def isEnabled(self):
        return self.enabled

    def __createDescription(self, priorityFilterCfg):
        direct = priorityFilterCfg.direction.PCDATA
        attr = priorityFilterCfg.parameter.PCDATA

        descBuffer = StringIO()
        descBuffer.write('Priority Filter: %s, Direction: %s' % (attr, direct))

        if not hasattr(priorityFilterCfg.values, 'value'):
            result = "%s\n" % descBuffer.getvalue()
            descBuffer.close()
            return result

        descBuffer.write(', Values:')
        for val in priorityFilterCfg.values.value:
            descBuffer.write(' ')
            descBuffer.write(val.PCDATA)

        descBuffer.write("\n")
        result = descBuffer.getvalue()
        descBuffer.close()
        return result

    def __group(self, source, attr, valuesNode):
        '''
        Performs the grouping of the tests by priority. If more than
        one group exists, then no modifications applied
        @param groups: the list of source groups (expected 1 default group)
        @param attr: the attribute by which divide into priorities
        @param values: the list of values, of priorities
        '''
        defGroup = source.groups[0]
        if len(source.groups) != 1 or defGroup.name != 'DefaultGroup':
            return

        defaultFilter = self.__literalFilter
        if hasattr(valuesNode, 'type') and valuesNode.type == 'regex':
            defaultFilter = self.__regexFilter

        values = valuesNode.value
        if not isinstance(values, list):
            values = [values]

        for value in values:
            tests = self.__filterTests(value, defGroup, attr, defaultFilter)
            if len(tests) == 0: continue

            newGroup = Group(value, '%s priority group' % attr)
            newGroup.tests = tests
            source.groups.insert(0, newGroup)

        if len(defGroup.tests) == 0:
            source.groups.remove(defGroup)

    def __filterTests(self, value, defaultGroup, attr, defaultFilter):
        tests = []
        for test in defaultGroup.tests[:]:
            content = getattr(test, attr, '')

            if hasattr(value, 'type'):
                result = self.__getFilter(value.type)(value.PCDATA, content)
            else: result = defaultFilter(value.PCDATA, content)

            if not result: continue
            tests.append(test)
            defaultGroup.removeTest(test)
        return tests

    def __getFilter(self, name):
        if name != 'regex': return self.__literalFilter
        return self.__regexFilter

    def __literalFilter(self, value, content):
        return value == content

    def __regexFilter(self, value, content):
        return re.match(value, content) != None

    def __sort(self, source, attr, direction):
        '''
        Performs the sorting of the tests in the group. Method is used
        when no priority values are specified.
        @param tests: the list of tests in the group
        @param attr: the attribute by which the sorting should be applied
        @param direction: ascending or descending direction
        @return: the sorted list of tests
        '''
        if direction != 'ascending':
            direction = self.PriorityDirection.DESCENDING
        else: direction = self.PriorityDirection.ASCENDING

        for group in source.groups:
            tests = sorted(group.tests,
                key = lambda test: getattr(test, attr, None),
                reverse = direction)
            group.tests = tests

    def getAppliedFilterDescription(self):
        return self.__filterString
