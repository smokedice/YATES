import sys
import os
import traceback
from Utils.Logging import LogManager
import pdb
class TestCaseParser(object):
    def __init__(self, *args, **kwargs):
        self.logger = LogManager().getLogger(self.__class__.__name__)

    def parseTestCase(self, testCaseData, testDocs, testCases = None,
                        importErrors = None, syntaxErrors = None):
        '''
        Method, which parses the test case data retrieved from nose framework
        @param testCaseData: data about the test case including filepath, testcase
        @param testCases: dictionary of the testcases {path:[testcase]}
        @param testDocs: dict of dicts of docstrings {path:{case:[docstrings]}}
        @param importErrors: dictionary of import errors
        @param syntaxErrors: dictionary of syntax errors
        '''
        filepath, _, test = testCaseData
        pathname, basename = os.path.split(filepath)
        module_name = basename.replace(".py", "")
        for _path in (".", pathname):
            if _path not in sys.path:
                sys.path.append(_path)

        try:
            _module = __import__(module_name)
        except ImportError, exc:
            if importErrors != None:
                importErrors[filepath] = str(exc)
        except SyntaxError, exc:
            if syntaxErrors != None:
                syntaxErrors[filepath] = str(exc)
        except:
            self.logger.warn(traceback.format_exc())
        else:
            _case = _module
            self.__retrieveDoc(test, _case, filepath, testDocs)

    def __retrieveDoc(self, test, case, filepath, testDocs):
        '''
        Method, which retrieves the docstring for a specific testcase
        @param test: name of the test
        @param case: name of the testcase
        @param filepath: filepath to the test file
        @param testDocs: dict of dict of docstrings {path:{case:[docstrings]}}
        '''
        _case = case
        if test is not None:
            for _scase in test.split('.'):
                try:
                    _case = getattr(_case, _scase)
                    doc = _case.__doc__
                    if doc: self.__addTestDoc(testDocs, filepath, test, doc)

                except Exception:
                    self.logger.error(traceback.format_exc())

    def __addTestDoc(self, testDocs, path, test, doc):
        '''
        Procedure, which adds the new docstring to the dictionary of docstrings
        @param testDocs: dict of dict of docstrings {path:{case:[dostring]}}
        @param path: path to the test
        @param test: test name
        @param doc: test dosctring
        '''
        if path not in testDocs:
            testDocs[path] = {test:[doc]}
        else:
            if test not in testDocs[path]:
                testDocs[path][test] = [doc]
            else:
                testDocs[path][test].append(doc)

