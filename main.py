#!/usr/bin/env python

import cv
import array
from ola.ClientWrapper import ClientWrapper


class Target:

    #width, height = 640, 480
    width, height = 1280, 720

    center = (125, 40)
    topRight = (113, 52)
    bottomLeft = (137, 21)

    def __init__(self):
        # self.capture = cv.CaptureFromCAM(1)
        self.capture = cv.CreateCameraCapture(1)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)
        cv.NamedWindow("Target", 1)

    def _DmxSent(self, state):
        self.wrapper.Stop()

    def restrict(self, val, minval, maxval):
        if val < minval: return minval
        if val > maxval: return maxval
        return val

    def moveDmxTo(self, position):
        #position = (self.restrict(position[0], 0, 255), self.restrict(position[1], 0, 255))
        data = array.array('B')
        pan = self.restrict(position[0] >> 8, 0, 255)
        panFine = self.restrict(0xFF & position[0], 0, 255)
        tilt = self.restrict(position[1] >> 8, 0, 255)
        tiltFine = self.restrict(0xFF & position[1], 0, 255)

        print "pan: ", pan, " panFine: ", panFine, " tilt: ", tilt, " tiltFine: ", tiltFine

        data.append(pan)
        data.append(panFine)
        data.append(tilt)
        data.append(tiltFine)
        data.append(255)
        data.append(134)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)
        data.append(0)

        self.client.SendDmx(1, data, self._DmxSent)
        self.wrapper.Run()

    def run(self):
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()
        i = 0
        while True:
            if (++i > 7): i = 0

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
            cv.InRangeS(hsv_img, (75, 100, 100), (130, 255, 255), thresholded_img)

            #determine the objects moments and check that the area is large
            #enough to be our object
            mat = cv.GetMat(thresholded_img)
            moments = cv.Moments(mat, 0)
            area = cv.GetCentralMoment(moments, 0, 0)

            #there can be noise in the video so ignore objects with small areas
            if(area > 100000):
                #determine the x and y coordinates of the center of the object
                #we are tracking by dividing the 1, 0 and 0, 1 moments by the area
                x = cv.GetSpatialMoment(moments, 1, 0)/area
                y = cv.GetSpatialMoment(moments, 0, 1)/area

                #print 'x: ' + str(x) + ' y: ' + str(y) + ' area: ' + str(area)

                xRange = (self.bottomLeft[0] << 8) - (self.topRight[0] << 8)
                yRange = (self.topRight[1] << 8) - (self.bottomLeft[1] << 8)
                #print "xRange: ", xRange, " yRange: ", yRange
                dmxCoordinate = (int((self.bottomLeft[0] << 8) - (x / self.width) * xRange), int((self.topRight[1] << 8) - (y / self.height) * yRange))

                self.moveDmxTo(dmxCoordinate)

                #create an overlay to mark the center of the tracked object
                overlay = cv.CreateImage(cv.GetSize(img), 8, 3)

                cv.Circle(overlay, (int(x), int(y)), 2, (255, 255, 255), 20)
                cv.Add(img, overlay, img)
                #add the thresholded image back to the img so we can see what was
                #left after it was applied
                cv.Merge(thresholded_img, None, None, None, img)

            #display the image
            cv.ShowImage("Target", img)

            del(img)
            del(hsv_img)
            del(thresholded_img)

            if cv.WaitKey(10) == 27:
                del self.capture
                break

if __name__ == "__main__":
    t = Target()
    t.run()
