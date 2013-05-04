#!/usr/bin/env python

import cv
import array
from ola.ClientWrapper import ClientWrapper


class Target:

    width, height = 1280, 720

    center = (125, 40)
    topRight = (115, 52)
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
        position = (self.restrict(position[0], 0, 255), self.restrict(position[1], 0, 255))
        data = array.array('B')
        data.append(position[0])
        data.append(0)
        data.append(position[1])
        data.append(0)
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
        # Capture first frame to get size
        frame = cv.QueryFrame(self.capture)
        frame_size = cv.GetSize(frame)
        color_image = cv.CreateImage(cv.GetSize(frame), 8, 3)
        grey_image = cv.CreateImage(cv.GetSize(frame), cv.IPL_DEPTH_8U, 1)
        moving_average = cv.CreateImage(cv.GetSize(frame), cv.IPL_DEPTH_32F, 3)

        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()

        first = True
        i = 0
        while True:
            closest_to_left = cv.GetSize(frame)[0]
            closest_to_right = cv.GetSize(frame)[1]
            i = i+1
            color_image = cv.QueryFrame(self.capture)

            # Smooth to get rid of false positives
            cv.Smooth(color_image, color_image, cv.CV_GAUSSIAN, 3, 0)

            if first:
                difference = cv.CloneImage(color_image)
                temp = cv.CloneImage(color_image)
                cv.ConvertScale(color_image, moving_average, 1.0, 0.0)
                first = False
            else:
                cv.RunningAvg(color_image, moving_average, 0.020, None)

            # Convert the scale of the moving average.
            cv.ConvertScale(moving_average, temp, 1.0, 0.0)

            # Minus the current frame from the moving average.
            cv.AbsDiff(color_image, temp, difference)

            # Convert the image to grayscale.
            cv.CvtColor(difference, grey_image, cv.CV_RGB2GRAY)

            # Convert the image to black and white.
            cv.Threshold(grey_image, grey_image, 70, 255, cv.CV_THRESH_BINARY)

            # Dilate and erode to get people blobs
            cv.Dilate(grey_image, grey_image, None, 18)
            cv.Erode(grey_image, grey_image, None, 10)

            storage = cv.CreateMemStorage(0)
            contour = cv.FindContours(grey_image, storage, cv.CV_RETR_CCOMP, cv.CV_CHAIN_APPROX_SIMPLE)
            points = []

            while contour:

                bound_rect = cv.BoundingRect(list(contour))
                contour = contour.h_next()

                pt1 = (bound_rect[0], bound_rect[1])
                pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
                points.append(pt1)
                points.append(pt2)
                #cv.Rectangle(color_image, pt1, pt2, cv.CV_RGB(255,0,0), 1)

            if (len(points) and i > 2):
                i = 0
                center_point = reduce(lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), points)

                xRange = self.bottomLeft[0] - self.topRight[0]
                yRange = self.topRight[1] - self.bottomLeft[1]

                # x = lowestValue + (center_point[0] / width) * xRange
                dmxCoordinate = (int(self.bottomLeft[0] - (float(center_point[0]) / self.width) * xRange), int(self.topRight[1] - (float(center_point[1]) / self.height) * yRange))

                print dmxCoordinate, "bei: ", center_point
                self.moveDmxTo(dmxCoordinate)

                cv.Circle(color_image, center_point, 40, cv.CV_RGB(255, 255, 255), 1)
                cv.Circle(color_image, center_point, 30, cv.CV_RGB(255, 100, 0), 1)
                #cv.Circle(color_image, center_point, 20, cv.CV_RGB(255, 255, 255), 1)
                #cv.Circle(color_image, center_point, 10, cv.CV_RGB(255, 100, 0), 1)

            cv.ShowImage("Target", color_image)

            # Listen for ESC key
            c = cv.WaitKey(7) % 0x100
            if c == 27:
                break

if __name__ == "__main__":
    t = Target()
    t.run()
