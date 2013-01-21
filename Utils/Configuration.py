from Utils.Objectify import Objectify
from Utils.Singleton import Singleton
from Utils.Logging import LogManager
from glob import glob
from threading import RLock
import os

class ConfigurationManager(Singleton):
    _instance = None
    _instanceLock = RLock()
    
    def _setup(self, cwd=None):
        orgCwd = os.getcwd()
        existingCwd = os.path.join(os.getcwd(), 'config')
        if not cwd: cwd = existingCwd
        self.logger = LogManager().getLogger(self.__class__.__name__)

        try:
            xml = None
            os.chdir(cwd)
            self.xmls = {}

            for xml in glob("*.xml"):
                name = xml.split("/")[-1].split(".")[0]
                xsd = "validation/%s.xsd" % name
                if not os.path.exists(xsd): continue
                self.loadConfiguration(xml, xsd)
        finally:
            os.chdir(orgCwd)

    def loadConfiguration(self, xml, xsd):
        """
        Load and validate the configuration file provided
        @param xml: XML to convert into an object
        @param xsd: XSD file to validate the XML
        """
        if not xml.endswith(".xml") or not os.path.exists(xml):
            raise Exception("Invalid XML File: %s"
                % os.path.realpath(xml))

        if not xsd.endswith(".xsd") or not os.path.exists(xsd):
            raise Exception("Invalid XSD File: %s"
                % os.path.realpath(xsd))

        name = xml.split(os.path.sep)[-1][:-4]
        if name in self.xmls.keys():
            raise Exception("Duplicate XML File: %s"
                % os.path.realpath(xml))

        xmlObject = Objectify(xml, xsd)
        self.xmls[name.lower()] = xmlObject

    def getConfiguration(self, name):
        """
        Retrieve a configuration object based on its name
        @param name: Name of configuration file with the .xml (exp.xml = exp)
        @raise InvalidConfiguration: Configuration instance not found
        @return: Configuration instance
        """
        name = name.lower()
        if name not in self.xmls.keys():
            raise Exception("Cannot find configuration: %s, %s" % (name, os.getcwd()))
        return self.xmls[name]

    def configurationExists(self, name):
        """
        Finds if a given configuration has been loaded
        @param name: Name of configuration file with the .xml (exp.xml = exp)
        @return: True if the configuration exists, else false
        """
        return name.lower() in self.xmls.keys()

    def configurationNames(self):
        """
        Return a list of configuration names that have been loaded
        @return: List of configuration names
        """
        return self.xmls.keys()

    def revalidateXMLs(self):
        """ Re-validate all the XMLs against their related XSD """
        for xml in self.xmls.values():
            xml.revalidate()
