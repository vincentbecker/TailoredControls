import time

from touchet import Touchet
from shapepicker import shapepicker


class TouchetHB(Touchet):

    @classmethod
    def prepare(cls, touchet_manager):  # Need to pass touchet manager as argument to avoid cyclic dependencies
        shapepicker().pick(
            cls.instantiate,
            "Pick a shape that you want to become a hold button.",
            touchet_manager
        )

    @classmethod
    def instantiate(cls, shape, touchet_manager):
        touchet_manager.add_touchet(cls([shape]))

    def __init__(self, shapes):
        super().__init__(shapes)
        self.down = False
        self.down_on = 0
        self.reported_long_press = False

    def on_finger_down(self, *_):
        self.down = True
        self.down_on = time.time()
        self.emit_touchet_event('pressed')

    def on_finger_pressing(self, *_):
        if not self.reported_long_press and time.time() - self.down_on >= 0.5:
            self.reported_long_press = True
            self.emit_touchet_event('pressed_long')

    def on_finger_up(self, *_):
        self.down = False
        duration = time.time() - self.down_on
        self.emit_touchet_event('released', duration=duration)
        self.reported_long_press = False
        if duration < 0.5:
            self.emit_touchet_event('pressed_short')
