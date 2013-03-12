#!/usr/bin/env python2.7
import argparse
import inspect
import json
import os
import pprint
import sys
import urllib
import urllib2
import urlparse

DEFAULT_ENVSERVER = os.environ.get("ENVSERVER", "localhost")
DEFAULT_PORT = int(os.environ.get("ENVSERVER_PORT", "9595"))

UNSPECIFIED = object()


class CallFailed(Exception):

    def format_message(self):
        return "\x1b[1mERROR: \x1b[1;31m%s\x1b[0m" % self.message


class _Client(object):

    URL_PREFIX = None

    def __init__(self, server, port):
        self.url_base = "http://%s:%s%s/" % (server, port, self.URL_PREFIX)

    def _filter_data(self, data):
        return dict((k, v) for k, v in data.iteritems() if v is not UNSPECIFIED)

    def _POST(self, url, data=None, data_key="data"):
        query = ""
        if data is not None:
            query = urllib.urlencode(self._filter_data(data))

        full_url = urlparse.urljoin(self.url_base, url)
        request = urllib2.Request(full_url, query)

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            json_msg = json.loads('\n'.join(e.readlines()))
            if 'traceback' in json_msg.keys():
                print json_msg['traceback']
            raise CallFailed(json_msg['message'])

        payload = json.load(response)
        data = payload[data_key]
        return "\x1b[32mCall succeeded\x1b[0m" if data is None else data


class keystoreClient(_Client):
    
    """A simple key=value pair store"""
    
    URL_PREFIX = "/keystore"
    NAME = "keystore"

    def count(self, ):
        """Return the number of items in the keystore
        """
        return self._POST("count", {}, "data")

    def set_key(self, key, value):
        """Set <key> to be <value>
        """
        return self._POST("set_key", {"value": value, "key": key}, "data")

    def view_keys(self, ):
        """Return a list of all keys currently stored
        """
        return self._POST("view_keys", {}, "keys")

    def remove_key(self, key):
        """
        """
        return self._POST("remove_key", {"key": key}, "data")

    def get_key(self, key):
        """Return the value that has been stored for <key>
        """
        return self._POST("get_key", {"key": key}, "value")


class statusClient(_Client):
    
    """Query and manage the envserver status"""
    
    URL_PREFIX = "/status"
    NAME = "status"

    def status(self, ):
        
        return self._POST("status", {}, "data")

    def stopall(self, ):
        """ Stop all services 
        """
        return self._POST("stopall", {}, "data")

    def capabilities(self, ):
        """ Capabilities of all modules 
        """
        return self._POST("capabilities", {}, "capabilities")

    def latest_id(self, ):
        """ Get the latest ID within the logs 
        """
        return self._POST("latest_id", {}, "data")

    def clear_logs(self, ):
        """ Remove all logs from envserver 
        """
        return self._POST("clear_logs", {}, "data")

    def shutdown(self, ):
        """Shut down the server, after calling this, the server should not be running
        """
        return self._POST("shutdown", {}, "data")

    def get_logs(self, since=UNSPECIFIED, limit=UNSPECIFIED):
        """Return a list of system event log items, ordered by the date they occurred.
    Only logs items with an ID greater than <since> are returned.
    No more than <limit> items are returned.
    
        """
        return self._POST("get_logs", {"since": since, "limit": limit}, "data")


class ipstreamClient(_Client):
    
    URL_PREFIX = "/ipstream"
    NAME = "ipstream"

    def play(self, requests):
        """
        """
        return self._POST("play", {"requests": requests}, "playback")

    def stop(self, group, port):
        """
        """
        return self._POST("stop", {"group": group, "port": port}, "data")

    def stopall(self, ):
        
        return self._POST("stopall", {}, "data")

    def conflicts(self, ):
        
        return self._POST("conflicts", {}, "data")

    def availablegroups(self, ):
        
        return self._POST("availablegroups", {}, "groups")

    def listen(self, ):
        
        return self._POST("listen", {}, "data")


