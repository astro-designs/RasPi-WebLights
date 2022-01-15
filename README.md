![RasPi-Weblights](Banner_Logo_RasPi-WebLights.png)

A project by Mark Cantrill / Astro-Designs

**install from GitHub:**

Please note that this project requires the rpi_ws281x Python library. The easiest way to install this is to get yourself a Unicorn-Hat / pHat from Pimoroni and follow their instructions for the Unicorn-Hat / pHat. The hardware built for this project, much like most Raspberry Pi Neopixel / WS281x based RGB light projects, is compatible with the Pimoroni Unicorn-Hat/pHat.

The rpi_ws281x Python library can be found here:
https://github.com/pimoroni/rpi_ws281x-python


```
git clone https://github.com/astro-designs/RasPi-WebLights.git
```

RasPi-Weblights uses Flask so one of the first thing you need to do is to install the Flask framework. Flask requires no additional packages, we only need the basic package.

```
sudo pip install flask
```

Once the basic installation is complete, you're ready to configure and run the program

Edit the configuration file WebLight_conf.py to configure the application for the number of lights in your string, set the initial mode and brightness.

```
cd RasPi-WebLights
nano WebLight_conf.py
sudo python app.py
```

Once running, you should be able to navigate to the RasPi-WebLights html page to control your lights.
