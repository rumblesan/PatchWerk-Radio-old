---
layout: page
title: "How does it work"
---
{% include JB/setup %}

## How does it work

The following is a brief rundown of the internals and gives an explanation of what’s going on, in an attempt to answer:

* How does PatchWerk Radio work?
* What is it doing?
* How do the loaded patches interact with the main program and how are they controlled?

Here is a diagram showing roughly what’s involved:

<div class="wp-caption aligncenter" style="width: 600px">
<a href="/images/program-diagram.png">
<img src="/images/program-diagram.png" alt="Program Diagram" />
</a>
<p class="wp-caption-text">PatchWerk Radio Program Diagram</p>
</div>

The Python script is the brains of the whole thing, it:

* Gets Pure Data (PD) to load the master control patch ‘masterPatch’.
* Sends PD all the streaming settings.
* Chooses which patches it will load and fades between them.

All of this is done over a network connection between PD and Python using a slightly modified version of the [PyPD](http://mccormick.cx/projects/PyPd/) class written by Chris McCormick.

### Master Patch

The masterPatch is a PD patch that deals with the cross-fading, the streaming, the dynamic patch loading and the routing of messages between these sections.
It has a number of sub sections, each of which handle these different tasks.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/master-patch.png">
<img src="/images/master-patch.png" alt="The Master Patch" />
</a>
<p class="wp-caption-text">Master Patch</p>
</div>

### Python Interface

The python-interface sub-patch deals with the network communications between the patch and Python.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/python-interface.png">
<img src="/images/python-interface.png" alt="Python Interface" />
</a>
<p class="wp-caption-text">Python Interface</p>
</div>

### Volume Control

The volume-control sub-patch just does the cross fading between the audio of the loaded patches.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/volume-control.png">
<img src="/images/volume-control.png" alt="Volume Control" />
</a>
<p class="wp-caption-text">Volume Control</p>
</div>

### Patch Control

The patch-control section is responsible for loading and closing the chosen patches using the dynamic messaging properties of PD.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/patch-control.png">
<img src="/images/patch-control.png" alt="Patch Control" />
</a>
<p class="wp-caption-text">Patch Control</p>
</div>

### Patch Interface

The patch-interfaces are the important sub-sections. This is where the audio from the dynamically loaded patches comes into the master patch and then gets routed to the streaming section. It contains two receive~ objects for left and right channels and the logic to change where these will get their data from. It’s also where the messages to the loaded patches from the master patch are routed through.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/patch-interface.png">
<img src="/images/patch-interface.png" alt="Patch Interface" />
</a>
<p class="wp-caption-text">Patch Interface</p>
</div>

### Streaming

The streaming sub-patch contains the oggcast~ object and all the routing to get the settings messages from python and format them correctly.
The audio from the loaded patches is routed to here, from where it is streamed to the internet at large.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/streaming.png">
<img src="/images/streaming.png" alt="Streaming" />
</a>
<p class="wp-caption-text">Streaming</p>
</div>

### Loaded Patches

The audio-patches themselves are treated by PD exactly as if the patch were opened from the file menu.
This is good because it means that messages and audio data can easily be sent between it and the master, without having to do any external routing. The drawback is that we don’t have objects we can connect using patch cords, nor can we just give it a pre-defined set of send~ objects at the output, because that would make cross-fading between patches a bit tricker.

As well as that, we have to be careful with how we name objects such as send and receives, in case patches interfere with one another.
My solution to this was to use ‘$0’ as a creation argument for each object that needed to be unique in each patch and/or sub-patch of an abstraction. Then for each object made from an abstraction, the creation argument is replaced with a number unique to each instance of that abstraction. You can read more on this subject [here](http://puredata.hurleur.com/sujet-5853-abstraction-why-use-etc).

In each of the loadable audio-patches there is an abstraction called patchComs. Sound output from the patch is routed into this, where inside it is connected to two send objects named $0-l and $0-r.
There are also objects for sending the ‘patch register’ message, as well as routing for the debug and DSP control messages.
In every patch there is a switch~ object hanging off that outlet.

<div class="wp-caption aligncenter" style="width: 585px">
<a href="/images/patchComs.png">
<img src="/images/patchComs.png" alt="patchComs Abstraction" />
</a>
<p class="wp-caption-text">patchComs Abstraction</p>
</div>

When the patch is loaded the unique $0 argument gets sent, via the masterCom send object, to the python-interface in the master patch, which sends it on to python.
After it loads each new patch, python waits for this message and when it receives it, registers that this is the unique id number for the patch.
It will then send a registration message back to the master patch, which will update one pair of receive~ objects in a patch-interface to start getting their audio from the new send~ objects. A similar thing is done with the message sending objects.

Initially DSP processing within the patch is turned off by the switch~ object.
This is done to reduce any spikes in CPU that might cause audio glitches when the patch is first loaded.
Once the patch is fully loaded and registered, python sends a ‘dsp on’ message to the patch, which turns on the switch~ object and starts DSP processing within the patch.

Once the patch is making noise, Python gets the master patch to fade over to the new output channel, waits until this is done, then it closes the old patch.
There are a few other housekeeping things done here such as turning off the DSP in the old patch and changing the receive~ objects to get their input from the dummy sends~.
Once this is done it will sleep for ten minutes until it needs to choose the next patch to load. There are a few checks in place to make sure the same patch isn’t loaded and that patches register themselves properly, but really everything is pretty simple.

This process keeps going for as long as the station is up. At the time of writing this I’ve found that it can happily run for upwards of three weeks without any problems but there are still a few bugs which mean that it infrequently crashes.

If you want to understand it a bit more, have a look at the code yourself and email me if you need to.

