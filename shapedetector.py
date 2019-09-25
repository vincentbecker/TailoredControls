import cv2
import numpy as np

from conf import conf
from publisher import Publisher
from realsensecam import realsensecam
from handdetector import handdetector
from shape import Shape
from bbox import Bbox


__shapedetector_instance = None


def shapedetector(*init_params):
    global __shapedetector_instance
    if __shapedetector_instance is None:
        __shapedetector_instance = ShapeDetector(*init_params)
    return __shapedetector_instance


class ShapeDetector(Publisher):
    def detect_shapes(self):
        # Get mask by filtering by color saturation in HSV color space
        hsv = cv2.cvtColor(realsensecam().bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, conf()['shape_saturation_threshold'], 0]), np.array([255, 255, 255]))
        self.most_recent_mask = mask

        # Find contours in mask in order to isolate individual shapes
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_shapes = []
        for cnt in contours:
            if cv2.contourArea(cnt) < 750:
                continue
            if handdetector().cnt_intersects_with_hand(cnt):
                continue
            s = Shape(cnt)
            if s is not None:
                detected_shapes.append(s)
        return detected_shapes
