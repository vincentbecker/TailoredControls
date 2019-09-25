from touchet import Touchet
from shapepicker import shapepicker


class TouchetB(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.instantiate,
            "Pick a shape that you want to become a button.",
            touchet_manager
        )

    @classmethod
    def instantiate(cls, shape, touchet_manager):
        touchet_manager.add_touchet(cls([shape]))

    def __init__(self, shapes):
        super().__init__(shapes)
        self.down = False

    def on_finger_down(self, _, data):
        self.down = True
        self.emit_touchet_event('pressed')

    def on_finger_up(self, _, data):
        self.down = False
