import logging

class LogManager(object):
    FILENAME = 'application.log'

    def __init__(self):
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s - %(name)s: %(message)s')
        self.getLogger('peewee.logger').setLevel(logging.CRITICAL)

    def getLogger(self, name):
        """
        Get a logger with a certain name
        @param name: Name of logger to retrieve
        """
        return logging.getLogger(name)
