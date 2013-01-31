from Utils.Configuration import ConfigurationManager
from gnosis.xml.objectify._objectify import _XO_
from sys import stdout
import sys

# TODO: what happens if the same key is used multiple times?
# Need to be able to track the modifications & then add array items?
# TODO: case sensitive is shite

class ArgumentParser(object):
    def __init__(self, output = stdout):
        self.output = output
        self.configLoc = None
        self.monitor = False

        if '--config' in sys.argv:
            index = sys.argv.index('--config') + 1
            self.configLoc = sys.argv[index]
            del sys.argv[index]
            del sys.argv[index - 1]
        elif '--monitor' in sys.argv:
            self.monitor = True
        elif '--help' in sys.argv:
            self.getHelpContent()
        else: 
            self.configManager = ConfigurationManager(self.configLoc)

    def parseArgs(self, argv = None):
        if not argv: argv = sys.argv[1:]

        if not len(argv):
            return True

        return self.__overrideValues(argv)

    def __overrideValues(self, argv):
        if not len(argv) % 2 == 0:
            raise Exception(
                'System arguments should be paired '
                'key -> value. Uneven pairing')

        # Process each key/value pair
        for index in range(0, len(argv), 2):
            self.overrideValue(argv[index], argv[index + 1])
        self.configManager.revalidateXMLs()
        return True

    def overrideValue(self, key, value):
        if key.find('.') == -1:
            raise Exception('Key is invalid: %s' % key)

        xmlName, pathParts = key.split('.', 1)
        pathParts = pathParts.split('.')
        config = self.configManager.getConfiguration(xmlName)

        try:
            self.__processOverride(config.configuration, pathParts, value)
        except Exception, e:
            raise Exception(e)

    def __processOverride(self, root, pathParts, value):
        path = pathParts[0]
        pathParts = pathParts[1:]

        if not hasattr(root, path):
            raise Exception("Invalid configuration")

        if len(pathParts) > 0:
            return self.__processOverride(
                getattr(root, path), pathParts, value)

        obj = getattr(root, path)
        value = unicode(value)

        if isinstance(obj, _XO_):
            setattr(obj, 'PCDATA', value)
        elif isinstance(obj, unicode):
            setattr(root, path, value)
        else: raise Exception("Invalid configuration")

    def getHelpContent(self):
        configs = self.configManager.configurationNames()
        configs = [ self.configManager.getConfiguration(n) for n in configs ]

        for config in configs:
            self.__processPath(config.configuration)
        self.output.write("  --help\n  --config %s\n  --monitor\n" % (self.configLoc or '.'))
        return False # Should stop the execution

    def __processPath(self, rootConfig, namespace = None):
        if isinstance(rootConfig, unicode):
            return self.output.write("  %s %s\n" % (namespace, str(rootConfig)))
        elif not namespace:
            namespace = rootConfig.__class__.__name__[4:]

        # Gather objects to process
        objs = [ (name, getattr(rootConfig, name))
            for name in dir(rootConfig)
            if self.__filterObjects(rootConfig, name)
        ]

        for name, obj in objs: # Update namespace and iterate
            nm = "%s.%s" % (namespace, name) if name != "PCDATA" else namespace
            self.__processPath(obj, nm)

    def __filterObjects(self, rootConfig, name):
        obj = getattr(rootConfig, name)
        if name == "parent": return False
        if name.startswith("_") or name.endswith("_"): return False
        if name.startswith('xmlns') or name.startswith('xsi'): return False

        isCorrectType = isinstance(obj, _XO_) or isinstance(obj, unicode)
        if not isCorrectType: return False

        return True
