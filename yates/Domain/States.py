class PeerState(object):
    VALUES = {
        'DEAD'          : {'index' :-40 , 'description' :
            'Peer has been declared as being dead and cannot be revived' },
        'CANNOT_REVIVE' : {'index' :-35 , 'description' :
            'Reboot Helper failed to revive the peer' },
        'UNRESPONSIVE'  : {'index' :-20 , 'description' :
            'Peer became unresponsive' },
        'CANNOT_REBOOT' : {'index' :-15 , 'description' :
            'Peer cannot be rebooted' },
        'REBOOTING'     : {'index' :-10 , 'description' :
            'Peer is rebooting' },
        'PENDING'       : {'index' : 0  , 'description' :
            'Peer has connected and is waiting for the code to test' },
        'SYNC_CODE'     : {'index' : 5  , 'description' :
            'TAS is syncing the test code to the peer' },
        'SYNC_LOGS'     : {'index' : 6  , 'description' :
            'TAS is syncing the logs from the peer' },
        'RECOVER_LOGS'  : {'index' : 7  ,  'description' :
            'Recovering the logs from the peer after crash' },
        'LOCKED'        : {'index' : 8  ,  'description' :
            'Peer is being used by another client' },
        'REMOVED'       : {'index' : 10 , 'description' :
            'Peer has been removed and will not be used' },
        'ACTIVE'        : {'index' : 20 , 'description' :
            'Peer has all the code required and is waiting to be used' },
        'TESTING'       : {'index' : 30 , 'description' :
            'Peer is currently testing' },
    }

    def __init__(self, name):
        if isinstance(name, PeerState):
            name = name.getName()
        elif not isinstance(name, str):
            raise LookupError('Expecting string object: %s' % type(name))
        elif name.upper() not in PeerState.VALUES.keys():
            raise LookupError('cannot find value: %s' % name)

        value = PeerState.VALUES[name.upper()]
        self.index = value['index']
        self.name = name

    def getIndex(self): return self.index
    def getBaseType(self): return self.baseType
    def clone(self): return PeerState(self.name)
    def getName(self): return self.name

    def __eq__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            return other == self.getName()
        if not isinstance(other, PeerState): return False
        return other.getIndex() == self.getIndex()

    def __str__(self):
        return self.getName()

    def __cmp__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            other = PeerState(str(other))
        elif not isinstance(other, PeerState):
            raise Exception("Cannot compare type %s with type TestState"
                % other.__class__.__name__)

        if self.getIndex() < other.getIndex(): return -1
        if self.getIndex() > other.getIndex(): return 1
        return 0

    @staticmethod
    def DEAD():
        return PeerState('DEAD')

    @staticmethod
    def CANNOT_REVIVE():
        return PeerState('CANNOT_REVIVE')

    @staticmethod
    def UNRESPONSIVE():
        return PeerState('UNRESPONSIVE')

    @staticmethod
    def CANNOT_REBOOT():
        return PeerState('CANNOT_REBOOT')

    @staticmethod
    def REBOOTING():
        return PeerState('REBOOTING')

    @staticmethod
    def PENDING():
        return PeerState('PENDING')

    @staticmethod
    def SYNC_CODE():
        return PeerState('SYNC_CODE')

    @staticmethod
    def SYNC_LOGS():
        return PeerState('SYNC_LOGS')

    @staticmethod
    def RECOVER_LOGS():
        return PeerState('RECOVER_LOGS')

    @staticmethod
    def ACTIVE():
        return PeerState('ACTIVE')

    @staticmethod
    def REMOVED():
        return PeerState('REMOVED')

    @staticmethod
    def TESTING():
        return PeerState('TESTING')

    @staticmethod
    def LOCKED():
        return PeerState('LOCKED')

