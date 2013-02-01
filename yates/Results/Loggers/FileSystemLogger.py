from Utils.Configuration import ConfigurationManager
from gnosis.xml.objectify._objectify import _XO_

import os
import shutil
import tarfile
import traceback
from time import strftime

class FileSystemLogger(object):
    STANDARD_LOG_NAMES = ['stdout.txt', 'stderr.txt', 'dbus.txt', 'envlog.txt', 'xunit.xml']

    def __init__(self, config, loc, trmsLogger, discovery=None):
        self.contentLoc = loc
        self.clear = config.clear.PCDATA == 'true'
        self.archiveName = config.archive.name.PCDATA.encode('utf-8')
        self.archiveFormat = config.archive.format.PCDATA.encode('utf-8')
        self.archiveLocation = config.archive.location.PCDATA.encode('utf-8')
        self.inputsPath = os.path.join(self.contentLoc, 'inputs')
        self.trmsLogger = trmsLogger

        if self.clear and os.path.exists(self.contentLoc):
            shutil.rmtree(self.contentLoc)

        if not os.path.exists(self.contentLoc): os.makedirs(self.contentLoc)
        if not os.path.exists(self.inputsPath): os.makedirs(self.inputsPath)

        # Copy the source to the logged content
        if discovery==None:
            discovery = ConfigurationManager().getConfiguration('discovery').configuration

        for codeType in dir(discovery):
            xmlObj = getattr(discovery, codeType)
            if not isinstance(xmlObj, _XO_): continue
            testRoot = xmlObj.SourceLocation.testRoot.PCDATA
            testRoot = os.path.abspath(testRoot)
            if not os.path.exists(testRoot): continue
            shutil.copytree(testRoot, os.path.join(self.inputsPath, codeType))

            # Copy the master db, if it exists
            if hasattr(xmlObj, 'DatabaseReader') \
            and hasattr(xmlObj.DatabaseReader, 'location') \
            and xmlObj.DatabaseReader.enabled == 'true':
                shutil.copyfile(xmlObj.DatabaseReader.location.PCDATA,
                    os.path.join(self.contentLoc, '%s.master.sqlite3' % codeType))

    def logResult(self, test, files):
        testName = test.combineClassMethod()
        iterationID = test.uniqueId
        fileLocation = test.testFile

        if fileLocation.endswith('.py'):
            fileLocation = fileLocation[:-3]

        if fileLocation.startswith(os.path.sep):
            fileLocation = fileLocation[1:]

        resultLocation = os.path.join(self.contentLoc,
            'logs', fileLocation, testName, iterationID)
        customLogLocation = os.path.join(resultLocation, 'customLogs')
        self.__createFolderLocation(customLogLocation)
        standardLogFiles, customLogFiles = self.__splitFiles(files)

        # Copy logs to their correct location
        for logs, location in [(standardLogFiles, resultLocation), (customLogFiles, customLogLocation)]:
            for log in logs: shutil.copy(log, location)

    def logPeerState(self, peer, comment = None):
        """ Ignoring peer states """
        pass

    def __splitFiles(self, files):
        """
        Split the given files into two categories, standard and custom
        @param files: List of files to split
        @return: Tuple containing two lists (standard, custom)
        """
        standardLogs = []
        customLogs = []

        for lFile in files:
            fileName = lFile.split(os.path.sep)[-1]
            if fileName in FileSystemLogger.STANDARD_LOG_NAMES:
                standardLogs.append(lFile)
            else: customLogs.append(lFile)
        return standardLogs, customLogs

    def __logExists(self, name, logLoc):
        if not logLoc or not os.path.exists(logLoc):
            print ' **> FileSystemLogger: Log does not exist: %s,%s' % (name, logLoc)
            return False
        return True

    # TODO: this could be improved. Currently TAS will stop with an error
    # once a single test has finished. This could take a while.. Would be
    # better to cause a error at start up
    def __createFolderLocation(self, location):
        if os.path.exists(location): return

        try: os.makedirs(location)
        except Exception, e:
            raise Exception("Logger cannot create log folder")

    def __templateName(self, name):
        return name.replace("%d", strftime("%Y-%m-%dT%H:%M:%S"))

    def logIteration(self, iteration): pass

    def shutdown(self):
        """ Archive logged content """
        curDir = os.getcwd()
        os.chdir(self.contentLoc)

        try:
            archiveName = self.__templateName(self.archiveName.encode('utf-8'))
            archiveUniqueName, archiveFile = self.__getUniqueFileName(self.contentLoc,
                archiveName, self.archiveFormat)

            if not os.path.exists(self.contentLoc): os.makedirs(self.contentLoc)
            if not os.path.exists(self.archiveLocation): os.makedirs(self.archiveLocation)

            if self.archiveFormat == 'zip':
                shutil.make_archive(archiveUniqueName,
                    self.archiveFormat,
                    self.contentLoc)
            else:
                t = tarfile.open(archiveFile, 'w:gz')
                for item in os.listdir('.'): t.add(item)
                t.close()

            _, fileDestLocation = self.__getUniqueFileName(self.archiveLocation,
                archiveName, self.archiveFormat)
            shutil.copyfile(archiveFile, fileDestLocation)

            if self.trmsLogger:
                self.trmsLogger.resultsReady(archiveFile)
        finally:
            os.chdir(curDir)

    def __getUniqueFileName(self, location, name, extension):
        """ Find a unique file name for given location """
        index = None

        while True:
            indexID = ".v%s" % index if index else ""
            uniqueName = "%s%s" % (name, indexID)
            fileName = "%s.%s" % (uniqueName, extension)
            filePath = os.path.join(location, fileName)
            if not os.path.exists(filePath): break

            if index: index += 1;
            else: index = 1

        return uniqueName, filePath
