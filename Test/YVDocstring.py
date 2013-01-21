import re

class YVDocstring(object):
    """
    @summary: Simple <single-line> docstring parsing!
    @attention: For the purposes of a non-ui controller, 
                all it cares about is if a @YVManual tag 
                is specified or not.
    """

    # Docstring tags:
    # YV specific:
    DBUS_API = "@YVDBusApi:"
    DEV_API = "@YVDevApi:"
    CPP_API = "@YVCppApi:"
    CPF = "@Yvcpf:"
    MANUAL = "@YVManual:"
    SPEC = "@YVSpec:"
    TIMEOUT = "@timeout:"     # Timeout in seconds.
    YVTESTASSET = "@YVTestAsset:"

    # Python generic:
    SUMMARY = "@summary:"
    ATTENTION = "@attention:"
    WARNING = "@warning:"
    NOTE = "@note:"
    PRECONDITION = "@precondition:"

    # DTVL specific: 
    MOCK = "@mock:"
    ENVIRONMENT = "@environment:"
    STATUS = "@status:"
    TEST = "@test:"
    DTVLSPEC = "@DTVLSPEC:"

    _tags = [
        DBUS_API, DEV_API, CPP_API, CPF, MANUAL, SPEC,
        SUMMARY, YVTESTASSET, ATTENTION, WARNING, TIMEOUT,
        PRECONDITION, STATUS, NOTE, MOCK, TEST,
        ENVIRONMENT, DTVLSPEC ]

    def __init__(self, docStrings):
        '''
        Constructor for the class
        @param docStrings: A list of strings 
        '''
        self._docStrings = docStrings
        self._docs = {}
        self._unknown = {}
        self._parse()

    def _parse(self):
        '''
        Method which parses the docstring for a testcase. It includes
        all the lines of the docstring comment
        '''
        if not self._docStrings:
            return

        for i in range(0, len(self._docStrings)):
            if self._docStrings[i] and len(self._docStrings[i]) > 0:
                self._docStrings[i] = self._docStrings[i].__str__()

        for docstring in self._docStrings:
            prev_tag = None
            if docstring is None: continue
            lines = docstring.splitlines()
            for line in lines:
                self._parseLine(line, prev_tag)


    def _parseLine(self, line, prev_tag):
        '''
        Method which parses the single line of the docstring.
        @param line: The line, which should be parsed
        @param prev_tag: The previous tag in the docstring. If no
                previous tag and the current line doesn't contain
                any tag, then it will be considered as multiline
                SUMMARY comment
        '''
        if line is not None:
            doctype = 0
            # if the beginning of the line more than 8 spaces
            # then it is the method comment, and the summary
            # can be included into the docstring
            if re.match('        ', line):
                doctype = 1

            line = line.strip()
            if len(line) > 0:
                tag, value = self._getTag(line)

                if tag is not None:
                    prev_tag = tag

                    if tag not in self._docs:
                        self._docs[tag] = []

                    self._docs[tag].append(value)
                # if the were no previous tags, and the next
                # line is without a tag too, then this is the
                # next line of the SUMMARY
                elif self._checkUnknownTag(line) == True:
                    pass
                elif prev_tag == None:
                    if doctype == 1:
                        if self.SUMMARY not in self._docs:
                            self._docs[self.SUMMARY] = []
                            self._docs[self.SUMMARY].append("")
                        if self._docs[self.SUMMARY][0] == "":
                            self._docs[self.SUMMARY][0] = value
                        else:
                            self._docs[self.SUMMARY][0] = \
                                self._docs[self.SUMMARY][0] + " " + value
                # if there was a TAG found before then this line
                # without a tag belong to previous tag
                # only MANUAL and PRECONDITION may be multiline except for 
                # SUMMARY which is processed in previous branch    
                elif prev_tag == self.MANUAL or prev_tag == self.PRECONDITION:
                    self._docs[prev_tag][0] = \
                            self._docs[prev_tag][0] + " " + value


    def _getTag(self, line):
        '''
        Private method, which retrieves the tag from a line
        @param line: line which should be parsed
        @return: Tuple, which includes the tag name and the line itself
        '''
        for tag in self._tags:
            if line.startswith(tag) is True:
                _, match, post = line.partition(tag)

                if match and post:
                    return (tag, post.strip())

        return (None, line)

    def _checkUnknownTag(self, line):
        lline = line.split(" ")
        if lline[0].startswith("@") is True:
            if lline[0] not in self._tags:
                _, match, post = line.partition(lline[0])

                if match not in self._unknown:
                    self._unknown[match] = []

                self._unknown[match].append(post)

                return True

        return False

    def getUnknown(self):
        return self._unknown

    def getTags(self):
        '''
        Method, which returns the tags with the contents 
        @return: dictionary of docstrings, where the key is the tag
                _docs    {tag:docstrings}
        '''
        return self._docs

    def hasField(self, field):
        '''
        Method, which checks whether the requested tag exists in the 
        docstring.
        @param field: The name of the field
        @return: boolean valie whether the field exists or no
        '''
        return field in self._docs

    def getField(self, field):
        '''
        Method, which returns the value of the field.
        @note: Method is unsafe, because in case the field does not
        exist, the exception will be thrown. So before calling the 
        method, make sure, that the field exists by calling 
        YVDocstring.hasField()
        @param field: The name of the field
        @return: the value of the field
        '''
        assert self.hasField(field) is True

        return self._docs[field]

    def getFieldOrDefault(self, field, default = ""):
        '''
        Method, which returns the value of the field or the default value
        @note: Method is safe, in case the field does not exist, the 
               default value will be returned
        @param field: The name of the field
        @param default: The default value to be returned in case the field
               does not exist
        @return: The value of the field
        '''
        try:
            tags = self._docs[field]
            result = ",\r\n".join(tags)
        except:
            return default
        else:
            return result

    @staticmethod
    def convertToYVDocstring(testDocs):
        '''
        Function, which converts the original string docstrings acquired form
        nose framework into YVDocstring object, which contains YouView specific
        docstrings
        @param testDocs: dict of dict of docstrings {path:{case:[docstrings]}}
        @return: dict of dict of YVDocstring {path:{case:YVDocstring}}
        '''
        if testDocs != None:
            for key in testDocs.keys():
                for case in testDocs[key].keys():
                    testDocs[key][case] = YVDocstring(testDocs[key][case])

        return testDocs