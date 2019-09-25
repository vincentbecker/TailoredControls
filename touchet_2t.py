import numpy as np

from touchet import Touchet
from shapepicker import shapepicker
from shapepositionpicker import shapepositionpicker


class Touchet2T(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.prepare2,
            "Pick a shape that should become the 2D trackbar.",
            touchet_manager
        )

    @classmethod
    def prepare2(cls, slider_shape, touchet_manager):
        shapepicker().pick(
            cls.prepare3,
            "Pick another shape to become the vertical lower ref.",
            slider_shape,
            touchet_manager
        )

    @classmethod
    def prepare3(cls, v_loref_shape, slider_shape, touchet_manager):
        if v_loref_shape == slider_shape:
            print("Error: You picked twice the same shape.")
            return
        shapepicker().pick(
            cls.prepare4,
            "Pick another shape to become the vertical upper ref.",
            [v_loref_shape, slider_shape],
            touchet_manager
        )

    @classmethod
    def prepare4(cls, v_hiref_shape, other_shapes, touchet_manager):
        other_shapes = [v_hiref_shape] + other_shapes
        if len(set(other_shapes)) < len(other_shapes):
            print("Error: You picked twice the same shape.")
            return
        shapepicker().pick(
            cls.prepare5,
            "Pick another shape to become the horizontal lower ref.",
            other_shapes,
            touchet_manager
        )

    @classmethod
    def prepare5(cls, h_loref_shape, other_shapes, touchet_manager):
        other_shapes = [h_loref_shape] + other_shapes
        if len(set(other_shapes)) < len(other_shapes):
            print("Error: You picked twice the same shape.")
            return
        shapepicker().pick(
            cls.instantiate,
            "Pick another shape to become the horizontal upper ref.",
            other_shapes,
            touchet_manager
        )

    @classmethod
    def instantiate(cls, h_hiref_shape, other_shapes, touchet_manager):
        all_shapes = [h_hiref_shape] + other_shapes
        if len(set(all_shapes)) < len(all_shapes):
            print("Error: You picked twice the same shape.")
            return
        instance = cls(list(reversed(all_shapes)))
        touchet_manager.add_touchet(instance)

    def __init__(self, shapes):
        assert len(shapes) == 5
        super().__init__(shapes)

    def on_moved(self, _, data):
        self.__emit(data, True)

    def on_transformation_adjusted(self, _, data):
        self.__emit(data, False)

    def __emit(self, data, moved_by_finger):
        # Horizontal
        pos = self.shapes[0].bbox.center_nparr()
        radius_slider = max(self.shapes[0].bbox.size()) / 2
        pos_low = self.shapes[3].bbox.center_nparr()
        radius_low = max(self.shapes[3].bbox.size()) / 2
        pos_high = self.shapes[4].bbox.center_nparr()
        radius_high = max(self.shapes[4].bbox.size()) / 2
        dist_low = np.linalg.norm(pos_low - pos) - radius_low - radius_slider - 5
        dist_high = np.linalg.norm(pos_high - pos) - radius_high - radius_slider - 5
        dist_total = np.linalg.norm(pos_high - pos_low) - radius_low - radius_high - radius_slider - 10
        value_x = min(1, max(0, (dist_low - dist_high) / dist_total / 2 + .5))

        # Vertical
        pos = self.shapes[0].bbox.center_nparr()
        radius_slider = max(self.shapes[0].bbox.size()) / 2
        pos_low = self.shapes[1].bbox.center_nparr()
        radius_low = max(self.shapes[1].bbox.size()) / 2
        pos_high = self.shapes[2].bbox.center_nparr()
        radius_high = max(self.shapes[2].bbox.size()) / 2
        dist_low = np.linalg.norm(pos_low - pos) - radius_low - radius_slider - 5
        dist_high = np.linalg.norm(pos_high - pos) - radius_high - radius_slider - 5
        dist_total = np.linalg.norm(pos_high - pos_low) - radius_low - radius_high - radius_slider - 10
        value_y = min(1, max(0, (dist_low - dist_high) / dist_total / 2 + .5))
        self.emit_touchet_event('moved',
                                value_x=value_x,
                                value_y=value_y,
                                moved_shape=dict(zip(
                                    self.shapes,
                                    ['slider', 'referential_low_vertical', 'referential_high_vertical', 'referential_low_horizontal', 'referential_high_horizontal'])
                                )[data['shape']],
                                moved_by_finger=moved_by_finger)
