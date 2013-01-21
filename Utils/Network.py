from uuid import getnode as getMacAddress
import fcntl, os, socket, struct, subprocess
import time, tempfile

__MAC_ADDRESS = hex(getMacAddress())[2:-1]

def getIPAddressByInterface(ifname = "eth0"):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915, # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def hostIsAlive(ip, attempts = 5):
    for _ in range(attempts):
        if not os.system("ping -c 2 %s" % ip):
            return True
    return False

def getMacAddress():
    return __MAC_ADDRESS

def syncGetHTTPFile(location, destination, uncompress = False):
    """
    Retrieve a file without blocking
    @param location: HTTP location of the file
    @param destination: Directory destination of the file
    @param uncompress: If true, uncompress the file into the destination
    """
    assert os.path.isdir(destination), destination
    fileName = location.split('/')[-1]
    tmpDir = os.environ['TAS_TMP']

    fHandle, tmpFileName = tempfile.mkstemp('', fileName, tmpDir)
    os.close(fHandle)

    ucCmd = ' && tar -xmzf %s -C %s ' % (tmpFileName, destination) \
        if uncompress else ' && mv %s %s/%s' %(tmpFileName, destination, fileName)
    return subprocess.Popen('wget %s -q -O %s%s' %(location, tmpFileName, ucCmd),
        shell = True)
