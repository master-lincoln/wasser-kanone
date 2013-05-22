#!/usr/bin/env python

import cv
import array
import socket
import sys
import time
import math
from ola.ClientWrapper import ClientWrapper


class Target:

    # for testing
    pump = False
    dmx = True

    server_address = ('192.168.0.99', 10000)

    width, height = 640, 480
    #width, height = 1280, 720
    skipPictures = 10

    center = (41 << 8, 38 << 8)
    topRight = (31, 48)
    bottomLeft = (53, 18)
    dmxCoordinate = center
    lastPosition = center

    def __init__(self):
        # self.capture = cv.CaptureFromCAM(1)
        self.capture = cv.CreateCameraCapture(1)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)
        cv.NamedWindow("Target", 1)
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        print >>sys.stderr, 'connecting to %s port %s' % self.server_address
        self.sock.connect(self.server_address)

        self.startTime = time.clock()

    def sendFire(self):
        elapsed = (time.clock() - self.startTime)
        #print "elapsed: %fs" % elapsed
        if (elapsed > 1):
            self.startTime = time.clock()
            try:
                # Send data
                print 'sending fire command'
                self.sock.sendall('f')

            except Exception, e:
                print>>sys.stderr, "Error:", e

    def _DmxSent(self, state):
        self.wrapper.Stop()

    def restrict(self, val, minval, maxval):
        if val < minval: return minval
        if val > maxval: return maxval
        return val

    def moveDmxTo(self, position, lamp):
        #position = (self.restrict(position[0], 0, 255), self.restrict(position[1], 0, 255))
        data = array.array('B')
        pan = self.restrict(position[0] >> 8, 0, 255)
        panFine = self.restrict(0xFF & position[0], 0, 255)
        tilt = self.restrict(position[1] >> 8, 0, 255)
        tiltFine = self.restrict(0xFF & position[1], 0, 255)
        dimmer = (9 if lamp else 0)

        difference = max(math.fabs(position[0] - self.lastPosition[0]), math.fabs(position[1] - self.lastPosition[1]))
        print difference

        if (difference > 50):

            #print "pan: ", pan, " panFine: ", panFine, " tilt: ", tilt, " tiltFine: ", tiltFine

            data.append(pan)        #pan
            data.append(panFine)    #panFine
            data.append(tilt)       #tilt
            data.append(tiltFine)   #tiltfine
            data.append(8)        #vectorSpeed
            data.append(dimmer)        #dimmer
            data.append(255)        #red
            data.append(32)        #green
            data.append(0)         #blue
            data.append(0)          #colorMacros
            data.append(0)          #vectorSpeedColor
            data.append(0)          #moveMentMacros
            data.append(0)
            data.append(0)
            data.append(0)
            data.append(0)

            self.client.SendDmx(1, data, self._DmxSent)
            self.wrapper.Run()

            self.lastPosition = position

    def run(self):
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()
        i = 0
        while True:
            if (i > self.skipPictures):
                i = 0

                img = cv.QueryFrame(self.capture)

                #blur the source image to reduce color noise
                cv.Smooth(img, img, cv.CV_BLUR, 3)

                #convert the image to hsv(Hue, Saturation, Value) so its
                #easier to determine the color to track(hue)
                hsv_img = cv.CreateImage(cv.GetSize(img), 8, 3)
                cv.CvtColor(img, hsv_img, cv.CV_BGR2HSV)

                #limit all pixels that don't match our criteria, in this case we are
                #looking for purple but if you want you can adjust the first value in
                #both turples which is the hue range(120,140).  OpenCV uses 0-180 as
                #a hue range for the HSV color model
                # Orange  0-22
                # Yellow 22- 38
                # Green 38-75
                # Blue 75-130
                # Violet 130-160
                # Red 160-179
                thresholded_img = cv.CreateImage(cv.GetSize(hsv_img), 8, 1)
                cv.InRangeS(hsv_img, (160, 80, 80), (179, 255, 255), thresholded_img)

                #determine the objects moments and check that the area is large
                #enough to be our object
                mat = cv.GetMat(thresholded_img)
                moments = cv.Moments(mat, 0)
                area = cv.GetCentralMoment(moments, 0, 0)

                #there can be noise in the video so ignore objects with small areas
                if(area > 500000):
                    #determine the x and y coordinates of the center of the object
                    #we are tracking by dividing the 1, 0 and 0, 1 moments by the area
                    x = cv.GetSpatialMoment(moments, 1, 0)/area
                    y = cv.GetSpatialMoment(moments, 0, 1)/area

                    #print 'x: ' + str(x) + ' y: ' + str(y) + ' area: ' + str(area)

                    xRange = (self.bottomLeft[0] << 8) - (self.topRight[0] << 8)
                    yRange = (self.topRight[1] << 8) - (self.bottomLeft[1] << 8)
                    #print "xRange: ", xRange, " yRange: ", yRange
                    self.dmxCoordinate = (int((self.bottomLeft[0] << 8) - (x / self.width) * xRange), int((self.topRight[1] << 8) - (y / self.height) * yRange))

                    if self.dmx:
                        self.moveDmxTo(self.dmxCoordinate, True)
                    if self.pump:
                        self.sendFire()

                    #create an overlay to mark the center of the tracked object
                    overlay = cv.CreateImage(cv.GetSize(img), 8, 3)

                    cv.Circle(overlay, (int(x), int(y)), 2, (255, 255, 255), 20)
                    cv.Add(img, overlay, img)
                    #add the thresholded image back to the img so we can see what was
                    #left after it was applied
                    cv.Merge(thresholded_img, None, None, None, img)
                else:
                    self.moveDmxTo(self.dmxCoordinate, False)

                #display the image
                cv.ShowImage("Target", img)

                del(img)
                del(hsv_img)
                del(thresholded_img)

                if cv.WaitKey(150) == 27:
                    del self.capture
                    # close socket connection
                    print >>sys.stderr, 'closing socket'
                    sock.close()

                    break

            else:
                i = i + 1

if __name__ == "__main__":
    t = Target()
    t.run()