class modulatorsClient(_Client):
    
    URL_PREFIX = "/modulators"
    NAME = "modulators"

    def status(self, ):
        
        return self._POST("status", {}, "status")

    def play(self, request):
        """
        """
        return self._POST("play", {"request": request}, "data")

    def stop(self, ):
        
        return self._POST("stop", {}, "data")

    def streaminfo(self, name):
        """
        """
        return self._POST("streaminfo", {"name": name}, "streaminfo")

    def capabilities(self, ):
        
        return self._POST("capabilities", {}, "capabilities")

    def modconfig(self, ):
        
        return self._POST("modconfig", {}, "modconfig")

    def uploadconfig(self, config_file, file_name):
        """
        """
        with open(os.path.abspath(config_file), 'r') as f:
            config_file = '\n'.join(f.readlines())
        
        return self._POST("uploadconfig", {"file_name": file_name, "config_file": config_file}, "status")

    def usedcapabilities(self, ):
        
        return self._POST("usedcapabilities", {}, "capabilities")

    def active(self, ):
        
        return self._POST("active", {}, "active")


class hubClient(_Client):
    
    URL_PREFIX = "/hub"
    NAME = "hub"

    def push(self, server_id):
        """Start envserver on the server with ID = <server_id>.
        """
        return self._POST("push", {"server_id": server_id}, "data")

    def remove(self, server_id):
        """Delete the server record with ID = <server_id>
        """
        return self._POST("remove", {"server_id": server_id}, "data")


class Client(object):

    def __init__(self, server=DEFAULT_ENVSERVER, port=DEFAULT_PORT):
        self._server = server
        self._port = port

    @property
    def keystore(self):
        return keystoreClient(self._server, self._port)

    @property
    def status(self):
        return statusClient(self._server, self._port)

    @property
    def ipstream(self):
        return ipstreamClient(self._server, self._port)

    @property
    def modulators(self):
        return modulatorsClient(self._server, self._port)

    @property
    def hub(self):
        return hubClient(self._server, self._port)

    
def main():
    parser = argparse.ArgumentParser(
        usage= '%(prog)s module command [arguments]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Connect to an envserver and run commands remotely")
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-s", "--server", default=DEFAULT_ENVSERVER)
    module_subparsers = parser.add_subparsers(title="Modules", metavar="")

    for mod in [keystoreClient, statusClient, ipstreamClient, modulatorsClient, hubClient, ]:
        mod_parser =  module_subparsers.add_parser(mod.NAME, help="", description=mod.__doc__)
        mod_parser.set_defaults(client=mod)
        cmd_subparsers = mod_parser.add_subparsers(
            help='command', title="Commands", metavar="<command>")

        for name, value in mod.__dict__.iteritems():
            if not callable(value) or name.startswith("_"):
                continue

            arg_spec = inspect.getargspec(value)
            arg_list = arg_spec.args[1:]
            if arg_spec.defaults:
                mandatory_args = arg_list[:-len(arg_spec.defaults)]
                optional_args = arg_list[-len(arg_spec.defaults):]
            else:
                mandatory_args = arg_list
                optional_args = []

            help_content = " ".join(["--%s=%s" % (a, a.upper()) for a in arg_list])
            method_parser = cmd_subparsers.add_parser(name, help=help_content, description=value.__doc__)
            method_parser.set_defaults(method_name=name, arg_list=arg_list)
            for arg in mandatory_args:
                method_parser.add_argument("--%s" % arg, required=True)
            for arg in optional_args:
                method_parser.add_argument("--%s" % arg, default=UNSPECIFIED)

    options = parser.parse_args(sys.argv[1:])
    args = {name: getattr(options, name) for name in options.arg_list}
    client = options.client(server=options.server, port=options.port)

    try:
        result = getattr(client, options.method_name)(**args)
        if isinstance(result, basestring):
            print result
        else:
            pprint.pprint()
    except Exception, e:
        if hasattr(e, "format_message"):
            return e.format_message()
        raise


if __name__ == "__main__":
    sys.exit(main())