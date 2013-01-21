from Utils.Logging import LogManager

import socket, traceback, os
from multiprocessing import Process

class EnvCat(Process):
    def __init__(self, host, port, dest, cmd):
        """ 
        Save the envlog to a given destination
        @param host: IP address where the env server exists
        @param port: Env server tcp port
        @param dest: Full path of where the env log should be written to
        """
        Process.__init__(self, name = 'EnvCatLog')

        path, filename = os.path.split(os.path.abspath(dest))
        if not os.path.exists(path):
            os.makedirs(path)

        self.dest = dest
        self.host = host
        self.port = port
        self.cmd = cmd
        self.start()

    def run(self):
        if self.host == '' or self.port == '':
            return

        with open(self.dest, 'w') as log:
            content = envcatRequest(self.host, self.port, self.cmd)
            log.write(content)

def envcatRequest(hostname, port, content):
    '''
    Method retreives data from the evserver
    @param hostname: IP address of the envserver
    @param port: port of the envserver
    @param content: the content keyword required to be retreived
    @return: the retrieved content, or empty string in case of error
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ret = ''

    if not hostname or not port:
        return ret

    try:
        s.settimeout(3)
        s.connect((hostname, port))
        s.settimeout(None)
        s.sendall(content)
        s.shutdown(socket.SHUT_WR)

        while 1:
            data = s.recv(1024)
            if data == "": break
            ret = data
        s.close()
    except:
        #If the exception will be raised duting the retrieval of the
        #data, we just put log message, and return empty string,
        #as failure in the retrieval may indicate, that the configuration
        #of the envserver exist, but the server is not running
        exc = traceback.format_exc().splitlines()
        LogManager().getLogger('EnvCat').warning(
            "Failed retrieve %s from server %s:%s: %s" % (content, hostname,
            port, exc[-1]))

    return ret
