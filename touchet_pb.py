import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shaperegionpicker import shaperegionpicker


class TouchetPB(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that should be your new pos. button.",
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
            print("Error: PB Touchet needs at least one region")
            return
        new_touchet = cls([picked_shape])
        picked_shape.keypoints[new_touchet] = picked_regions
        touchet_manager.add_touchet(new_touchet)

    def __init__(self, shapes):
        super().__init__(shapes)
        self.down = False
        self.pressed_region = -1

    def on_finger_down(self, _, data):
        # Find out which region was touched
        kps = np.array(self.shapes[0].keypoints[self])
        pt = data['fingertip_pos']
        self.pressed_region = np.linalg.norm(kps - pt, axis=1).argmin()
        self.down = True
        self.emit_touchet_event('pressed', region=self.pressed_region)

    def on_finger_up(self, _, data):
        self.down = False
        self.pressed_region = -1
