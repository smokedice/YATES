from multiprocessing import Process
import yates.Utils.envclient

UNSPECIFIED = yates.Utils.envclient.UNSPECIFIED


def capabilities(host, port):
    """ Retrieve the envservers capabilities """
    client = yates.Utils.envclient.Client(host, port)
    return client.status.capabilities()


def latest_id(host, port):
    """ Retrieve the latest log ID on the envserver """
    client = yates.Utils.envclient.Client(host, port)
    return client.status.latest_id()


def stop_all(host, port):
    """ Stop all services on the envserver """
    client = yates.Utils.envclient.Client(host, port)
    return _create_process(client.status.stopall)


def store_log(host, port, file_loc, since=UNSPECIFIED):
    """ Store the envserver log to a given file """
    def _store_log(host, port, file_loc, since):
        client = yates.Utils.envclient.Client(host, port)
        with open(file_loc, 'w') as f:
            lines = client.status.get_logs(since)
            f.write('\n'.join([
                ' '.join(str(i) for i in x[1:])
                for x in lines
            ]))

    return _create_process(_store_log, host, port,
                           file_loc, since)


def _create_process(target, *args):
    """ create process for background processing """
    name = target.__name__
    process = Process(
        name='envcat-%s' % name,
        target=target, args=args)
    process.start()
    return process
