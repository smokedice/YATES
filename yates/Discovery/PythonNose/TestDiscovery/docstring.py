import sys, os, traceback, StringIO, time, tempfile, pickle, glob, re, types
from yates.Utils.Logging import LogManager


def find_python_files(location, filePattern = '^(t|T)est.*\.py$'):
    ''' Find all Python files from a given location '''
    location = os.path.abspath(location)
    pattern = re.compile(filePattern)
    python_files = []

    for path, dirs, files in os.walk(location):
        if '/.' in path: continue

        for fle in files:
            if not pattern.match(fle): continue
            python_files.append(os.path.join(path, fle))

    return python_files

def reload_modules(location):
    ''' Reload of modules with simular folder names '''
    cwd = os.getcwd()
    if location != os.getcwd():
        os.chdir(location)

    for path, _, _ in os.walk('.'):
        if '/.' in path: continue
        key = path[2:].replace(os.path.sep, '.')
        if key not in sys.modules.keys(): continue
        reload(sys.modules[key])

    os.chdir(cwd)

def parse_test_file(test_root, test_path):
    ''' Parse a Python file to find test cases '''
    logger = LogManager().getLogger('parse_test_file')
    test_root = os.path.abspath(test_root)
    test_path = os.path.abspath(test_path)
    python_path = test_path[len(test_root)+1:-3].replace(os.path.sep, '.')
    file_name = python_path.split('.')[-1]

    if test_root not in sys.path:
        sys.path.insert(0, test_root)
    old_path = os.getcwd()
    os.chdir(test_root)
    reload_modules(test_root)

    try:
        module = __import__(python_path, globals(),
            locals(), fromlist=[file_name])
        return find_test_methods(module)
    except:
        logger.warn("Could not load test %s, \n%s"
            %(test_path, traceback.format_exc()))
    finally:
        os.chdir(old_path)

    return []

TEST_OBJ_PATT = re.compile('^(t|T)est.*$')
def find_test_methods(module):
    ''' Find all test methods within given module '''
    tests = []
    for attr_name in dir(module):
        if not TEST_OBJ_PATT.match(attr_name):
            continue

        obj = getattr(module, attr_name)
        within_cls = type(module) in [types.ClassType, types.TypeType]
        is_cls = type(obj) in [types.ClassType, types.TypeType]
        is_func = type(obj) in [types.FunctionType, types.MethodType]

        if not within_cls and is_cls:
            tests += find_test_methods(obj)
        elif is_func:
            cls = module if within_cls else None
            tests.append((cls, obj))

    return tests

def process_docstr(doc):
    ''' Convert a docstring into key->value pairs '''
    docstrings = {}

    for line in doc.splitlines():
        value = str(line.strip().decode('utf-8', errors = "ignore"))

        if len(value) == 0: continue
        elif value[0] == '@' and value.find(':') >= 2:
            k, v = value.split(':', 1)
            key, value = k[1:].strip(), v.strip()
        else:
            key = 'summary'

        if key in docstrings.keys():
            value = docstrings[key] + value
        docstrings[key] = value

    return docstrings

def gather_doc_str(cls, method):
    ''' Combine docstrings from method and cls '''
    buff = StringIO.StringIO()
    if cls != None: buff.write(cls.__doc__)
    buff.write(method.__doc__)
    value = buff.getvalue()
    buff.close()
    return value
