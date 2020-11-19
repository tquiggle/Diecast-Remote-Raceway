# Diecast Remote Raceway - Finish Line

This folder contains the 3D models, software and instructions for the
Finish Line component of the Diecast Remote Raceway.

## 3D Printed Components

### Finish Lanes

The Finish Lane design is derived from the Starting Box design by 
[capsurfer](https://www.thingiverse.com/capsurfer/about) on 
[Thingiverse](https://www.thingiverse.com/thing:4026846).  His sketch for
the profile of the track was re-used as the basis for the profile
for the finish line.  The cut-outs for the track connectors are similarly
based on capsurfer's sketches in his original Fusion360 design.  All other
aspects are my own creation.


* Controller-Box.stl - Box to house the ESP32 development board and Infrared Tracking Sensor Module
* Controller-Lid.stl - Solid lid to Controller-Box
* Controller-Lid-Adjust.stl - Controller-Box lid with viewing window and access holes for adjusting sensitivity
* Track-1.stl - Finish line for lane 1
* Track-2.stl - Finish line for lane 2
* Track-3.stl - Finish line for lane 3
* Track-4.stl - Finish line for lane 4
* Track-Bottom-Cover.stl - Snap-on cover for wiring on lane

#### License

Since I started with a sketch from capsurfer's Starter Box, the Starting Gate components are released under 
the same [Creative Commons Attribution - NonCommercial - ShareAlike](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.

## Hardware

![ESP32 devkit](../images/ESP32-pinout-mapping.png)

The wiring to connect the ESP32 dev board to the YWBL-WH Infrared Tracking Sensor Module is shown below:

![Finish Line Wiring](../images/FinishLine-Wiring.png)

I used a 6 pin Dupont connector for the YWBL-WH header and two right angle crimp-on connectors to connect to
the ESP32. The ribbon cable was split to accomodate two right angle connectors: a two pin connector for Vcc and
GND, and a *5 pin* connector to connect the four lane sensors to GPIO16 through GPIO19.  Note that the middle
pin of the 5 pin connector that would connect to GPIO05 is not connected.

### Lane Sensitivity Adjustment
The Starting Gate and Finish Line detect cars by infrared light reflected off the bottom of the car.  As such,
they are sensitive to ambient infrared light striking the sensor.  If the sensors are exposed to high levels of
ambient infrared lighting, such as in direct sunlight, they may report a car when none is present.  The
sensitivity of each Finish Line can be adjusted.

![Finish Line](../images/FinishLine.png)

The LED labeled “D5” is a power indicator.  It will illuminate whenever power is applied to the Finish Line.

Adjustments are made with a small screwdriver using the four trim potentiometers labeled “Lane 1” through
“Lane4” in the above photo.  When correctly adjusted, the lane indicator LED will be unlit when no car is
present in a lane and will light up when a car is placed over the sensor.  To adjust, make sure the Finish Line
is plugged into a 5V power source.  Start with no car present.  Turn the white potentiometer corresponding to
the lane until the indicator lights up.  Then turn back just past the point where the light turns off.  Test the
lane by placing a car over the sensor.  The corresponding indicator should illuminate.

