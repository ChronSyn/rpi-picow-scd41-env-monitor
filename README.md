# Raspberry Pi Pico W - SCD41 Environment Monitor

The code in this repo is designed to read data from an SCD41 sensor, and send the data to an MQTT server.
It also listens for screen-on and reset messages via MQTT, allowing you to have some limited control via home assistant or another MQTT interface.

## Hardware

You will need the following hardware:

  - Raspberry Pi Pico W flashed with the Pimoroni firmware
  - SCD41 sensor
  - An SPI LCD display (I used a Waveshare 1.3" 240x240 SPI LCD display)
  - Recommended: A breakout board for the Pico W which exposes easy-connect headers (i.e. dupont connectors)
    - You'll also need cables to connect them in this case
  - Optional: A Qwiic cable to connect the SCD41 to the breakout headers
    - This negates the need to solder the wires to the SCD41

## Software

You will need to install the following libraries:

  - `umqtt.simple`
  - `ntptime`

## Wiring configuration

The LCD module I used was connected as follows:

  - BL = 13
  - DC = 8
  - RST = 12
  - MOSI = 11
  - SCK = 10
  - CS = 9

You can change these pins in the `LCDModule.py` file.

The SCD41 sensor was connected to the I2C pins on the Pico W via a Qwiic cable (connected to the breakout board).

## Configuration

In the `config.py` file, you will need to modify these values:
```
WIFI_SSID = "your_2.4_ghz_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
MQTT_SERVER = "123.456.789.000" # the IP address of your MQTT server
```

That file also contains the following:
```
MQTT_SCREEN_ON_TOPIC = "environment-monitor/state/screen-on"
MQTT_RESET_TOPIC = "environment-monitor/state/reset"
```

Further options may be added in future.

## Important note - LCD displays

Due to the limited memory of the Pico W when running Micropython, I strongly recommend using a display with a resolution of 240x240 or less.
This is because the framebuffer of a display takes up a significant amount of memory, and the Pico W will run out of memory if you use a larger display.
I tried to get this working with a 320x240 display, but there simply isn't enough memory to do so.

I tried to get this working on an ESP32, but unfortunately the micropython firmeware available for it provides even less memory than the Pico W. Additionally, there are some other weird issues with even getting the display working.

TLDR: Use a 240x240 display or smaller, and use a Pico W.

## MQTT

I recommend using eclipse-mosquitto as your MQTT server, as it's easy to set up and use and its reportedly one of the only MQTT servers that works with the implementation of MQTT we used here. That's not to say other options won't work, but I haven't tested them.

The MQTT server should be configured to listen on port 1883, and should not require authentication. In a future release, we might add support for authentication, but for now it's not supported. Feel free to adapt the code if you want to add it yourself (it should be a case of modifying the config and the `connect_mqtt()` function).

The default setup for the MQTT topics are as follows:

  - CO2: published to `environment-monitor/carbondioxide`
  - Temperature: published to `environment-monitor/temperature`
  - Humidity: published to `environment-monitor/humidity`
  - Last update: published to `environment-monitor/last_update`

The topics that the monitor listens to are:
  
  - `environment-monitor/state/screen-on`
    - If it receieves 'on', the screen will turn on
    - If it receieves 'off', the screen will turn off
    - You should send this message with the retain flag set, as this will cause the Pico W to use the existing settings between reset
  - `environment-monitor/state/reset`
    - If it receieves any message to this topic, it will reset the Pico W
    - IMPORTANT: You should **NOT** send this message with the retain flag set, as this will cause the Pico W to reset every time it connects to the MQTT server

Please note that during initialisation, the LCD display will be switched on. Once it has connected to the MQTT server, it will check for the `environment-monitor/state/screen-on` topic, and will turn the screen off if it receives a message with the value 'off'. Otherwise, it'll be on.

## Why did I make this?

In recent months, I've been moving all my IoT devices over to connect to a Home Assistant instance that's running on my network. I've found that cloud services are unreliable - if my internet is out, or there's an AWS outage, I found that I couldn't control my lights, blinds, or a whole bunch of other devices.

I was using a Netatmo environment monitor. In addition to the cloud-specific issues and concerns, I was frustrated that it only polled once every 5 minutes. I wanted something which would poll more frequently while still providing moderately good accuracy up to 5000 ppm. With that in mind, I decided to build my own. I also wanted to learn more about the Pico W, and this seemed like a good project to do so.

I went through a couple of code revisions, and had something that mostly worked, but it was also notoriously slow. I decided to pitch my idea to chatGPT. It managed to come up with some solid ideas, but ultimately I had to hand-hold through a lot of the process. I can't tell you how many times I had to tell it to not use `wifi.isConnected()` (a function which isn't available). It made some mistakes, and created some code which was quite buggy. We got real close to having 100% functionality a few times, but it always seemed to miss things. Sometimes it'd even delete code that I'd previously asked for!

Ultimately though, with some prodding, poking and prompting, we managed to get a working solution. I'd say it's around 50/50 - I did half the work by prompting it correctly, and it did the other 50% of creating code that's clean, functional and as efficient as could reasonably be expected.