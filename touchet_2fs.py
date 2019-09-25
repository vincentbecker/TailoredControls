import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shaperegionpicker import shaperegionpicker


class Touchet2FS(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that becomes the new 2D finger slider.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, picked_shape, touchet_manager):
        shaperegionpicker().pick_n(
            ['lower vertical ref.', 'upper vertical ref.', 'lower horizontal ref.', 'upper horizontal ref.'],
            picked_shape,
            cls.instantiate,
            touchet_manager,
            picked_shape
        )

    @classmethod
    def instantiate(cls, picked_regions, touchet_manager, picked_shape):
        if len(picked_regions) != 4:
            print("Error: You must pick exactly 4 regions")
            return
        new_touchet = cls([picked_shape])
        picked_shape.keypoints[new_touchet] = picked_regions
        picked_shape.keypoints_on_down[new_touchet] = picked_regions  # Finger is already down
        touchet_manager.add_touchet(new_touchet)

    def __init__(self, shapes):
        super().__init__(shapes)
        self.value_y = 0
        self.value_y_on_down = -1
        self.value_x = 0
        self.value_x_on_down = -1

    def on_finger_moved(self, _, data):
        # Vertical
        pos = np.array(data['fingertip_pos'])
        pos_low = self.shapes[0].keypoints[self][0]
        pos_high = self.shapes[0].keypoints[self][1]
        dist_low = np.linalg.norm(pos_low - pos)
        dist_high = np.linalg.norm(pos_high - pos)
        dist_total = np.linalg.norm(pos_high - pos_low)
        self.value_y = max(0, min(1, (dist_low - dist_high) / dist_total / 2 + .5))

        # Horizontal
        pos = np.array(data['fingertip_pos'])
        pos_low = self.shapes[0].keypoints[self][2]
        pos_high = self.shapes[0].keypoints[self][3]
        dist_low = np.linalg.norm(pos_low - pos)
        dist_high = np.linalg.norm(pos_high - pos)
        dist_total = np.linalg.norm(pos_high - pos_low)
        self.value_x = max(0, min(1, (dist_low - dist_high) / dist_total / 2 + .5))

        if self.value_y_on_down < 0:
            self.value_y_on_down = self.value_y

        if self.value_x_on_down < 0:
            self.value_x_on_down = self.value_x

        self.emit_touchet_event('moved', value_x=self.value_x, value_y=self.value_y)

    def on_finger_up(self, _, data):
        self.emit_touchet_event('finger_up',
                                value_x=self.value_x,
                                value_y=self.value_y,
                                value_x_difference=self.value_x - self.value_x_on_down,
                                value_y_difference=self.value_y - self.value_y_on_down)
        self.value_y_on_down = -1
        self.value_x_on_down = -1
