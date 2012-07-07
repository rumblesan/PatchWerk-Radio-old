---
layout: page
title: "Index"
description: ""
---
{% include JB/setup %}

## Creating Patches

There are a few things that need to be noted before making a patch for PatchWerk Radio. Because the patches are loaded under the same instance of PD, it is possible that they could interfere with each other. The following are a few simple guidelines that you need to follow if you want to make a well behaved radio patch.

* When the Python script is choosing the next patch to load it will pick a random folder from it's given patch directory. Once it has a folder it will check inside this folder for a patch named main-*.pd and then load this if it finds it. If it doesn't find it then it will try again so make sure the patch you want loaded follows this naming convention.
* Because of the way that the close message in PD works, each main patch must have a unique name. Currently I'm just naming everything with incrementing numbers in folder names and main patch names and that should be fine for the moment.
* Patches need to be totally stand-alone. They need to start on their own and play on their own. In the future I hope to add the ability for information (weather, stock prices, music scales etc) to be requested from the master patch but for the moment your patch has to do everything by itself.
* Patches play for about ten minutes so bear this in mind. Again, in future I hope to have this be specifiable on a per patch basis bit it's not here yet.
* Objects such as sends, receives, delay chains, tables and buffers need to use $0 arguments to make sure they're unique. Otherwise there might be inter patch interference.
* Try to avoid objects such as declare that modify the path. I still need to investigate how this works with the way PatchWerk Radio is setup.
* The only other thing to do is to make sure the audio output of your patch all goes into the patchComs object and you have that switch~ hanging off it. There is a test patchComs object in the repository that simulates starting up and fading in. If you use that when you’re building the patch then everything should work fine.

I still want to do work on the basic infrastructure of the system but that shouldn't affect the design of the patches. For those who are interested in getting involved, I'll point your towards the patch repository on GitHub. You can either fork it on there and then send me pull requests, or get in contact with me and send me the patches so I can put them in.

Have a look at some of the patches in there to see how everything works but if you still have questions then by all means email me.
