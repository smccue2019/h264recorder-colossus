#!/usr/bin/env python

import socket
import time

UDP_IP="198.17.154.189"
UDP_PORT=10520
msg = "VID 1"

while 1:
    vidstat_send = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    vidstat_send.sendto(msg, (UDP_IP, UDP_PORT) )
    time.sleep( 3.0 )

