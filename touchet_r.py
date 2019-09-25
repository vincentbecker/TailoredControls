from touchet import Touchet
from shapepicker import shapepicker


class TouchetR(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.instantiate,
            "Pick a shape that should become a rotation touchet.",
            touchet_manager
        )

    @classmethod
    def instantiate(cls, shape, touchet_manager):
        touchet_manager.add_touchet(cls([shape]))

    def __init__(self, shapes):
        super().__init__(shapes)
        self.rotation_since_touched = 0  # degrees clockwise
        self.total_rotation = 0  # degrees clockwise
        self.total_rotation_when_down = 0

    def on_moved(self, _, data):
        self.rotation_since_touched = data['shape_degs']
        self.total_rotation = self.total_rotation_when_down + self.rotation_since_touched
        self.__emit(True)

    def on_transformation_adjusted(self, _, data):
        self.total_rotation += data['shape_degs']
        self.__emit(False)

    def on_finger_down(self, _, data):
        self.rotation_since_touched = 0
        self.total_rotation_when_down = self.total_rotation

    def __emit(self, rotated_by_finger):
        self.emit_touchet_event('rotated',
                                rotation_since_touched=self.rotation_since_touched,
                                total_rotation=self.total_rotation,
                                rotated_by_finger=rotated_by_finger)
