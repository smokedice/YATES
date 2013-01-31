#!/bin/bash -x
python -c "
import socket, time, uuid, os, traceback
while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        msg = '%s:%s' %(hex(uuid.getnode())[2:-1].zfill(12), str(os.urandom(10)).encode('hex'))
        while time.sleep(2) == None: sock.sendto(msg, ('224.6.6.6', 8005))
    except Exception:
        f = open('/tmp/udp.log', 'w')
        f.write(\"%s\n%s\" %(datetime.datetime.now(), traceback.format_exc()))
        f.write(\"\n\n\")
        f.close()
    time.sleep(5)
" &

python -m SimpleHTTPServer 5005 >http.log 2>&1 &
