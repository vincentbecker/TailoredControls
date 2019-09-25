import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shapepositionpicker import shapepositionpicker


class TouchetS(Touchet):

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
            cls.prepare4,
            "Move the slider to its lowest position.",
            referential_shape,
            slider_shape,
            touchet_manager
        )

    @classmethod
    def prepare4(cls, pos_low, referential_shape, slider_shape, touchet_manager):
        shapepositionpicker().pick(
            slider_shape,
            cls.instantiate,
            "Move the slider to its highest position.",
            pos_low,
            referential_shape,
            slider_shape,
            touchet_manager
        )

    @classmethod
    def instantiate(cls, pos_high, pos_low, referential_shape, slider_shape, touchet_manager):
        instance = cls([slider_shape, referential_shape], pos_low, pos_high)
        touchet_manager.add_touchet(instance)

    def __init__(self, shapes, pos_low, pos_high):
        assert len(shapes) == 2
        super().__init__(shapes)
        shapes[1].keypoints[self] = [pos_low, pos_high]  # Save as keypoints in referential shape

    def on_moved(self, _, data):
        self.__emit(data, True)

    def on_transformation_adjusted(self, _, data):
        self.__emit(data, False)

    def __emit(self, data, moved_by_finger):
        pos = self.shapes[0].bbox.center_nparr()
        pos_low = self.shapes[1].keypoints[self][0]
        pos_high = self.shapes[1].keypoints[self][1]
        dist_low = np.linalg.norm(pos_low - pos)
        dist_high = np.linalg.norm(pos_high - pos)
        dist_total = np.linalg.norm(pos_high - pos_low)
        value = (dist_low - dist_high) / dist_total / 2 + .5
        self.emit_touchet_event('moved', value=value, moved_shape='slider' if data['shape'] == self.shapes[0] else 'referential', moved_by_finger=moved_by_finger)
