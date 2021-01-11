#!/usr/bin/env python

import sys,socket
#from PyQt4.QtCore import 
#from PyQt4.QtGui import *
from PyQt4 import QtNetwork

# Simple sender of video recorder status

class UDP_sendStatus(QObject):

        def __init__(self, send_port, targetIP, parent=None):
            super(UDP_sendStatus, self).__init__(parent)

            self.sendPort = num(send_port)
            self.target_IP = QtNetwork.QHostAddress(targetIP)

            try:
                self.ss = QtNetwork.QUdpSocket(self)
            except:
                print "Trouble opening UDP on socket %d" % (self.sendPort)

        def sendStatus(self, status):
            msg = "VID %d" % (status)
            self.ss.writeDatagram(msg, self.target_IP, self.sendPort)

	def num (s):
		try:
			return int(s)
		except ValueError as e:
			return float(s)
