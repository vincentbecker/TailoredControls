import time

from shapetracker import shapetracker


__shapepicker_instance = None


def shapepicker(*init_params):
    global __shapepicker_instance
    if __shapepicker_instance is None:
        __shapepicker_instance = ShapePicker(*init_params)
    return __shapepicker_instance


class ShapePicker:
    def __init__(self):
        self.active = False
        self.callback = None
        self.args = []
        self.stable_since = 0
        self.shape = None

    # Initiate picking procedure. After picking,
    # the callback will be called with the selected
    # shape and the given args
    def pick(self, callback, hint, *args):
        self.active = True
        self.callback = callback
        self.args = args
        self.hint = hint
        self.must_lift_finger = True

    def on_finger_pressing(self, _, data):
        if not self.active or self.must_lift_finger:
            return

        xy = data['fingertip_pos']
        found = False
        for id, shape in shapetracker().shapes.items():
            if shape.bbox.contains(*xy):
                if shape != self.shape:
                    self.shape = shape
                    self.stable_since = time.time()
                found = True
                break
        if not found:
            self.shape = None
            self.stable_since = time.time()

        if time.time() - self.stable_since >= 1:
            self.active = False
            self.shape = None
            self.callback(shape, *self.args)  # Picking completed, call the callback
            return

    def on_finger_up(self, *_):
        self.shape = None
        self.must_lift_finger = False

    def progress(self):
        if self.shape is None:
            return 0
        return min(1, time.time() - self.stable_since)
