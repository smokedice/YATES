from ExecutionOrganiser import ExecutionOrganiser
from ArgumentParser import ArgumentParser
from Utils.Envcat import envcatRequest
import sys, time, traceback, urllib2

VERSION = '0.01'
class CMDLine(ExecutionOrganiser):
    def __init__(self):
        ExecutionOrganiser.__init__(self, VERSION)
        self.argumentParser = ArgumentParser()
        if self.argumentParser.monitor: return
        if not self.argumentParser.parseArgs():
            sys.exit(0)

    def go(self):
        try:
            if self.argumentParser.monitor:
                self.__monitor()
            else:
                ExecutionOrganiser._go(self)
                self.__runTests()
        except: print traceback.format_exc()
        self._shutdown()

    def __runTests(self):
        """ Process tests and then shutdown """
        try:
            self.logger.info('Executing..')
            while not self._process(): time.sleep(1)
            self.logger.info('Closing..')

            for test in self.testDistributor.getNonFinishedTests():
                self.resultWorker.report(test, [], None)
        except Exception, e:
            print '>>', traceback.format_exc()
            self.logger.warn(traceback.format_exc())
        finally: self._shutdown()

    def __monitor(self):
        """ Monitor peers on the network """
        print ' >>. gathering peers .<<'
        time.sleep(4)
        peers = []

        for heartBeat in self.udpServer.getHeartBeats(10000000000000):
            try:
                config = {}
                ip, mac, randomBits = heartBeat
                response = urllib2.urlopen('http://%s:5005/config' % ip)

                for line in response.read().splitlines():
                    name, value = line.split('=', 1)
                    config[name] = value   

                try: 
                    response = urllib2.urlopen('http://%s:5005/locked' % ip)
                    config['locked'] = 'True, user %s' % response.read().strip()
                except urllib2.URLError:
                    config['locked'] = 'False'

                envServer = config['envserver']
                envServerPort = config['envserverport']
                if self.envServerPort.isdigit():
                    self.envServerPort = int(self.envServerPort)
                config['capabilities'] = envcatRequest(
                    envServer, envServerPort, 'capabilities')

                peers.append([ip, mac, config])
            except urllib2.URLError: pass

        for peer in sorted(peers, key = lambda v: v[1]):
            ip, mac, config = peer
            print 'IP: %s, MAC: %s' %(ip, mac)
            print '\n'.join([ '  %s=%s' %(n,v) for n,v in config.items() ]), '\n'

if __name__ == "__main__":
    CMDLine().go()
