import os
import cv2

from conf import conf
from publisher import Publisher
from realsensecam import realsensecam
from shapedetector import shapedetector
from shapetracker import shapetracker
from shapetracker import shapetracker
from touchedshapetracker import touchedshapetracker
from handdetector import handdetector
from handtracker import handtracker
from visualizer import visualizer
from shapepicker import shapepicker
from shaperegionpicker import shaperegionpicker
from shapepositionpicker import shapepositionpicker
from ui import ui
from logger import Logger

__controller_instance = None


def controller(*init_params):
    global __controller_instance
    if __controller_instance is None:
        __controller_instance = Controller(*init_params)
    return __controller_instance


class Controller(Publisher):
    def __init__(self, logger=None):
        super().__init__()
        if conf()['compile_pyx_on_startup']:
            os.system("python setup.py build_ext --inplace")

        self.frame = 0
        self.logger = logger

        # Initialize all needed modules
        shapedetector()
        shapetracker()
        touchedshapetracker()
        handdetector()
        handtracker()
        visualizer()
        ui()
        shapepicker()
        shaperegionpicker()

        # Put the wires together
        handtracker().subscribe('hand_exit', shapetracker().clear_lost_shapes)
        handtracker().subscribe('finger_up', touchedshapetracker().on_finger_up)
        handtracker().subscribe('finger_pressing', ui().on_finger_pressing)
        handtracker().subscribe('finger_up', ui().on_finger_up)
        handtracker().subscribe('finger_down', ui().on_finger_down)
        handtracker().subscribe('finger_pressing', shapepicker().on_finger_pressing)
        handtracker().subscribe('finger_up', shapepicker().on_finger_up)
        handtracker().subscribe('hand_exit', handdetector().on_hand_exit)
        handtracker().subscribe('finger_pressing', shaperegionpicker().on_finger_pressing)
        handtracker().subscribe('finger_up', shaperegionpicker().on_finger_up)
        handtracker().subscribe('hand_exit', shaperegionpicker().on_hand_exit)
        handtracker().subscribe('hand_exit', shapepositionpicker().on_hand_exit)

    def next_frame(self):
        self.frame += 1
        self.publish('frame_begins', {'frame': self.frame})

        if not realsensecam().acquire_frames():
            return None

        handdetector().determine_hand_cnt()
        if handtracker().update() and not ui().menu_active:
            detected_shapes = shapedetector().detect_shapes()
            shapetracker().process_detected_shapes(detected_shapes)
            touchedshapetracker().update()
        if self.logger is not None:
            self.logger.logAll()
        return visualizer().visualize()

    def on_key(self, key):
        ui().on_key(key)
