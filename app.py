'''

RasPi-WebLights - Control Neopixels from a webpage - created by Mark Cantrill @Astro-Designs

'''
version = "1.0.25"

import os
import sys
import subprocess
import logging
import time
import datetime
import RPi.GPIO as GPIO
import WebLights_conf
from random import seed
from random import randint
from rpi_ws281x import __version__ as __rpi_ws281x__, PixelStrip, Color
from array import *
import requests
from threading import Thread
#import neopixel_modes

from flask import Flask, render_template, request
app = Flask(__name__)

# Setup Log to file function
logfile = 'logs/' + time.strftime("%B-%d-%Y-%I-%M-%S%p") + '.log'
logger = logging.getLogger('myapp')
hdlr = logging.FileHandler(logfile)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

# LED strip configuration:
LED_COUNT       = WebLights_conf.LED_COUNT
LED_PIN         = 18      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ     = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA         = 5       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS  = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT      = False   # True to invert the signal (when using NPN transistor level shift)

# Initial configuration
mode            = WebLights_conf.mode
prev_mode       = WebLights_conf.mode
brightness      = WebLights_conf.brightness
running         = False
colorFMT        = WebLights_conf.colorFMT

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Seed the random number generator
seed()

# Create a list called modes to store the mode name of each mode:
modes = {
   0  : {'name' : "White",                  'R' : 255, 'G' : 255, 'B' : 255, 'Br' : 50},
   1  : {'name' : "Candle",                 'R' : 255, 'G' : 147, 'B' :  41, 'Br' : 50},
   2  : {'name' : "Tungsten",               'R' : 255, 'G' : 214, 'B' : 170, 'Br' : 50},
   3  : {'name' : "Halogen",                'R' : 255, 'G' : 241, 'B' : 224, 'Br' : 50},
   4  : {'name' : "Overcast",               'R' : 201, 'G' : 226, 'B' : 255, 'Br' : 50},
   5  : {'name' : "ClearBlueSky",           'R' :  64, 'G' : 156, 'B' : 255, 'Br' : 50},
   6  : {'name' : "Yellow",                 'R' : 255, 'G' : 255, 'B' :   0, 'Br' : 50},
   7  : {'name' : "Cyan",                   'R' :   0, 'G' : 255, 'B' : 255, 'Br' : 50},
   8  : {'name' : "Green",                  'R' :   0, 'G' : 255, 'B' :   0, 'Br' : 50},
   9  : {'name' : "Magenta",                'R' : 255, 'G' :   0, 'B' : 255, 'Br' : 50},
   10 : {'name' : "Blue",                   'R' :   0, 'G' :   0, 'B' : 255, 'Br' : 50},
   11 : {'name' : "Red",                    'R' : 255, 'G' :   0, 'B' :   0, 'Br' : 50},
   12 : {'name' : "Cylon",                  'R' :   0, 'G' :   0, 'B' :   0, 'Br' : 50},
   13 : {'name' : "KnightRider",            'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   14 : {'name' : "TwinkleColours",         'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   15 : {'name' : "TheaterChaseRainbow",    'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   16 : {'name' : "RainbowCycle",           'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   17 : {'name' : "CheerLights",            'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   18 : {'name' : "Pacman",                 'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   19 : {'name' : "TheaterChaseWhite",      'R' : 255, 'G' : 255, 'B' : 255, 'Br' : 50},
   20 : {'name' : "TheaterChaseRed",        'R' : 255, 'G' : 000, 'B' : 000, 'Br' : 50},
   21 : {'name' : "TheaterChaseGreen",      'R' : 000, 'G' : 255, 'B' : 000, 'Br' : 50},
   21 : {'name' : "TheaterChaseBlue",       'R' : 000, 'G' : 000, 'B' : 255, 'Br' : 50},
   23 : {'name' : "RainbowCycle",           'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   24 : {'name' : "TheaterChaseRainbow",    'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   25 : {'name' : "CountDown",              'R' : 000, 'G' : 000, 'B' : 000, 'Br' : 50},
   26 : {'name' : "White_5min",             'R' : 255, 'G' : 255, 'B' : 255, 'Br' : 75}
   }

# Create a dictionary called pins to store the pin number, name, and pin state:
pins = {
   23 : {'name' : 'GPIO 23', 'state' : GPIO.LOW},
   24 : {'name' : 'GPIO 24', 'state' : GPIO.LOW}
   }

# Set each pin as an output and make it low:
for pin in pins:
   GPIO.setup(pin, GPIO.OUT)
   GPIO.output(pin, GPIO.LOW)
   
def RGB2GRB(color):
   # Swap the red & green colors (needed for some lighting strips)
   white = (color & (255 << 24)) >> 24
   red = (color & (255 << 16)) >> 16
   green = (color & (255 << 8)) >> 8
   blue = (color & 255)
   return (white << 24) | (green << 16)| (red << 8) | blue
   
def dimmer(color, brightness):
   # Adjust the brightness
   white = (color & (255 << 24)) >> 24
   red = (color & (255 << 16)) >> 16
   green = (color & (255 << 8)) >> 8
   blue = (color & 255)

   red = int(red * (brightness / 100.0))
   green = int(green * (brightness / 100.0))
   blue = int(blue * (brightness / 100.0))
   white = int(white * (brightness / 100.0))
 
   if red > 255: red = 255
   if green > 255: green = 255
   if blue > 255: blue = 255
   if white > 255: white = 255

   return (white << 24) | (red << 16)| (green << 8) | blue
   
# Convert named colours to 24bit RGB colours
namesToRGB = {'red':        Color(255,  0,  0),
    		'green':        Color(  0,255,  0),
    		'blue':         Color(  0,  0,255),
    		'cyan':         Color(  0,255,255),
    		'white':        Color(255,255,255),
    		'warmwhite':    Color(253,245,230),
    		'grey':         Color(128,128,128),
    		'purple':       Color(128,  0,128),
    		'magenta':      Color(255,  0,255),
    		'yellow':       Color(255,255,  0),
    		'orange':       Color(255,165,  0),
    		'pink':         Color(255,192,203),
    		'candle':       Color(255,147, 41),
    		'tungsten':     Color(255,214,170),
    		'halogen':      Color(255,241,224),
    		'overcast':     Color(201,226,255),
    		'clearbluesky': Color( 64,156,255),
    		'oldlace':      Color(253,245,230)}

# Define a function to control the brightness
def setBrightness(red_100, green_100, blue_100, brightness = 100):
	global red, green, blue
	red = int(red_100 * (brightness / 100.0))
	green = int(green_100 * (brightness / 100.0))
	blue = int(blue_100 * (brightness / 100.0))
	if red > 255: red = 255
	if green > 255: green = 255
	if blue > 255: blue = 255

# Define a function to set all LEDs to black / off.
def allBlack(strip, wait_ms=50):
	color = Color(0,0,0)
	#print('Colour (R, G, B): ', color)
	for i in range(strip.numPixels()):
		strip.setPixelColor(i,color)
		if wait_ms > 0:
			time.sleep(wait_ms/1000.0)
	strip.show()
	time.sleep(1)

# Define a function to set all LEDs to white.
def allWhite(strip, wait_ms=50):
	color = namesToRGB['white']
	for i in range(strip.numPixels()):
		strip.setPixelColor(i,color)
		if wait_ms > 0:
			time.sleep(wait_ms/1000.0)
	strip.show()
	time.sleep(1)

# Define a function to set all LEDs to a colour.
def colorWipe(strip, color, wait_ms=50):
	for i in range(strip.numPixels()):
		strip.setPixelColor(i, color)
		if wait_ms > 0:
			time.sleep(wait_ms/1000.0)
	strip.show()
	time.sleep(1)
   
# Function to continuously sweep eight green LEDs from one end of the array to the other
def cylon(strip, wait_ms=50):
	#print("By your command!")
	dir = 1
	i = 10
	i1 = 9
	i2 = 8
	i3 = 7
	i4 = 6
	i5 = 5
	i6 = 4
	i7 = 3
	i8 = 2
	i9 = 1
	current_mode = mode

	while mode == current_mode:
		strip.setPixelColor(i,  Color(16,16,16))
		strip.setPixelColor(i1, Color(0,32,0))
		strip.setPixelColor(i2, Color(0,64,0))
		strip.setPixelColor(i3, Color(0,200,0))
		strip.setPixelColor(i4, Color(0,255,0))
		strip.setPixelColor(i5, Color(0,255,0))
		strip.setPixelColor(i6, Color(0,200,0))
		strip.setPixelColor(i7, Color(0,64,0))
		strip.setPixelColor(i8, Color(0,32,0))
		strip.setPixelColor(i9, Color(16,16,16))
		strip.show()
		
		i9 = i8
		i8 = i7
		i7 = i6
		i6 = i5
		i5 = i4
		i4 = i3
		i3 = i2
		i2 = i1
		i1 = i
		
		if i == 1:
			dir = 1
			i+=1
		elif i == strip.numPixels()-1:
			dir = 0
			i-=1
		elif dir == 1:
			i+=1
		else:
			i-=1
		
		time.sleep(wait_ms/1000.0)
      
# Function to create a red comet-tail effect sweeping continuously from one end of the array to the other.
def kitt(strip, wait_ms=50):
	#print("Hello, I'm the Knight Industries Two-Thousand!")
	dir = 1
	i   = 30
	i1  = 29
	i2  = 28
	i3  = 27
	i4  = 26
	i5  = 25
	i6  = 24
	i7  = 23
	i8  = 22
	i9  = 21
	i10 = 20
	i11 = 19
	i12 = 18
	i13 = 17
	i14 = 16
	i15 = 15
	i16 = 14
	i17 = 13
	i18 = 12
	i19 = 11
	i20 = 10
	i21 = 9
	i22 = 8
	i23 = 7
	i24 = 6
	i25 = 5
	i26 = 4
	i27 = 3
	i28 = 2
	i29 = 1
	current_mode = mode

	while mode == current_mode:
		strip.setPixelColor(i,   Color(255,0,0))
		strip.setPixelColor(i1,  Color(255,0,0))
		strip.setPixelColor(i2,  Color(255,0,0))
		strip.setPixelColor(i3,  Color(255,0,0))
		strip.setPixelColor(i4,  Color(200,0,0))
		strip.setPixelColor(i5,  Color(200,0,0))
		strip.setPixelColor(i6,  Color(200,0,0))
		strip.setPixelColor(i7,  Color(150,0,0))
		strip.setPixelColor(i8,  Color(150,0,0))
		strip.setPixelColor(i9,  Color(150,0,0))
		strip.setPixelColor(i10, Color(100,0,0))
		strip.setPixelColor(i11, Color(100,0,0))
		strip.setPixelColor(i12, Color(100,0,0))
		strip.setPixelColor(i13, Color(50,0,0))
		strip.setPixelColor(i14, Color(50,0,0))
		strip.setPixelColor(i15, Color(50,0,0))
		strip.setPixelColor(i16, Color(50,0,0))
		strip.setPixelColor(i17, Color(25,0,0))
		strip.setPixelColor(i18, Color(25,0,0))
		strip.setPixelColor(i19, Color(25,0,0))
		strip.setPixelColor(i20, Color(25,0,0))
		strip.setPixelColor(i21, Color(12,0,0))
		strip.setPixelColor(i22, Color(12,0,0))
		strip.setPixelColor(i23, Color(12,0,0))
		strip.setPixelColor(i24, Color(12,0,0))
		strip.setPixelColor(i25, Color(6,0,0))
		strip.setPixelColor(i26, Color(6,0,0))
		strip.setPixelColor(i27, Color(6,0,0))
		strip.setPixelColor(i28, Color(6,0,0))
		strip.setPixelColor(i29, Color(0,0,0))
		strip.show()
		
		i29 = i28
		i28 = i27
		i27 = i26
		i26 = i25
		i25 = i24
		i24 = i23
		i23 = i22
		i22 = i21
		i21 = i20
		i20 = i19
		i19 = i18
		i18 = i17
		i17 = i16
		i16 = i15
		i15 = i14
		i14 = i13
		i13 = i12
		i12 = i11
		i11 = i10
		i10 = i9
		i9  = i8
		i8  = i7
		i7  = i6
		i6  = i5
		i5  = i4
		i4  = i3
		i3  = i2
		i2  = i1
		i1  = i
		
		if i == 1:
			dir = 1
			i+=1
		elif i == strip.numPixels()-1:
			dir = 0
			i-=1
		elif dir == 1:
			i+=1
		else:
			i-=1
		
		time.sleep((200 / strip.numPixels()) * wait_ms/1000.0)


# One-dimensional Pacman...
def pacman(strip, wait_ms=50):

	food_pos = []

	# The board components...
	pacman = 1
	redghost = 2
	blueghost = 3
	food = 4
	star = 5
	pactime = 4
	
	# Initial positions...
	pacman_pos = 1 # randint(1,10)
	pacman_dir = 1 #left to right
	redghost_pos = -90 + randint(0,19)
	redghost2_pos = -115 + randint(0,9)
	redghost3_pos = -125 + randint(0,9)
	ghost_dir = 1 #left to right
	blueghost_pos = -1000
	blueghost2_pos = -1020
	blueghost3_pos = -1030
	star_pos = 140 + randint(0,6)*5
	for i in range(0, strip.numPixels()):
		food_pos.append(1)
	for i in range(0, strip.numPixels()):
		if i % 5 == 0:
			food_pos[i] = 1
		else:
			food_pos[i] = 0

	current_mode = mode
	while mode == current_mode:

		# Timer...
		if pactime > 0:
			pactime = pactime - 1
		else:
			pactime = 699

		#print("Star pos: ", star_pos)
		#print(randint(0,6))
		#print("Red Ghost #1 pos: ", redghost_pos)
		#print("Red Ghost #2 pos: ", redghost2_pos)
		#print("Red Ghost #3 pos: ", redghost3_pos)
		
		# display board...
		for i in range(0, strip.numPixels()):
			if i == redghost_pos or i-1 == redghost_pos or i+1 == redghost_pos:
				color = Color(255, 0, 0) # red
			elif i == redghost2_pos or i-1 == redghost2_pos or i+1 == redghost2_pos:
				color = Color(255, 0, 0) # red
			elif i == redghost3_pos or i-1 == redghost3_pos or i+1 == redghost3_pos:
				color = Color(255, 0, 0) # red
			elif i == pacman_pos or i-1 == pacman_pos or i+1 == pacman_pos:
				color = Color(255, 255, 0) # yellow
			elif i == blueghost_pos or i-1 == blueghost_pos or i+1 == blueghost_pos:
				color = Color(0, 0, 255) # blue
			elif i == blueghost2_pos or i-1 == blueghost2_pos or i+1 == blueghost2_pos:
				color = Color(0, 0, 255) # blue
			elif i == blueghost3_pos or i-1 == blueghost3_pos or i+1 == blueghost3_pos:
				color = Color(0, 0, 255) # blue
			elif i == star_pos:
				color = Color(255, 255, 255) # Bright white
			elif food_pos[i] == 1:
				color = Color(12, 12, 12) # white
			else:
				color = Color(0, 0, 0) # black

			strip.setPixelColor(i, color)
		
		strip.show()
		
		# Move
		if pactime % 3 == 0:
			# If out of range, head back into range...
			if pacman_dir < 0:
				pacman_dir = 1
			elif pacman_dir > strip.numPixels()-1:
				pacman_dir = 0
				
			# Just move back & forward between end points
			if pacman_dir == 1:
				if pacman_pos < strip.numPixels()-1:
					pacman_pos = pacman_pos + 1
				else:
					pacman_dir = 0
			else:
				if pacman_pos > 0:
					pacman_pos = pacman_pos - 1
				else:
					pacman_dir = 1

		# Red ghost runs towards pacman
		# slightly faster than pacman
		if pactime % 2 == 0:
			if redghost_pos < pacman_pos:
				redghost_pos = redghost_pos + 1
			else:
				redghost_pos = redghost_pos - 1

			if redghost2_pos < pacman_pos:
				redghost2_pos = redghost2_pos + 1
			else:
				redghost2_pos = redghost2_pos - 1

			if redghost3_pos < pacman_pos:
				redghost3_pos = redghost3_pos + 1
			else:
				redghost3_pos = redghost3_pos - 1

		# Eat the food...
		# (if pacman is on the board...)
		if pacman_pos > -1 and pacman_pos < strip.numPixels()-1:
			if food_pos[pacman_pos] == 1:
				#print("Yum")
				food_pos[pacman_pos] = 0
			
		# Eat the star...
		if pacman_pos == star_pos:
			#print("Yum!!! A pill!")
			pacman_dir = 0
			star_pos = -1
			blueghost_pos = redghost_pos
			blueghost2_pos = redghost2_pos
			blueghost3_pos = redghost3_pos
			redghost_pos = -1000
			redghost2_pos = -900
			redghost3_pos = -500

		# pacman eats blue ghost...
		if pacman_pos == blueghost_pos:
			#print("YUM!!! Eat blue ghost")
			blueghost_pos = -1000
		else:
			# Blue ghost runs away from pacman
			# slightly slower than pacman
			if pactime % 4 == 0:
				if blueghost_pos < pacman_pos:
					blueghost_pos = blueghost_pos - 1
				else:
					blueghost_pos = blueghost_pos + 1

		if pacman_pos == blueghost2_pos:
			#print("YUM!!! Eat blue ghost")
			blueghost2_pos = -1000
		else:
			# Blue ghost runs away from pacman
			# slightly slower than pacman
			if pactime % 4 == 0:
				if blueghost2_pos < pacman_pos:
					blueghost2_pos = blueghost2_pos - 1
				else:
					blueghost2_pos = blueghost2_pos + 1

		if pacman_pos == blueghost3_pos:
			#print("YUM!!! Eat blue ghost")
			blueghost3_pos = -1000
		else:
			# Blue ghost runs away from pacman
			# slightly slower than pacman
			if pactime % 4 == 0:
				if blueghost3_pos < pacman_pos:
					blueghost3_pos = blueghost3_pos - 1
				else:
					blueghost3_pos = blueghost3_pos + 1


		# redghost eats pacman
		# Send pacman off the board one way or the other...
		if pacman_pos == redghost_pos or pacman_pos == redghost2_pos or pacman_pos == redghost3_pos:
			#print("Arrrrgh!!!")
			if pacman_dir == 1:
				pacman_pos = pacman_pos + 500
			else:
				pacman_pos = pacman_pos - 500

			
		# Re-initialise if game over
		if (pacman_pos < 0 or pacman_pos > strip.numPixels()-1) and (redghost_pos < 0 or redghost_pos > strip.numPixels()-1) and (redghost2_pos < 0 or redghost2_pos > strip.numPixels()-1) and (redghost3_pos < 0 or redghost3_pos > strip.numPixels()-1) and (blueghost_pos < 0 or blueghost_pos > strip.numPixels()-1) and (blueghost2_pos < 0 or blueghost2_pos > strip.numPixels()-1) and (blueghost3_pos < 0 or blueghost3_pos > strip.numPixels()-1):
			pacman_pos = 1
			pacman_dir = 1 #left to right
			redghost_pos = -80 + randint(0,19)
			redghost2_pos = -105 + randint(0,9)
			redghost3_pos = -120 + randint(0,9)
			ghost_dir = 1 #left to right
			blueghost_pos = -1000
			blueghost2_pos = -1020
			blueghost3_pos = -1030
			star_pos = 140 + randint(0,6)*5
			for i in range(0, strip.numPixels()):
				food_pos.append(1)
			for i in range(0, strip.numPixels()):
				if i % 5 == 0:
					food_pos[i] = 1
				else:
					food_pos[i] = 0
			
		time.sleep(wait_ms/1000)
	time.sleep(1)
		
# Function to create a strip of randomly coloured lights that fade in and fade out, changing colour each time they fade out.
def ChristmasLights(strip, wait_ms=50):

	global red, green, blue
	
	brightness_array = []
	col = []
	for i in range(0, strip.numPixels()):
		brightness_array.append(1)
		col.append(1)

	# Initialise colour & brightness arrays...	
	for i in range(0, strip.numPixels()):
		brightness_array[i] = randint(0,50) - 25
		col[i] = 8

	current_mode = mode

	while mode == current_mode:
			
		for i in range(0, strip.numPixels()):
			if brightness_array[i] >= 25:
				brightness_array[i] = -25
			else:
				brightness_array[i] = brightness_array[i] + 1
				
			if brightness_array[i] == 0:
				col[i] = randint(0,7)
			
			if col[i] == 0:   # White
				red = 255
				green = 255
				blue = 255
			elif col[i] == 1: # Yellow
				red = 0
				green = 255
				blue = 255
			elif col[i] == 2: # Cyan
				red = 255
				green = 255
				blue = 0
			elif col[i] == 3: # Green
				red = 0
				green = 255
				blue = 0
			elif col[i] == 4: # Magenta
				red = 255
				green = 0
				blue = 255
			elif col[i] == 5: # Blue
				red = 0
				green = 0
				blue = 255
			elif col[i] == 6: # Red
				red = 255
				green = 0
				blue = 0
			elif col[i] == 7: # Grey
				red = 128
				green = 128
				blue = 128
			else:             # Black
				red = 0
				green = 0
				blue = 0

			brightness = abs(brightness_array[i]) * 4
			setBrightness(red, green, blue, brightness)
			strip.setPixelColor(i, Color(red, green, blue))
	
		strip.show()
		time.sleep(wait_ms/1000.0)

# Function to read the current Cheerlights feed colour and apply the colour to all LEDs
def cheerlights(strip, wait_ms=1000):
    global modes
    #print("Cheerlights...")
    
    #process the currently available list of colours
    r = requests.get('http://api.thingspeak.com/channels/1417/field/1/last.json', timeout=2)
    data = r.json()
    name = data['field1']
    name.strip()
    modes[17]['name'] = "Cheerlights (" + name + ")"
    color = namesToRGB[name]
    color = dimmer(color, brightness)
    if colorFMT == 'GRB':
       color = RGB2GRB(color)
    colorWipe(strip, color, 0)
    time.sleep(wait_ms/1000.0)

    current_mode = mode

    while mode == current_mode:
        r = requests.get('http://api.thingspeak.com/channels/1417/field/1/last.json', timeout=2)
        data = r.json()
        name = data['field1']
        name.strip()
        #print ("Cheerlights: ", name)
        modes[17]['name'] = "Cheerlights (" + name + ")"
        color = namesToRGB[name]
        color = dimmer(color, brightness)
        if colorFMT == 'GRB':
           color = RGB2GRB(color)
        colorWipe(strip, color, 0)
        time.sleep(wait_ms/1000.0)
	
def theaterChase(strip, color, wait_ms=25):
	#print("Movie theater light style chaser animation.")

	current_mode = mode

	while mode == current_mode:
		dimmed_color = dimmer(color, brightness)
		for q in range(3):
			for i in range(0, strip.numPixels(), 3):
				strip.setPixelColor(i+q, dimmed_color)
			strip.show()
			time.sleep(wait_ms/1000.0)
			for i in range(0, strip.numPixels(), 3):
				strip.setPixelColor(i+q, 0)
				

def wheel(pos):
	"""Generate rainbow colors across 0-255 positions."""
	if pos < 85:
		return Color(pos * 3, 255 - pos * 3, 0)
	elif pos < 170:
		pos -= 85
		return Color(255 - pos * 3, 0, pos * 3)
	else:
		pos -= 170
		return Color(0, pos * 3, 255 - pos * 3)
		

def rainbow(strip, wait_ms=20, iterations=1):
	"""Draw rainbow that fades across all pixels at once."""
	j = 0
	current_mode = mode

	while mode == current_mode:
		for i in range(strip.numPixels()):
			color = wheel((i+j) & 255)
			color = dimmer(color, brightness)
			strip.setPixelColor(i, color)
		strip.show()
		time.sleep(wait_ms/1000.0)
		if j < (256*iterations)-1:
			j += 1
		else:
			j = 0

	time.sleep(1)
	

def rainbowCycle(strip, wait_ms=20, iterations=5):
	#print("Draw rainbow that uniformly distributes itself across all pixels.")
	
	# Initialise variables...
	j = 0
	
	# Wait for the Mode button to be pressed or for all iterations to be complete
	current_mode = mode

	while mode == current_mode and j < (256*iterations)-1:
		for i in range(strip.numPixels()):
			color = wheel((int(i * 256 / strip.numPixels()) + j) & 255)
			color = dimmer(color, brightness)
			strip.setPixelColor(i, color)
		strip.show()
		time.sleep(wait_ms/1000.0)
		if j < (256*iterations)-1:
			j += 1
		else:
			j = 0

	time.sleep(1)

def theaterChaseRainbow(strip, wait_ms=50):
	#print("Rainbow movie theater light style chaser animation.")
	
	# Initialise variables...
	j = 0

	current_mode = mode

	while mode == current_mode:
		for q in range(3):
			for i in range(0, strip.numPixels(), 3):
				color = wheel((i+j) % 255)
				color = dimmer(color, brightness)
				strip.setPixelColor(i+q, color)
			strip.show()
			time.sleep(wait_ms/1000.0)
			for i in range(0, strip.numPixels(), 3):
				strip.setPixelColor(i+q, 0)
		if j < 255:
			j += 1
		else:
			j = 0

def CountDown(strip, wait_ms=30):
	"""Countdown timer in binary with 10th second resolution."""
	global red, green, blue, mode
	
	brightness_array = []
	col = []
	for i in range(0, strip.numPixels()):
		brightness_array.append(1)
		col.append(1)

	# Initialise colour & brightness arrays...	
	for i in range(0, strip.numPixels()):
		brightness_array[i] = randint(0,50) - 25
		col[i] = 8

	offset = int(LED_COUNT / 2) - 13
	
	# Initialise alarm time...
	AlarmTime = (datetime.datetime(2021,7,13,0,0) - datetime.datetime(1970,1,1)).total_seconds()
	
	TimeLeft = AlarmTime - time.time()

	current_mode = mode

	while mode == current_mode and TimeLeft > 0:
		for i in range(0, strip.numPixels()):
			if TimeLeft > 0:
				#color = Color(64, 0, 0) # red
				#strip.setPixelColor(i, color)
				
				if brightness_array[i] >= 25:
					brightness_array[i] = -25
				else:
					brightness_array[i] = brightness_array[i] + 1
					
				if brightness_array[i] == 0:
					col[i] = randint(0,7)
				
				if col[i] == 0:   # White
					red = 255
					green = 255
					blue = 255
				elif col[i] == 1: # Yellow
					red = 0
					green = 255
					blue = 255
				elif col[i] == 2: # Cyan
					red = 255
					green = 255
					blue = 0
				elif col[i] == 3: # Green
					red = 0
					green = 255
					blue = 0
				elif col[i] == 4: # Magenta
					red = 255
					green = 0
					blue = 255
				elif col[i] == 5: # Blue
					red = 0
					green = 0
					blue = 255
				elif col[i] == 6: # Red
					red = 255
					green = 0
					blue = 0
				elif col[i] == 7: # Grey
					red = 128
					green = 128
					blue = 128
				else:             # Black
					red = 0
					green = 0
					blue = 0

				brightness = abs(brightness_array[i]) * 4
				setBrightness(red, green, blue, brightness)
				strip.setPixelColor(i, Color(red, green, blue))
				
				if (i >= offset) and (i < (offset + 26)):
					color = Color(0, 0, 0)
					strip.setPixelColor(i, color)
					if (i - offset) == 0: # Bit(15)
						if int(TimeLeft) & 32768 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 1: # Bit(14)
						if int(TimeLeft) & 16384 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 2: # Bit(13)
						if int(TimeLeft) & 8192 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 3: # Bit(12)
						if int(TimeLeft) & 4096 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 4: # Bit(11)
						if int(TimeLeft) & 2048 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 5: # Bit(10)
						if int(TimeLeft) & 1024 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 6: # Bit(9)
						if int(TimeLeft) & 512 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 7: # Bit(8)
						if int(TimeLeft) & 256 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 8: # Bit(7)
						if int(TimeLeft) & 128 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 9: # Bit(6)
						if int(TimeLeft) & 64 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 10: # Bit(5)
						if int(TimeLeft) & 32 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 11: # Bit(4)
						if int(TimeLeft) & 16 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 12: # Bit(3)
						if int(TimeLeft) & 8 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 13: # Bit(2)
						if int(TimeLeft) & 4 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 14: # Bit(1)
						if int(TimeLeft) & 2 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 15: # Bit(0)
						if int(TimeLeft) & 1 > 0:
							color = Color(255, 255, 255)
							strip.setPixelColor(i, color)
					if (i - offset) == 16: # (0)
						if TimeLeft - int(TimeLeft) > 0.05:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 17: # (0)
						if TimeLeft - int(TimeLeft) > 0.15:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 18: # (0)
						if TimeLeft - int(TimeLeft) > 0.25:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 19: # (0)
						if TimeLeft - int(TimeLeft) > 0.35:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 20: # (0)
						if TimeLeft - int(TimeLeft) > 0.45:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 21: # (0)
						if TimeLeft - int(TimeLeft) > 0.55:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 22: # (0)
						if TimeLeft - int(TimeLeft) > 0.65:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 23: # (0)
						if TimeLeft - int(TimeLeft) > 0.75:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 24: # (0)
						if TimeLeft - int(TimeLeft) > 0.85:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
					if (i - offset) == 25: # (0)
						if TimeLeft - int(TimeLeft) > 0.95:
							color = Color(0, 255, 0)
							strip.setPixelColor(i, color)
			else:
				
				color = Color(0, 0, 255)
				strip.setPixelColor(i, color)
				
		strip.show()
		time.sleep(wait_ms/1000.0)
		TimeLeft = AlarmTime - time.time()

	if TimeLeft < 0:
		mode = 16
		UpdateRequired = True
        
# Function to temporarily change the lights to all white, 75% max brightness
# Reverts to previous mode after 5 minutes
def White_5min(strip):
	global mode, brightness
	#print("Temporary program #1 - All white for 5 minutes")

	current_mode = mode
	current_brightness = brightness
	wait_ms = 50
	run_time = 6000 # Run for 5 minutes (6000 x 50ms)

	red = modes[mode]['R']
	green = modes[mode]['G']
	blue = modes[mode]['B']
	brightness = modes[mode]['Br']
	setBrightness(red, green, blue, brightness)
	colorWipe(strip, Color(red, green, blue),0)

	while mode == current_mode:
		if run_time > 1:
			time.sleep(wait_ms/1000.0)
			run_time = run_time - 1
		else:
			brightness = prev_brightness
			mode = prev_mode


class neopixel_prog:
   def __init__(self):
      self._running = True
      
   def terminate(self):
      self._running = False
            
   def run(self):
       global red, green, blue, running
       
       print("Running: ", running)
       if running == False:
           running = True
           print("Running neopixel_prog")

           while self._running:
               #print("Applying mode")
               if mode == 0: # White
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 1: # Candle
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 2: # Tungsten
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 3: # Halogen
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 4: # Overcast
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 5: # Clear Blue Sky
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 6: # Yellow
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 7: # Cyan
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 8: # Green
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 9: # Magenta
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 10: # Blue
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)
               elif mode == 11: # Red
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  setBrightness(red, green, blue, brightness)
                  colorWipe(strip, Color(red, green, blue),0)

               elif mode == 12:
                  cylon(strip,10)
               elif mode == 13:
                  kitt(strip,5)   
               elif mode == 14:
                  ChristmasLights(strip,30)
               elif mode == 15:
                  theaterChaseRainbow(strip)
               elif mode == 16:
                  rainbowCycle(strip)
               elif mode == 17:
                  cheerlights(strip,1000)
               elif mode == 18:
                  pacman(strip,7)
               elif mode == 19 or mode == 20 or mode== 21 or mode == 22:
                  red = modes[mode]['R']
                  green = modes[mode]['G']
                  blue = modes[mode]['B']
                  theaterChase(strip, Color(red, green, blue))  # White theater chase
               elif mode == 23:
                  rainbowCycle(strip)
               elif mode == 24:
                  theaterChaseRainbow(strip)
               elif mode == 25:
                  CountDown(strip)
               elif mode == 26:
                  White_5min(strip)

           running = False

# Create NeoPixel object with appropriate configuration.
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

# Create class...
lights = neopixel_prog()
# Create Thread
lights_thread = Thread(target = lights.run)

@app.route("/")
def main():

   # For each pin, read the pin state and store it in the pins dictionary:
   for pin in pins:
      pins[pin]['state'] = GPIO.input(pin)

   # Put the pin dictionary into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)

# The function below is executed when someone requests a URL with the pin number and action in it:
@app.route("/<changePin>/<action>")
def action(changePin, action):
   # Convert the pin from the URL into an integer:
   changePin = int(changePin)
   # Get the device name for the pin being changed:
   deviceName = pins[changePin]['name']
   # If the action part of the URL is "on," execute the code indented below:
   if action == "on":
      # Set the pin high:
      GPIO.output(changePin, GPIO.HIGH)
      # Save the status message to be passed into the template:
      message = "Turned " + deviceName + " on."
      #print(message)
      logger.info(message)
   if action == "off":
      GPIO.output(changePin, GPIO.LOW)
      message = "Turned " + deviceName + " off."
      #print(message)
      logger.info(message)

   # For each pin, read the pin state and store it in the pins dictionary:
   for pin in pins:
      pins[pin]['state'] = GPIO.input(pin)

   # Put the pin dictionary into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)
   
# The function below is executed when someone requests a mode change
@app.route("/mode<changeMode>")
def set_mode(changeMode):
   global mode, prev_mode, prev_brightness
   
   # Store previous mode & brightness if we need to switch back...
   prev_mode = mode
   prev_brightness = brightness
   
   # Append zeros to changeMode
   Mode = '000' + str(changeMode)
   Mode = Mode[-3:]
   
   mode = int(Mode)
   mode = min(mode, len(modes)-1)
   mode = max(mode, 0)
   
   message = "Setting Mode: " + str(mode)
   #print(message)
   logger.info(message)
   
   # Put the controls into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)

# The function below is executed when someone requests a mode change
@app.route("/random")
def random():
   global mode
   
   # Append zeros to changeMode
   changeMode = randint(1,len(modes))
   Mode = '000' + str(changeMode)
   Mode = Mode[-3:]
   
   mode = int(Mode)
   mode = min(mode, len(modes)-1)
   mode = max(mode, 0)
      
   message = "Setting Random Mode: " + str(mode)
   #print(message)
   logger.info(message)

   # Put the controls into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)

# The function below is executed when someone requests a brightness change
@app.route("/brightness/<changeBrightness>")
def set_brighness(changeBrightness):
   global brightness
   
   if changeBrightness == "up":
      if brightness < 10: brightness = brightness + 1
      else: brightness = brightness + 10
   elif changeBrightness == "down":
      if brightness <= 10: brightness = brightness - 1
      else: brightness = brightness - 10
   else:
      Brightness = '000' + str(changeBrightness)
      Brightness = Brightness[-3:]
      brightness = int(Brightness)

   brightness = min(brightness, 100)
   brightness = max(brightness, 0)

   message = "Setting Brightness: " + str(brightness)
   #print(message)
   logger.info(message)

   # Put the controls into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)
   
# The function below is executed when someone requests a URL a system call:
@app.route("/system/<action>")
def system(action):
   # If the action part of the URL is "on," execute the code indented below:
   if action == "shutdown":
      # Shutdown...
      message = "Shutting down..."
      #print(message)
      logger.info(message)
      os.system("sudo shutdown") 
   elif action == "exit":
      # Exit to the command prompt...
      message = "Closing..."
      #print(message)
      logger.info(message)
      sys.exit()
   elif action == "reboot":
      # Reboot...
      message = "Rebooting..."
      #print(message)
      logger.info(message)
      os.system("sudo reboot") 
   elif action == "ping":
      # Ping to check it's alive...
      message = "Received a Ping!"
      #print(message)
      logger.info(message)

   # Put the pin dictionary into the template data dictionary:
   templateData = {
      'version' : version,
      'logfile' : logfile,
      'num_modes' : len(modes),
      'modes' : modes,
      'mode' : mode,
      'brightness' : brightness,
	  'pins' : pins
      }

   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)

if __name__ == "__main__":

   message = "Starting RasPi-WebLights - Version" + str(version)
   #print(message)
   logger.info(message)

   # Initialise Neopixel strip
   message = "Initialising strip..."
   #print(message)
   logger.info(message)
   strip.begin()

   # Start lighting controller thread...
   message = "Starting lighting controller thread..."
   #print(message)
   logger.info(message)
   lights_thread.start()

   app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)
