from Utils.Configuration import ConfigurationManager
from gnosis.xml.objectify._objectify import _XO_
import sys, argparse

# TODO: what happens if the same key is used multiple times?
# Need to be able to track the modifications & then add array items?
# TODO: case sensitive is shite

class ArgumentParser(object):
    def __init__(self, output = sys.stdout):
        self.output = output
        self.configLoc = None
        self.monitor = False

        if '--monitor' in sys.argv:
            self.monitor = True
            return

        if '--config' in sys.argv:
            index = sys.argv.index('--config') + 1
            self.configLoc = sys.argv[index]
            del sys.argv[index]
            del sys.argv[index - 1]

        self.configManager = ConfigurationManager(self.configLoc)

    def parse_args(self):
        configs = self.configManager.configurationNames()
        configs = [ self.configManager.getConfiguration(n) for n in configs ]
        parser = argparse.ArgumentParser()

        for config in configs:
            paths = self._process_path(config.configuration)
            for ns, value in paths or []:
                parser.add_argument('--%s' % ns)

        parser.add_argument('--config', '-c', help ='Configuration directory location')
        parser.add_argument('--monitor', '-m', help = 'Monitor UDP broadcasts for slave heartbeats', action="store_true")

        for key, value in vars(parser.parse_args()).items():
            if value == None or key == 'monitor': continue
            xml_name, path_parts = key.split('.', 1)
            path_parts = path_parts.split('.')
            config = self.configManager.getConfiguration(xml_name)
            self.__processOverride(config.configuration, path_parts, value)
        self.configManager.revalidateXMLs()

    def _process_path(self, root_conf, namespace = None):
        if isinstance(root_conf, unicode):
            return [(namespace, str(root_conf))]
        elif not namespace:
            namespace = root_conf.__class__.__name__[4:]

        # Gather objects to process
        objs = [ (name, getattr(root_conf, name))
            for name in dir(root_conf)
            if self._filter_objs(root_conf, name) ]
        if len(objs) == 0: return

        results = []
        for name, obj in objs: # Update namespace and iterate
            nm = "%s.%s" % (namespace, name) if name != "PCDATA" else namespace
            results += self._process_path(obj, nm) or []
        return results

    def _filter_objs(self, root_conf, name):
        obj = getattr(root_conf, name)

        if '_' in (name[0], name[-1]): return False
        elif name.startswith('xmlns') or name.startswith('xsi'): return False
        if name == "parent": return False

        isCorrectType = isinstance(obj, _XO_) or isinstance(obj, unicode)
        return isCorrectType

    def __processOverride(self, root, path, value):
        element_name = path.pop(0)
        new_root = getattr(root, element_name, None) 

        if not new_root:
            raise Exception("Invalid configuration")
        elif len(path) > 0:
            return self.__processOverride(new_root, path, value)

        value = unicode(value)
        if isinstance(new_root, _XO_): setattr(root, 'PCDATA', value)
        elif isinstance(new_root, unicode): setattr(root, element_name, value)
        else: raise Exception("Invalid configuration")
