# Diecast-Remote-Raceway
The Diecast Remote Raceway (DRR) allows participants to race 1:64 scale die-cast cars (such as the popular Hot Wheels® cars from 
[Mattel](https://www.mattel.com/en-us)), head-to-head, from remote locations.  A DRR consists of an automated Starting Gate, an electronic Finish Line, and a web service that coordinates races between multiple raceways via the internet.

The DRR is comprised of three components:

* The Starting Gate that manages races on a single track.  The Starting Gate houses a Raspberry Pi Zero W single board computer that performs all local race operations. Reflective infrared track sensors plug into the Starting Gate to signal the presence of a car positioned in each starting location.  A race begins when cars are present in all lanes.  The Starting Gate connects via Bluetoot to the Finish Line that reports when cars finish a race.
* The Finish Line houses an ESP32 Arduino dev board that reports when a car passes over a sensor in each lane.
* The Coordinator is a Node.js application that coordinates the actions of multiple tracks competing against each other.  Each track signals when all lanes have cars ready to race.  When all tracks are ready, the Coordinator signals all tracks to start the local race.  Tracks report the elapsed time for each lane back to the coordinator, which then computes the overall race standings and returns the results to each track to display the race results.

## Operation

Start by mounting the Starting Gate onto a suitable elevated surface. The mount on the bottom of
the Starting Gate can be attached to a [Hot Wheels Clamp
3-way](https://www.thingiverse.com/thing:4037458) to clamp onto a chair, desk, shelf or other
surface.  Alternatively, you can attach to a photography tripod using a [Hot Wheels Track Tripod Connector ](https://www.thingiverse.com/thing:4376073).

Next, attach track sections to build a track of your liking.  Terminate the track with the Finish
Line component.

Apply power to both the Starting Gate and Finish Line using 5 Volt sources
and mini-USB cables.  Most phone chargers or power packs work well to
provide power.  When the Starting Gate has completed its initialization,
the display should look like this:

![Top Menu](images/Top-Menu.png)

* To race locally, push the top button next to "Single Track"
* To race against another track, push the middle button next to "Multi Track"
* To set configuration parameters such as selecting car icons, other tracks to race against, tack timeout or WiFi parameters, push the button next to "Configure"

Once a race mode has been selected (Single Track or Multi Track) the
Starting Gate will establish a Bluetooth connection to the Finish Line.
This may take a minute or more to complete, during which time the
following is displayed:

![Connecting](images/Connecting.png)

### Multi-Track Race

In a multi-track race was selected, the Starting Gate contacts the race controller to await
another participating track.  The following is displayed:

![Wait Remote Track](images/Wait-Remote-Track.png)

Upon return, the name of the remote track is displayed
and the Starting Gate awaits cars in each starting gate.

![Waiting Cars 2](images/Waiting-Cars-2-Empty.png)

When a lane's sensor detects that a car has been placed in a lane, the "no
car" icon is replaced with the user's selected icon for that lane:

![Waiting Cars 2](images/Waiting-Cars-2.png)

Once cars are present in all lanes of the local track the Starting Gate
contacts the race coordinator to signal that the track is ready to race and wait until the
remote track is also ready:

![Waiting on Other Track](images/Waiting-Other.png)

Once both tracks are ready, there is a 3 second countdown and the
race begins.  The elapsed time is displayed as the race progresses,
and the icons travel down the image of the track.

![Racing](images/Racing.png)

Finally, when all cars have finished (or the configured timeout is reached) the results of the
race are displayed:

![Results](images/Results.png)

and the starting gate barrier is raised to accept cars again.

To start next race, simply placing cars in the gates.  When the first car is placed, the
display clears the race results and goes back to the "Waiting for cars" state and the next race
proceeds.

### Single-Track Race

A Single Track race proceedes much like a Mulit Track but without the coordination with the
second track.  As soon as the connection to the Finish Line is established, the Starting Gate
waits for cars on the local track.

![Waiting for Cars](images/Waiting-for-Cars.png)

When a lane's sensor detects that a car has been placed in a lane, the "no
car" icon is replaced with the user's selected icon for that lane:

![Waiting with 1 Car](images/Waiting-Cars-1.png)

Once all cars are present, there is a 3 second countdown and the race begins.

![Racing 1 Track](images/Racing-1-Track.png)

When the race completes, the results are displayed:

![Racing 1 Track](images/Results-1-Track.png)

and the starting gate barrier is raised to accept cars again.

To start next race, simply placing cars in the gates.  When the first car is placed, the
display clears the race results and goes back to the "Waiting for cars" state and the next race
proceeds.
