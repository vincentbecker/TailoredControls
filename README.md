# TailoredControls
The code for the paper "Tailored Controls: Creating Personalized Tangible User Interfaces from Paper" presented at ISS'19.

TailoredControls is a framework for tracking paper shapes lying on a table and interactions performed on them by a finger.

## Physical setup

Mount an Intel RealSense camera (we tested with a D435) about 40cm above a flat surface such as a table. The surface must be uncolored, i.e. white or gray. The camera must be facing towards the surface. The camera must not move.

## Installation

### Dependencies

First, install the drivers for the RealSense camera, as well as Python 3. The following modules should be installed using pip:
`certifi`
`chardet`
`cycler`
`Cython`
`idna`
`kiwisolver`
`matplotlib`
`numpy`
`opencv-contrib-python`
`opencv-python`
`pyparsing`
`pyrealsense2`
`python-dateutil`
`PyYAML`
`requests`
`scikit-learn`
`scipy`
`six`
`urllib3`

### Precompiling the cython modules

Compile the `transformations` and the `icp` modules with the following command: `python setup.py build_ext --inplace`

### Providing a client

TailoredControls connects to a client using two sinks specified in `config.yaml`:

1. `actions_url`: TailoredControls performs a HTTP GET request on this URL and expects a 200 reply consisting of JSON list of strings which will be displayed in the actions menu (green square).
2. `event_sink_url`: When events are detected, TailoredControls sends JSON objects through a HTTP GET request to this URL and expects an empty 200 reply.

### Running DynamicUIs

Simply call `python run.py`.

## Example with Node-RED
One option to use  TailoredControls is to connect it to a Node-RED flow to further process the events and propagate the events to applications. In this example we simply output the events in a Node-RED debugger. First, install Node-RED locally as explained [here](https://nodered.org/docs/getting-started/local). Then start a Node-RED server using `node-red-start`. Open the indicated HTTP-address. Imported the following flow:

`[{"id":"77cbf8f4.842fd","type":"tab","label":"Flow 1","disabled":false,"info":""},{"id":"6036060d.1709f8","type":"http in","z":"77cbf8f4.842fd","name":"","url":"/touchets","method":"get","upload":false,"swaggerDoc":"","x":190,"y":380,"wires":[["8b26b50a.6bdcf8","28e91902.6c12a6"]],"info":"/touchets"},{"id":"2aaad64d.dd2bb2","type":"http in","z":"77cbf8f4.842fd","name":"","url":"/actions","method":"get","upload":false,"swaggerDoc":"","x":210,"y":660,"wires":[["2d3d63bd.ee3534"]]},{"id":"96667f7b.531fd8","type":"http response","z":"77cbf8f4.842fd","name":"","statusCode":"200","headers":{},"x":600,"y":660,"wires":[]},{"id":"2d3d63bd.ee3534","type":"template","z":"77cbf8f4.842fd","name":"","field":"payload","fieldType":"msg","format":"handlebars","syntax":"mustache","template":"[\"Lamp\"]","output":"str","x":420,"y":660,"wires":[["96667f7b.531fd8","978ce8f5.14898"]]},{"id":"978ce8f5.14898","type":"debug","z":"77cbf8f4.842fd","name":"","active":true,"tosidebar":true,"console":false,"tostatus":false,"complete":"false","x":600,"y":720,"wires":[]},{"id":"8b26b50a.6bdcf8","type":"function","z":"77cbf8f4.842fd","name":"Action filter","func":"if (msg.payload.hasOwnProperty(\"action\")) {\n    return msg;\n} else {\n    return null;\n}","outputs":1,"noerr":0,"x":410,"y":380,"wires":[["8a032f8b.d71e9"]]},{"id":"28e91902.6c12a6","type":"http response","z":"77cbf8f4.842fd","name":"","statusCode":"200","headers":{},"x":330,"y":280,"wires":[]},{"id":"eaf6de4f.118828","type":"debug","z":"77cbf8f4.842fd","name":"","active":true,"tosidebar":true,"console":false,"tostatus":false,"complete":"false","x":770,"y":380,"wires":[]},{"id":"8a032f8b.d71e9","type":"function","z":"77cbf8f4.842fd","name":"Event filter","func":"if (msg.payload.event == \"pressed\") {\n    return msg;\n} else {\n    return null;\n}","outputs":1,"noerr":0,"x":590,"y":380,"wires":[["eaf6de4f.118828"]]}]`

The flow should look like this:
![Node-RED flow](/images/node-red.png)
It consists of two parts. The lower one simply returns a JSON array of strings to TailoredControls containing the available actions upon a GET-request (here we simply use `Lamp`, imagine we were building an application to contorl a smart lamp). 

The one above contains the application logic. We first filter for events which have an action attribute in order to exclude all the other events which are generated when the hand is moved or the surface is touched. We then only forward events which are `pressed`-events, i.e. results from the Button touchet. Now run TailoredControls as explained above, add a paper snippet and add the `Lamp` action and the Button touchet to it (you can add more touchets but they will be filtered out in the flow). When touching the paper snippet you should see the event information in Node-RED's debug view. 
