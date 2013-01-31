from distutils.core import setup
from distutils.sysconfig import get_python_lib
from os.path import join
import glob, os

CONFIG_DIR = join(os.path.dirname(__file__), "yates", "config")
CONFIG_FILES = glob.glob(join(CONFIG_DIR, "*.xml"))
CONFIG_XSDS = glob.glob(join(CONFIG_DIR, "validation", "*.xsd"))

DOCS_DIR = join(os.path.dirname(__file__), "yates", "Docs")
DOCS_FILES = glob.glob(join(DOCS_DIR, "*.*"))
DOCS_CONF_FILES = glob.glob(join(DOCS_DIR, "config", "*.html"))

ROOT = join(get_python_lib(), 'yates')

setup(
    name='YATES',
    version='0.1.0',
    author='Mark Wallsgrove, Vladimirs Ambrosovs',
    author_email='mark.wallsgrove@gmail.com',
    packages=[
        'yates',
        'yates.Filters',
        'yates.Discovery',
        'yates.Discovery.STBTester',
        'yates.Discovery.PythonNose',
        'yates.Discovery.PythonNose.DBReader',
        'yates.Discovery.PythonNose.DBReader.Model',
        'yates.Discovery.PythonNose.TestDiscovery',
        'yates.TestEnvironment',
        'yates.TestGather',
        'yates.Test',
        'yates.Network',
        'yates.Utils',
        'yates.Domain',
        'yates.TestDistribution',
        'yates.Results',
        'yates.Results.Model',
        'yates.Results.Loggers'
    ],
    url='http://github.com/smokedice/YATES',
    license='',
    description='Yet Another Test Execution System',
    data_files=[
        (join(ROOT, 'config'), CONFIG_FILES),
        (join(ROOT, 'config/validation'), CONFIG_XSDS),
        (join(ROOT, 'Docs'), DOCS_FILES),
        (join(ROOT, 'Docs/config'), DOCS_CONF_FILES),
    ],
    package_data={
        'yates.Discovery.STBTester' : ['STBTesterScript'],
        'yates.Discovery.PythonNose' : ['PythonNoseScript'],
    },
    #long_description=open('README.rst').read(),
    install_requires=[
        "Gnosis==0.1.0",
        "Twisted==12.3.0",
        "argparse==1.2.1",
        "distribute==0.6.24",
        "mechanize==0.2.5",
        "minixsv==0.9.0",
        "peewee==1.0.0",
        "pyasn1==0.1.6",
        "pycrypto==2.6",
        "rsa==3.1.1",
        "wsgiref==0.1.2",
        "zope.interface==4.0.3",
    ],
)