class TestState(object):
    VALUES = {
        'CHANNELSCAN_FAILED' : {'sequenceId':-200, 'baseType' : 'ERROR',
            'description' : 'Channel scanning failed to complete' },

        'NO_SERVICE_LIST' : {'sequenceId' : -190, 'baseType' : 'ERROR',
            'description' : 'Channel scanning completed successfully, but no services populated in the service list' },
    
        'ERROR_TIME_SOURCE' : {'sequenceId' : -180, 'baseType' : 'ERROR',
            'description' : 'SR timesource not set correctly after channel scanning has completed successfully' },

        'DEADBOX'          : {'sequenceId' :-170 , 'baseType' : 'ERROR',
            'description' : 'Box crashed while testing, but didn\'t recover' },

        'CRASH'            : {'sequenceId' :-130 , 'baseType' : 'ERROR',
            'description' : 'Box crashed while testing, then recovered' },

        'DBUS_ERROR'       : {'sequenceId' :-126 , 'baseType' : 'ERROR',
            'description' : 'DBUS exception occurred' },

        'DBUS_NO_REPLY_ERROR' : {'sequenceId' :-122 , 'baseType' : 'ERROR',
            'description' : 'DBUS No Reply exception occurred' },

        'NO_XML'           : {'sequenceId' :-120 , 'baseType' : 'ERROR',
            'description' : 'No XML provided by the executor' },

        'INVALID_XML'      : {'sequenceId' :-110 , 'baseType' : 'ERROR',
            'description' : 'Returned XML from the test is invalid' },

        'ERROR'            : {'sequenceId' :-100 , 'baseType' : 'ERROR',
            'description' : 'Test error (something went wrong)' },

        'FAILURE'          : {'sequenceId' :-90  , 'baseType' : 'FAILURE',
            'description' : 'Test failed' },

        'SKIP'             : {'sequenceId' :-80  , 'baseType' : 'N/A',
            'description' : 'Test was skipped (due to the test case)' },

        'TIMEOUT'          : {'sequenceId' :-70  , 'baseType' : 'ERROR',
            'description' : 'Test timeout occurred' },

        'ENV_SERVER'       : {'sequenceId' :-60  , 'baseType' : 'ERROR',
            'description' : 'Environment Server failed' },

        'MODULE_INST'      : {'sequenceId' :-50  , 'baseType' : 'ERROR',
            'description' : 'Error occurred within module setup' },

        'MODULE_TEARDOWN'  : {'sequenceId' :-40  , 'baseType' : 'ERROR',
            'description' : 'Error occurred within module tear down' },

        'CLASS_SETUP'      : {'sequenceId' :-30  , 'baseType' : 'ERROR',
            'description' : 'Error occurred within the class setup' },

        'CLASS_TEARDOWN'   : {'sequenceId' :-20  , 'baseType' : 'ERROR',
            'description' : 'Error occurred within the class tear down' },

        'INSUFFICIENT_ENV' : {'sequenceId' :-10  , 'baseType' : 'N/A',
            'description' : 'The environment didn\'t include enough resources' },

        'NORESLT'          : {'sequenceId' :0    , 'baseType' : 'N/A',
            'description' : 'Test hasn\'t received a result' },

        'MANUAL'           : {'sequenceId' :10   , 'baseType' : 'N/A',
            'description' : 'Test was ignored as it is a manual test' },

        'PASS'             : {'sequenceId' :20   , 'baseType' : 'PASS',
            'description' : 'Test completed successfully' },
    }

    def __init__(self, name):
        if isinstance(name, TestState):
            name = name.getName()
        elif not isinstance(name, str):
            raise LookupError('Expecting string object')
        elif name not in TestState.VALUES.keys():
            raise LookupError('cannot find value: %s' % name)

        value = TestState.VALUES[name]
        self.index = value['sequenceId']
        self.baseType = value['baseType']
        self.name = name

    def getIndex(self): return self.index
    def getBaseType(self): return self.baseType
    def getName(self): return self.name
    def clone(self): return TestStates(self.name)

    def __eq__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            return other == self.getName()
        if not isinstance(other, TestState): return False
        return other.getIndex() == self.getIndex()

    def __str__(self):
        return self.getName()

    def __cmp__(self, other):
        if isinstance(other, str) or isinstance(other, unicode):
            other = TestState(str(other))
        elif not isinstance(other, TestState):
            raise Exception("Cannot compare type %s with type TestState"
                % other.__class__.__name__)

        if self.getIndex() < other.getIndex(): return -1
        if self.getIndex() > other.getIndex(): return 1
        return 0

    @staticmethod
    def CHANNELSCAN_FAILED(): return TestState('CHANNELSCAN_FAILED')

    @staticmethod
    def NO_SERVICE_LIST(): return TestState('NO_SERVICE_LIST')

    @staticmethod
    def ERROR_TIMESOURCE(): return TestState('ERROR_TIME_SOURCE')
 
    @staticmethod
    def DEADBOX(): return TestState('DEADBOX')

    @staticmethod
    def CRASH(): return TestState('CRASH')

    @staticmethod
    def DBUS_ERROR(): return TestState('DBUS_ERROR')

    @staticmethod
    def DBUS_NO_REPLY_ERROR(): return TestState('DBUS_NO_REPLY_ERROR')

    @staticmethod
    def NO_XML(): return TestState('NO_XML')

    @staticmethod
    def INVALID_XML(): return TestState('INVALID_XML')

    @staticmethod
    def ERROR(): return TestState('ERROR')

    @staticmethod
    def FAILURE(): return TestState('FAILURE')

    @staticmethod
    def SKIP(): return TestState('SKIP')

    @staticmethod
    def TIMEOUT(): return TestState('TIMEOUT')

    @staticmethod
    def ENV_SERVER(): return TestState('ENV_SERVER')

    @staticmethod
    def MODULE_INST(): return TestState('MODULE_INST')

    @staticmethod
    def MODULE_TEARDOWN(): return TestState('MODULE_TEARDOWN')

    @staticmethod
    def CLASS_SETUP(): return TestState('CLASS_SETUP')

    @staticmethod
    def CLASS_TEARDOWN(): return TestState('CLASS_TEARDOWN')

    @staticmethod
    def NORESLT(): return TestState('NORESLT')

    @staticmethod
    def PASS(): return TestState('PASS')

    @staticmethod
    def INSUFFICIENT_ENV(): return TestState('INSUFFICIENT_ENV')
