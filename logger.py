import cv2
import yaml

from handdetector import handdetector
from handtracker import handtracker
from shapetracker import shapetracker


class Logger:
    def __init__(self):
        self.log = []

    def logAll(self):
        l = {'fingertip': {'x': -1, 'y': -1}, 'fingerdown': False, 'shape': []}
        if handdetector().hand_cnt is not None and handdetector().hand_valid:
            l['fingertip'] = {'x': int(handdetector().fingertip_pos[0]), 'y': int(handdetector().fingertip_pos[1])}
        if handtracker().finger_down:
            l['fingerdown'] = True
        if len(shapetracker().shapes) > 0:
            cnt = next(iter(shapetracker().shapes.values())).cnt
            eps = .1 * cv2.arcLength(cnt, True)
            approxPts = cv2.approxPolyDP(cnt, eps, True)[:, 0]
            for pos in approxPts:
                l['shape'].append({'x': int(pos[0]), 'y': int(pos[1])})
        self.log.append(l)

    def dump(self, filename):
        with open(filename, 'w') as f:
            yaml.dump(self.log, f)
        print("Dumped log to {}".format(filename))
