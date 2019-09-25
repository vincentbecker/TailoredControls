import time
import cv2

from shapetracker import shapetracker
from bbox import Bbox


__shaperegionpicker_instance = None


def shaperegionpicker(*init_params):
    global __shaperegionpicker_instance
    if __shaperegionpicker_instance is None:
        __shaperegionpicker_instance = ShapeRegionPicker(*init_params)
    return __shaperegionpicker_instance


class ShapeRegionPicker:
    def __init__(self):
        self.active = False
        self.callback = None
        self.args = []
        self.stable_since = 0
        self.shape = None

    # Initiate picking procedure. After picking,
    # the callback will be called with the selected
    # shape and the given args
    def pick(self, shape, callback, *args):
        self.active = True
        self.callback = callback
        self.args = args
        self.shape = shape
        self.current_point = None
        self.picked_regions = []
        self.must_lift_finger = True
        self.descriptions = None
        self.amount_target_regions = 0

    def pick_n(self, descriptions, shape, callback, *args):
        self.active = True
        self.callback = callback
        self.args = args
        self.shape = shape
        self.current_point = None
        self.picked_regions = []
        self.must_lift_finger = True
        self.descriptions = descriptions
        self.amount_target_regions = len(descriptions)

    def on_finger_pressing(self, _, data):
        if not self.active or self.must_lift_finger:
            return

        xy = data['fingertip_pos']
        if not self.shape.bbox.contains(*xy):
            self.current_point = None
            return

        if self.current_point is None:
            self.current_point = xy
            self.stable_since = time.time()
        else:
            tolerance_bbox = Bbox(*xy, 0, 0)
            tolerance_bbox.extend_by(15)
            if not tolerance_bbox.contains(*self.current_point):
                self.stable_since = time.time()
                self.current_point = xy

        if time.time() - self.stable_since >= 1:
            self.picked_regions.append(self.current_point)
            self.current_point = None
            self.must_lift_finger = True
            if self.amount_target_regions > 0 and len(self.picked_regions) >= self.amount_target_regions:
                self.on_hand_exit()  # Simulate hand exit in order to terminate the regions
            return

    def on_finger_up(self, *_):
        self.current_point = None
        self.must_lift_finger = False

    def on_hand_exit(self, *_):
        if not self.active:
            return

        self.active = False
        self.shape = None
        self.callback(self.picked_regions, *self.args)  # Picking completed, call the callback
        self.callback = None
        self.args = []
        self.picked_regions = []

    def progress(self):
        if self.current_point is None:
            return 0
        return min(1, time.time() - self.stable_since)

    def current_region_description(self):
        if self.descriptions is None:
            return "an area"
        return self.descriptions[len(self.picked_regions)]
