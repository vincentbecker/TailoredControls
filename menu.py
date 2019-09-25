import cv2
import numpy as np
import time

from realsensecam import realsensecam
from bbox import Bbox


class Menu:
    def __init__(self, bg_color):
        self.bg_color = bg_color
        self.items = {}
        self.most_recent_mc = None
        self.mc_stable_since = 0

        self.margin = 20
        self.outter_w = realsensecam().W / 3
        self.inner_w = self.outter_w - 2 * self.margin
        self.outter_h = realsensecam().H / 6
        self.inner_h = self.outter_h - 2 * self.margin

    def clear_items(self):
        self.items = {}

    def add_item(self, xpos, ypos, text, callback, *args):
        self.items[(xpos, ypos)] = [text, 0, callback, args]

    def on_finger_pressing(self, xy):
        mc = self.__mc_for_xy(xy)
        if mc != self.most_recent_mc:
            self.most_recent_mc = mc
            self.mc_stable_since = time.time()
            for val in self.items.values():
                val[1] = 0
        if mc in self.items:
            self.items[mc][1] = min(1, time.time() - self.mc_stable_since)
            if self.items[mc][1] > 0.999:
                for val in self.items.values():
                    val[1] = 0
                self.items[mc][2](*self.items[mc][3])
                self.mc_stable_since = time.time()

    def visualize(self, visualizer):
        bg = np.full(visualizer.frame.shape, self.bg_color, dtype=visualizer.frame.dtype)
        visualizer.frame = cv2.addWeighted(visualizer.frame, .2, bg, 1, 0)
        for (x, y), (text, progress, *_) in self.items.items():
            x0 = int(x * self.outter_w + self.margin)
            y0 = int(y * self.outter_h + self.margin)
            x1 = int(x0 + self.inner_w)
            y1 = int(y0 + self.inner_h)
            cv2.rectangle(visualizer.frame, (x0, y0), (x1, y1), (int(255 - 255 * progress), 255, 255), 1)
            cv2.putText(visualizer.frame, text, (x0, y1 - int(self.margin / 3)), cv2.FONT_HERSHEY_SIMPLEX, .6, (int(255 - 255 * progress), 255, 255), 1)

    def __mc_for_xy(self, xy):
        for x in range(3):
            for y in range(6):
                x0 = int(x * self.outter_w + self.margin)
                y0 = int(y * self.outter_h + self.margin)
                if Bbox(x0, y0, int(self.inner_w), int(self.inner_h)).contains(*xy):
                    return (x, y)
        return None
