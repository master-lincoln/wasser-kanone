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
    movementDetection = 0

    server_address = ('192.168.0.99', 10000)

    #width, height = 640, 480
    width, height = 800, 600
    skipPictures = 1
    offset = 0
    XOff = 10
    YOff = 14
    area = 900000

    # limit all pixels that don't match our criteria
    # OpenCV uses 0-180 as a hue range for the HSV color model
    # Orange  0-22
    # Yellow 22- 38
    # Green 38-75
    # Blue 75-130
    # Violet 130-160
    # Red 160-179
    colorLower = [0, 80, 65]
    colorUpper = [22, 255, 255]

    center = (41 << 8, 15 << 8)
    topRight = (28, 36) #32 33
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
        cv.CreateTrackbar("Area", "Target", 0, 20, self.setArea)
        cv.CreateTrackbar("MinColor", "Target", 0, 180, self.setMinCol)
        cv.CreateTrackbar("MaxColor", "Target", 0, 180, self.setMaxCol)
        cv.CreateTrackbar("MinVal", "Target", 0, 255, self.setMinVal)
        cv.CreateTrackbar("MaxVal", "Target", 0, 255, self.setMaxVal)
        cv.CreateTrackbar("X-Offset", "Target", 0, 20, self.setXOff)
        cv.CreateTrackbar("Y-Offset", "Target", 0, 20, self.setYOff)
        cv.CreateTrackbar("Movement", "Target", 0, 1, self.setMovement)
        # Set initial trackbar positions
        cv.SetTrackbarPos("MinColor", "Target", self.colorLower[0])
        cv.SetTrackbarPos("MaxColor", "Target", self.colorUpper[0])
        cv.SetTrackbarPos("MinVal", "Target", self.colorLower[1])
        cv.SetTrackbarPos("MaxVal", "Target", self.colorUpper[1])
        cv.SetTrackbarPos("X-Offset", "Target", self.XOff)
        cv.SetTrackbarPos("Y-Offset", "Target", self.YOff)
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

    def setXOff(self, value):
        self.XOff = value

    def setYOff(self, value):
        self.YOff = value

    def setMovement(self, value):
        self.movementDetection = value


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
        pan = (self.restrict(position[0] >> 8, 0, 255)) + (self.XOff-10)
        panFine = self.restrict(0xFF & position[0], 0, 255)
        tilt = (self.restrict(position[1] >> 8, 0, 255)) + (self.YOff-10)
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

        self.img = cv.QueryFrame(self.capture)
        grey_image = cv.CreateImage(cv.GetSize(self.img), cv.IPL_DEPTH_8U, 1)
        moving_average = cv.CreateImage(cv.GetSize(self.img), cv.IPL_DEPTH_32F, 3)
        difference = None
        movement = []
        i = 0
        while True:
            if (++i > self.skipPictures): i = 0

            self.img = cv.QueryFrame(self.capture)

            cv.Flip(self.img, flipMode=-1)

            #blur the source image to reduce color noise
            cv.Smooth(self.img, self.img, cv.CV_BLUR, 3)

            #If Difference should be computed
            if(self.movementDetection):
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
                    if (len(points)):
                        i = 0
                        center_point = reduce(lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), points)

                        xRange = (self.bottomLeft[0] << 8) - (self.topRight[0] << 8)
                        yRange = (self.topRight[1] << 8) - (self.bottomLeft[1] << 8)

                       # x = lowestValue + (center_point[0] / width) * xRange
                        self.dmxCoordinate = (int((self.bottomLeft[0] << 8) - (center_point[0] / self.width) * xRange)+5, int(((self.topRight[1]+self.offset) << 8) - (center_point[0] / self.height) * yRange))

                        print self.dmxCoordinate, "bei: ", center_point
                        if self.dmx:
                            self.moveDmxTo(self.dmxCoordinate, True)
                        if self.pump:
                            self.sendFire()

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
            
            if(self.movementDetection == 0):
                #convert the image to hsv(Hue, Saturation, Value) so its
                #easier to determine the color to track(hue)
                hsv_img = cv.CreateImage(cv.GetSize(self.img), 8, 3)
                cv.CvtColor(self.img, hsv_img, cv.CV_BGR2HSV)

                thresholded_img = cv.CreateImage(cv.GetSize(hsv_img), 8, 1)
                cv.InRangeS(hsv_img, self.colorLower, self.colorUpper, thresholded_img)

                #determine the objects moments and check that the area is large
                #enough to be our object
                mat = cv.GetMat(thresholded_img)
                moments = cv.Moments(mat, 0)
                area = cv.GetCentralMoment(moments, 0, 0)

                #there can be noise in the video so ignore objects with small areas
                if(area > self.area):
                    #determine the x and y coordinates of the center of the object
                    #we are tracking by dividing the 1, 0 and 0, 1 moments by the area
                    x = cv.GetSpatialMoment(moments, 1, 0)/area
                    y = cv.GetSpatialMoment(moments, 0, 1)/area

                    #print 'x: ' + str(x) + ' y: ' + str(y) + ' area: ' + str(area)

                    xRange = (self.bottomLeft[0] << 8) - (self.topRight[0] << 8)
                    yRange = (self.topRight[1] << 8) - (self.bottomLeft[1] << 8)
                    #print "xRange: ", xRange, " yRange: ", yRange
                    self.dmxCoordinate = (int((self.bottomLeft[0] << 8) - (x / self.width) * xRange)+5, int(((self.topRight[1]+self.offset) << 8) - (y / self.height) * yRange))

                    if self.dmx:
                        self.moveDmxTo(self.dmxCoordinate, True)
                    if self.pump:
                        self.sendFire()

                    #create an overlay to mark the center of the tracked object
                    overlay = cv.CreateImage(cv.GetSize(self.img), 8, 3)

                    cv.Circle(overlay, (int(x), int(y)), 2, (255, 255, 255), 20)
                    cv.Add(self.img, overlay, self.img)
                    #add the thresholded image back to the img so we can see what was
                    #left after it was applied
                    cv.Merge(thresholded_img, None, None, None, self.img)
                elif self.dmx:
                    self.moveDmxTo(self.dmxCoordinate, False)

                cv.SetMouseCallback("Target", self.mouse_callback, self.img)
                #display the image
                cv.ShowImage("Target", self.img)
                
                del(self.img)
                del(hsv_img)
                del(thresholded_img)
            
            if cv.WaitKey(150) == 27:
                del self.capture
                # close socket connection
                print >>sys.stderr, 'closing socket'
                self.sock.close()

                break

if __name__ == "__main__":
    t = Target()
    t.run()
