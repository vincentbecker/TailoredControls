import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shapepositionpicker import shapepositionpicker


class TouchetT(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that should become the trackbar.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, slider_shape, touchet_manager):
        shapepicker().pick(
            cls.prepare3,
            "Pick another shape to become the lower referential.",
            slider_shape,
            touchet_manager
        )

    @classmethod
    def prepare3(cls, loref_shape, slider_shape, touchet_manager):
        if loref_shape == slider_shape:
            print("Error: You picked twice the same shape.")
            return
        shapepicker().pick(
            cls.instantiate,
            "Pick another shape to become the upper referential.",
            loref_shape,
            slider_shape,
            touchet_manager
        )

    @classmethod
    def instantiate(cls, hiref_shape, loref_shape, slider_shape, touchet_manager):
        if hiref_shape == slider_shape or loref_shape == hiref_shape:
            print("Error: You picked twice the same shape.")
            return
        instance = cls([slider_shape, loref_shape, hiref_shape])
        touchet_manager.add_touchet(instance)

    def __init__(self, shapes):
        assert len(shapes) == 3
        super().__init__(shapes)

    def on_moved(self, _, data):
        self.__emit(data, True)

    def on_transformation_adjusted(self, _, data):
        self.__emit(data, False)

    def __emit(self, data, moved_by_finger):
        pos = self.shapes[0].bbox.center_nparr()
        radius_slider = max(self.shapes[0].bbox.size()) / 2
        pos_low = self.shapes[1].bbox.center_nparr()
        radius_low = max(self.shapes[1].bbox.size()) / 2
        pos_high = self.shapes[2].bbox.center_nparr()
        radius_high = max(self.shapes[2].bbox.size()) / 2
        dist_low = np.linalg.norm(pos_low - pos) - radius_low - radius_slider - 5
        dist_high = np.linalg.norm(pos_high - pos) - radius_high - radius_slider - 5
        dist_total = np.linalg.norm(pos_high - pos_low) - radius_low - radius_high - radius_slider - 10
        value = min(1, max(0, (dist_low - dist_high) / dist_total / 2 + .5))
        self.emit_touchet_event('moved', value=value, moved_shape=dict(zip(self.shapes, ['slider', 'referential_low', 'referential_high']))[data['shape']], moved_by_finger=moved_by_finger)
