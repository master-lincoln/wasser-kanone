#!/usr/bin/env python

import socket
import sys
import time
import RPi.GPIO as GPIO

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('192.168.0.99', 10000)
print >>sys.stderr, 'starting up on %s port %s' % server_address
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

try:
    # to use Raspberry Pi board pin numbers
    GPIO.setmode(GPIO.BCM)

    # set up the GPIO channels - one input and one output
    GPIO.setup(11, GPIO.OUT)
finally:
    print >>sys.stderr, 'GPIO set'


def fire():
    # output to pin 1
    print "HIGH"
    GPIO.output(11, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(11, GPIO.LOW)
    print "LOW"

options = {'f': fire}

while True:
        # Wait for a connection
        print >>sys.stderr, 'waiting for a connection'
        connection, client_address = sock.accept()

        try:
            print >>sys.stderr, 'connection from', client_address

            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(16)
               
                if data:
                    print >>sys.stderr, 'received "%s"' % data
                    print >>sys.stderr, 'FIRE'
                    #options[data]()
                    fire()
                else:
                    print >>sys.stderr, 'no more data from', client_address
                    break
                
        finally:
            # Clean up the connection
            connection.close()