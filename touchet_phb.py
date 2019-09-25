import numpy as np
import time

from touchet import Touchet
from shapepicker import shapepicker
from shaperegionpicker import shaperegionpicker


class TouchetPHB(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape to become a your new pos. hold button.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, picked_shape, touchet_manager):
        shaperegionpicker().pick(
            picked_shape,
            cls.instantiate,
            touchet_manager,
            picked_shape
        )

    @classmethod
    def instantiate(cls, picked_regions, touchet_manager, picked_shape):
        if len(picked_regions) < 1:
            print("Error: PHB Touchet needs at least one region")
            return
        new_touchet = cls([picked_shape])
        picked_shape.keypoints[new_touchet] = picked_regions
        touchet_manager.add_touchet(new_touchet)

    def __init__(self, shapes):
        super().__init__(shapes)
        self.down = False
        self.pressed_region = -1
        self.down_on = 0
        self.reported_long_press = False

    def on_finger_down(self, _, data):
        # Find out which region was touched
        kps = np.array(self.shapes[0].keypoints[self])
        pt = data['fingertip_pos']
        self.pressed_region = np.linalg.norm(kps - pt, axis=1).argmin()
        self.down = True
        self.down_on = time.time()
        self.emit_touchet_event('pressed', region=self.pressed_region)

    def on_finger_pressing(self, *_):
        if not self.reported_long_press and time.time() - self.down_on >= 0.5:
            self.reported_long_press = True
            self.emit_touchet_event('pressed_long', region=self.pressed_region)

    def on_finger_up(self, _, data):
        self.down = False
        duration = time.time() - self.down_on
        self.emit_touchet_event('released', duration=duration, region=self.pressed_region)
        self.reported_long_press = False
        if duration < 0.5:
            self.emit_touchet_event('pressed_short', region=self.pressed_region)
        self.pressed_region = -1
