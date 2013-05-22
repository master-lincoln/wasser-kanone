#!/usr/bin/env python

import RPi.GPIO as GPIO

# to use Raspberry Pi board pin numbers
GPIO.setmode(GPIO.BOARD)

# set up the GPIO channels - one input and one output
GPIO.setup(1, GPIO.OUT)

# input from pin 11
#input_value = GPIO.input(11)

# output to pin 1
GPIO.output(1, GPIO.LOW)