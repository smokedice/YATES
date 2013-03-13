from yates.Utils.Logging import LogManager

from StringIO import StringIO
from traceback import format_exc
from types import StringTypes
from minixsv import pyxsval
from sys import stdout
import hashlib
import os

from gnosis.xml.objectify._objectify import make_instance, tagname, attributes, \
    content


class Objectify(object):
    """
    The objectify class allows the application
    to setup and use Objectify by using the
    constructor, then accessing Objectify
    by using the .instance attribute
    @param xml: XML file path
    @param xsd: XSD file path
    @raise InvalidConfigurationXML: Non existent XML/XSD. Invalid formatted files
    """

    KWARGS = {
        "xmlIfClass": pyxsval.XMLIF_ELEMENTTREE,
        "warningProc": pyxsval.PRINT_WARNINGS,
        "errorLimit": 200,
        "verbose": 0,
        "useCaching": 0,
        "processXInclude": 0
    }

    def __init__(self, xml, xsd):
        self.logger = LogManager().getLogger(self.__class__.__name__)

        self.cwd = os.path.abspath('.')
        self.xmlFile = os.path.abspath(xml)
        self.xsdFile = os.path.abspath(xsd)

        if not os.path.exists(self.xmlFile) or not os.path.exists(self.xsdFile):
            raise Exception("Given Files: %s - %s" % (self.xmlFile, self.xsdFile))

        successfulLoad, xmlHash, xsdHash = self.__loadFromCache(xml, xsd)

        if not successfulLoad:
            # Hashes are incorrect
            self.__loadAndValidate(xml, xsd, xmlHash, xsdHash)

    def __loadFromCache(self, xml, xsd):
        hashPath = self.__getXmlHashFile(xml)
        xmlHash = self.__hashFile(xml)
        xsdHash = self.__hashFile(xsd)

        if not os.path.exists(hashPath):
            return (False, xmlHash, xsdHash)

        with open(hashPath, 'r') as hashFile:
            cachedXMLHash = hashFile.readline().strip()
            cachedXSDHash = hashFile.readline().strip()

        if cachedXMLHash != xmlHash or cachedXSDHash != xsdHash:
            return (False, xmlHash, xsdHash)

        self.configuration = make_instance(xml)
        return (True, xmlHash, xsdHash)

    def __hashFile(self, path):
        with open(path, 'rb') as xmlFile:
            shaHash = hashlib.sha1()

            while True:
                data = xmlFile.read(4096)
                if not data:
                    break
                shaHash.update(hashlib.sha1(data).hexdigest())

        return shaHash.hexdigest()

    def __loadAndValidate(self, xml, xsd, xmlHash, xsdHash):
        try:
            # Validate the config file
            pyxsval.parseAndValidate(
                inputFile=xml, xsdFile=xsd,
                **Objectify.KWARGS)
        except Exception:
            raise Exception(format_exc())

        #gnosis.xml.objectify._XO_node = Node.Node
        #gnosis.xml.objectify._XO_interface = Interface.Interface
        self.configuration = make_instance(xml)
        hashPath = self.__getXmlHashFile(xml)

        try:
            with open(hashPath, 'w') as hashFile:
                hashFile.write("%s\n%s" % (xmlHash, xsdHash))
                hashFile.close()
        except IOError, e:
            self.logger.error(e)

    def __getXmlHashFile(self, xmlPath):
        head, tail = os.path.split(xmlPath)
        hashFile = os.path.join(head, ".hash.%s" % tail)
        return hashFile

    def getConfiguration(self):
        """
        Get the configuration object
        @return: Objects representing the configuration
        """
        return self.configuration

    def getXMLFileLocation(self):
        """
        Return the path of the related XML file
        @return: Path of XML file
        """
        return self.xmlFile

    def getXSDFileLocation(self):
        """
        Return the path of the related XSD file
        @return: Path of XSD file
        """
        return self.xsdFile

    def revalidate(self):
        """ Re-validate the in memory object tree against the related XSD """
        xmlBuffer = self.__write_xml(self.configuration, StringIO())
        xml = xmlBuffer.getvalue()
        xmlBuffer.close()

        with open(self.xsdFile, 'r') as xsdBuffer:
            xsd = "".join(xsdBuffer.readlines())
        orgCwd = os.getcwd()

        try:
            # Validate the config file
            cwd = os.path.sep.join(self.xmlFile.split(os.path.sep)[:-1])
            os.chdir(cwd)

            pyxsval.parseAndValidateXmlInputString(
                inputText=xml, xsdText=xsd,
                validateSchema=1,
                **Objectify.KWARGS)
        except Exception:
            self.logger.error("Error occurred within %s" % cwd)
            raise Exception(format_exc())
        finally:
            os.chdir(orgCwd)

    def __write_xml(self, o, out=stdout):
        """ Serialize an _XO_ object back into XML """
        out.write("<%s" % tagname(o))
        for attr in attributes(o):
            out.write(' %s="%s"' % attr)
        out.write('>')

        for node in content(o):
            if type(node) in StringTypes:
                out.write(node)
            else:
                self.__write_xml(node, out=out)
        out.write("</%s>" % tagname(o))
        return out
