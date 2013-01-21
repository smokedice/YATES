from Utils.Configuration import ConfigurationManager
from Domain.States import PeerState
from multiprocessing import Process, Queue
import re, os, mmap

class ReactionDefiner(Process):
    """ Find a reaction to match the provided content """

    def __init__(self, fileLocs, test):
        self.fileLocs = fileLocs
        self.test = test
        self.queue = Queue()
        self.config = ConfigurationManager().getConfiguration('reactions').configuration
 
        Process.__init__(self, target = self.__defineResult, name = "ReactionDefiner")
        self.start()

    def __defineResult(self):
        """ Match a reaction to the provided content """
        contents = self.createFileMaps(self.fileLocs)
        reactions = getattr(self.config, 'reaction', [])
        reactions = reactions if isinstance(reactions, list) else [reactions]

        try: self.__findReaction(contents, reactions) 
        finally: self.closeFileMaps(contents)

    def __findReaction(self, contents, reactions):     
        """ Match a reaction to a set of content """
        for reaction in reactions:
            if reaction.related not in contents.keys():
                continue

            fileHandler, fileMap = contents[reaction.related]
            if not re.search(reaction.pattern.PCDATA, fileMap):
                continue

            peerState = PeerState(str(reaction.effect.peerstate.PCDATA)) \
                if hasattr(reaction.effect, 'peerstate') else None
            gracePeriod = int(reaction.effect.graceperiod.PCDATA) \
                if hasattr(reaction.effect, 'graceperiod') else 0
            return self.queue.put((peerState, gracePeriod))
            
        return self.queue.put((None, 0))

    def createFileMaps(self, fileLocs):
        contents = {}
        contents['teststate'] = (None, self.test.state.name)

        for fileLoc in self.fileLocs:
            fullName = fileLoc.split(os.path.sep)[-1]
            name = fullName.split('.')[0].lower()
            fileHandler = open(fileLoc, 'r')
            fileSize = os.path.getsize(fileLoc)
            if fileSize == 0: continue
            fileMap = mmap.mmap(fileHandler.fileno(), fileSize, access=mmap.ACCESS_READ)
            contents[name] = (fileHandler, fileMap)
        return contents

    def closeFileMaps(self, contents):
        for content in contents:
            if not isinstance(content, mmap.mmap):
                continue
            fileHandler, fileMap = content
            fileMap.close()
            fileHandler.close()

    def getResult(self):
        """ Retrieve the peer state and grace period """
        if self.is_alive():
            raise Exception('Result is being processed')

        result = self.queue.get()
        self.queue.close()
        return result
