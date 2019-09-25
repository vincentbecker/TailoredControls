import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shaperegionpicker import shaperegionpicker


class TouchetSB(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that becomes the new swipe button.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, picked_shape, touchet_manager):
        shaperegionpicker().pick_n(
            ['upper edge'],
            picked_shape,
            cls.instantiate,
            touchet_manager,
            picked_shape
        )

    @classmethod
    def instantiate(cls, picked_regions, touchet_manager, picked_shape):
        if len(picked_regions) != 1:
            print("Error: You must pick exactly 1 region")
            return
        new_touchet = cls([picked_shape])
        picked_shape.keypoints[new_touchet] = picked_regions
        picked_shape.keypoints_on_down[new_touchet] = picked_regions  # Finger is already down
        touchet_manager.add_touchet(new_touchet)

    def __init__(self, shapes):
        super().__init__(shapes)
        self.most_recent_angle = 0
        self.most_recent_dist = 0

    def on_swiped(self, _, data):
        zero_vect = self.shapes[0].keypoints[self][0] - self.shapes[0].bbox.center_nparr()
        swipe_vect = data['shape_swipe_delta']
        dist = np.linalg.norm(swipe_vect)
        if dist < 0.5:
            return
        dot = np.dot(zero_vect, swipe_vect)
        det = zero_vect[0] * swipe_vect[1] - zero_vect[1] * swipe_vect[0]
        self.most_recent_angle = np.rad2deg(np.arctan2(det, dot))
        self.emit_touchet_event('swiping', angle=self.most_recent_angle, distance=dist)
        self.most_recent_dist = dist

    def on_finger_up(self, _, data):
        if 'shape_swipe_delta' in data:
            self.on_swiped(None, data)
        self.emit_touchet_event('swiped', angle=self.most_recent_angle)

        if self.most_recent_dist > 10:
            if -135 <= self.most_recent_angle < -45:
                self.emit_touchet_event('swiped_left')
            elif -45 <= self.most_recent_angle < 45:
                self.emit_touchet_event('swiped_up')
            elif 45 <= self.most_recent_angle < 135:
                self.emit_touchet_event('swiped_right')
            else:
                self.emit_touchet_event('swiped_down')
