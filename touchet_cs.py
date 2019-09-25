import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shapepositionpicker import shapepositionpicker


class TouchetCS(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that should become the slider.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, slider_shape, touchet_manager):
        shapepicker().pick(
            cls.prepare3,
            "Pick another shape that should become the referential.",
            slider_shape,
            touchet_manager
        )

    @classmethod
    def prepare3(cls, referential_shape, slider_shape, touchet_manager):
        if referential_shape == slider_shape:
            print("Error: You picked twice the same shape.")
            return
        shapepositionpicker().pick(
            slider_shape,
            cls.instantiate,
            "Move the slider to its zero position.",
            referential_shape,
            slider_shape,
            touchet_manager
        )

    @classmethod
    def instantiate(cls, pos_zero, referential_shape, slider_shape, touchet_manager):
        instance = cls([slider_shape, referential_shape], pos_zero)
        touchet_manager.add_touchet(instance)

    def __init__(self, shapes, pos_zero):
        assert len(shapes) == 2
        super().__init__(shapes)
        shapes[1].keypoints[self] = [pos_zero]  # Save as keypoints in referential shape

    def on_moved(self, _, data):
        self.__emit(data, True)

    def on_transformation_adjusted(self, _, data):
        self.__emit(data, False)

    def __emit(self, data, moved_by_finger):
        zero_vect = self.shapes[1].bbox.center_nparr() - self.shapes[1].keypoints[self][0]
        move_vect = self.shapes[0].bbox.center_nparr() - self.shapes[1].bbox.center_nparr()
        dot = np.dot(zero_vect, move_vect)
        det = zero_vect[0] * move_vect[1] - zero_vect[1] * move_vect[0]
        self.most_recent_angle = np.rad2deg(np.arctan2(det, dot)) + 180
        self.emit_touchet_event('moved', angle=self.most_recent_angle, moved_shape='slider' if data['shape'] == self.shapes[0] else 'referential', moved_by_finger=moved_by_finger)
