#!/usr/bin/env python

import cv
import array
import socket
import sys
import time
import math
from ola.ClientWrapper import ClientWrapper


class Target:

    gobos = {'circle': 0, 'pfeilkreis': 10, 'blasen': 18, 'tribal': 25, 'wirbel': 35, 'parkett': 45, 'dreiecke': 55, 'spirale': 60, 'punkte': 65, 'wald': 75}


    # for testing
    pump = True
    dmx = True

    server_address = ('192.168.0.99', 10000)

    #width, height = 640, 480
    width, height = 800, 600
    skipPictures = 1
    offset = 0
    area = 900000

    # limit all pixels that don't match our criteria
    # OpenCV uses 0-180 as a hue range for the HSV color model
    # Orange  0-22
    # Yellow 22- 38
    # Green 38-75
    # Blue 75-130
    # Violet 130-160
    # Red 160-179
    colorLower = [0, 20, 65]
    colorUpper = [18, 255, 119]

    center = (41 << 8, 21 << 8)
    topRight = (28, 33) #32
    bottomLeft = (53, 12)
    dmxCoordinate = center
    lastPosition = center

    gobo = gobos['blasen']

    def __init__(self):
        # self.capture = cv.CaptureFromCAM(1)
        self.capture = cv.CreateCameraCapture(1)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)
        cv.NamedWindow("Target", 1)

        # Trackbars for calibration
        # TODO set initial values from self.area, self.colorLower, self.colorUpper
        cv.CreateTrackbar("Area", "Target", 0, 20, self.setArea)
        cv.CreateTrackbar("MinColor", "Target", 0, 180, self.setMinCol)
        cv.CreateTrackbar("MaxColor", "Target", 0, 180, self.setMaxCol)
        cv.CreateTrackbar("MinVal", "Target", 0, 255, self.setMinVal)
        cv.CreateTrackbar("MaxVal", "Target", 0, 255, self.setMaxVal)
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        print >>sys.stderr, 'connecting to %s port %s' % self.server_address
        self.sock.connect(self.server_address)

        self.startTime = time.clock()

    def setArea(self, value):
        self.area = 100000 * value + 100000

    def setMinCol(self, value):
        self.colorLower[0] = value

    def setMaxCol(self, value):
        self.colorUpper[0] = value

    def setMinVal(self, value):
        self.colorLower[2] = value

    def setMaxVal(self, value):
        self.colorUpper[2] = value

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
        #print difference

        if (difference > 50):
            pass 

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
        data.append(self.gobo)          #gobo
        data.append(0)
        data.append(0)
        data.append(0)

        self.client.SendDmx(5, data, self._DmxSent)
        self.wrapper.Run()

        self.lastPosition = position

    def mouse_callback(self, event,x,y,flags,param):
        if event==cv.CV_EVENT_LBUTTONDBLCLK:
            print "click at (" +str(x)+", "+str(y)+")"
            self.getColor(x,y)
            #print x,y

    def getColor(self, x, y):
        print cv.Get2D(self.img, y, x)
        #print 'Hue: %d Saturation %d Value: %d' % hue, sat, val

    def run(self):
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()
        i = 0

        self.img = cv.QueryFrame(self.capture)
        frame_size = cv.GetSize(self.img)
        grey_image = cv.CreateImage(cv.GetSize(self.img), cv.IPL_DEPTH_8U, 1)
        moving_average = cv.CreateImage(cv.GetSize(self.img), cv.IPL_DEPTH_32F, 3)
        difference = None
        movement = []

        while True:
            if (++i > self.skipPictures): i = 0

            self.img = cv.QueryFrame(self.capture)

            cv.Flip(self.img, flipMode=-1)

            # Smooth to get rid of false positives
            cv.Smooth(self.img, self.img, cv.CV_GAUSSIAN, 3, 0)

            if not difference:
                # Initialize
                difference = cv.CloneImage(self.img)
                temp = cv.CloneImage(self.img)
                cv.ConvertScale(self.img, moving_average, 1.0, 0.0)
            else:
                cv.RunningAvg(self.img, moving_average, 0.020, None)

            # Convert the scale of the moving average.
            cv.ConvertScale(moving_average, temp, 1.0, 0.0)

            # Minus the current frame from the moving average.
            cv.AbsDiff(self.img, temp, difference)

            # Convert the image to grayscale.
            cv.CvtColor(difference, grey_image, cv.CV_RGB2GRAY)

            # Convert the image to black and white.
            cv.Threshold(grey_image, grey_image, 70, 255, cv.CV_THRESH_BINARY)

            # Dilate and erode to get object blobs
            cv.Dilate(grey_image, grey_image, None, 18)
            cv.Erode(grey_image, grey_image, None, 10)

            # Calculate movements
            storage = cv.CreateMemStorage(0)
            contour = cv.FindContours(grey_image, storage, cv.CV_RETR_CCOMP, cv.CV_CHAIN_APPROX_SIMPLE)
            points = []
            
            while contour:
                # Draw rectangles
                bound_rect = cv.BoundingRect(list(contour))
                contour = contour.h_next()
                pt1 = (bound_rect[0], bound_rect[1])
                pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
                print pt1
                    
                
                points.append(pt1)
                points.append(pt2)
                cv.Rectangle(self.img, pt1, pt2, cv.CV_RGB(255,0,0), 1)
                if (len(points) and i > 2):
                    i = 0
                    center_point = reduce(lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), points)

                    xRange = self.bottomLeft[0] - self.topRight[0]
                    yRange = self.topRight[1] - self.bottomLeft[1]

                    # x = lowestValue + (center_point[0] / width) * xRange
                    dmxCoordinate = (int(self.bottomLeft[0] - (float(center_point[0]) / self.width) * xRange), int(self.topRight[1] - (float(center_point[1]) / self.height) * yRange))

                    print dmxCoordinate, "bei: ", center_point
                    self.moveDmxTo(dmxCoordinate)

                    cv.Circle(self.img, center_point, 40, cv.CV_RGB(255, 255, 255), 1)
                    cv.Circle(self.img, center_point, 30, cv.CV_RGB(255, 100, 0), 1)

                

            num_points = len(points)

            if num_points:
                x = 0
                for point in points:
                    x += point[0]
                x /= num_points

                movement.append(x)
                            #display the image
            cv.ShowImage("Target", self.img)

            if cv.WaitKey(150) == 27:
                del(self.img)
                del self.capture
                # close socket connection
                print >>sys.stderr, 'closing socket'
                self.sock.close()

                break

if __name__ == "__main__":
    t = Target()
    t.run()
