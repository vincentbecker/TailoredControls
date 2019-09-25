import time

from shapetracker import shapetracker


__shapepositionpicker_instance = None


def shapepositionpicker(*init_params):
    global __shapepositionpicker_instance
    if __shapepositionpicker_instance is None:
        __shapepositionpicker_instance = ShapePositionPicker(*init_params)
    return __shapepositionpicker_instance


class ShapePositionPicker:
    def __init__(self):
        self.active = False
        self.callback = None
        self.args = []
        self.stable_since = 0
        self.shape = None

    # Initiate picking procedure. After picking,
    # the callback will be called with the selected
    # shape and the given args
    def pick(self, shape, callback, hint, *args):
        self.active = True
        self.shape = shape
        self.callback = callback
        self.args = args
        self.hint = hint

    def on_hand_exit(self, *_):
        if self.active:
            self.active = False
            pos = self.shape.bbox.center_nparr()
            self.callback(pos, *self.args)
            return
