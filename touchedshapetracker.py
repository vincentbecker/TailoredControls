from realsensecam import realsensecam
import cv2
import numpy as np
import random

from publisher import Publisher
from handdetector import handdetector
from handtracker import handtracker
from shapedetector import shapedetector
from shapetracker import shapetracker
import icp
from bbox import Bbox

import time

__touchedshapetracker_instance = None


def touchedshapetracker(*init_params):
    global __touchedshapetracker_instance
    if __touchedshapetracker_instance is None:
        __touchedshapetracker_instance = TouchedShapeTracker(*init_params)
    return __touchedshapetracker_instance


class TouchedShapeTracker(Publisher):
    def __init__(self):
        super().__init__()
        self.move = False
        self.old_hand_mask = None
        self.old_mask_to_search = None
        self.old_translation = None
        self.old_rotation = None
        self.initial_mask_to_search = None

    def update(self):
        touched_shape = handtracker().touched_shape
        if touched_shape is None:
            return

        # Create a mask that should only contain the shape that is being moved, without the finger
        new_hand_mask = handdetector().most_recent_mask
        shape_mask = shapedetector().most_recent_mask
        new_mask_to_search = cv2.bitwise_and(shape_mask, shape_mask, mask=(255 - new_hand_mask))
        for shape in shapetracker().shapes.values():
            if shape != touched_shape:
                cv2.drawContours(new_mask_to_search, [shape.cnt], 0, 0, -1)
                cv2.drawContours(new_mask_to_search, [shape.cnt], 0, 0, 5)
        new_mask_to_search = cv2.morphologyEx(new_mask_to_search, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        if self.old_mask_to_search is None:
            self.old_mask_to_search = new_mask_to_search
            self.initial_mask_to_search = new_mask_to_search
            self.old_hand_mask = new_hand_mask
            return  # The prediction will only be possible in the next frame

        # Calculate xor between last shape footprint (since it has last moved, ignoring swipes) and its current footprint
        xored_mask = cv2.bitwise_xor(self.old_mask_to_search, new_mask_to_search)
        xored_mask = cv2.bitwise_and(xored_mask, 255 - self.old_hand_mask)
        xored_mask = cv2.bitwise_and(xored_mask, 255 - new_hand_mask)
        xored_mask = cv2.morphologyEx(xored_mask, cv2.MORPH_OPEN, np.ones((2, 2)))
        # Use this metric to determine if the shape has moved significantly
        amount_moved_pixels = np.count_nonzero(xored_mask)
        if amount_moved_pixels > 200:
            self.move = True
            if not touched_shape.moving:
                touched_shape.start_moving(np.array(handdetector().fingertip_pos))

            # Calculate and apply transform
            angle = touched_shape.transform_to_fit_masks(
                self.initial_mask_to_search, new_mask_to_search, -handtracker().finger_deg_delta
            )[1]

            # Prepare next iteration
            self.old_mask_to_search = new_mask_to_search
            self.old_hand_mask = new_hand_mask
        else:
            self.move = False
            touched_shape.stop_moving()

    def on_finger_up(self, *_):
        self.move = False
        self.old_hand_mask = None
        self.old_mask_to_search = None
        self.initial_mask_to_search = None

    def __largest_ext_cnt(self, img):
        _, cnts, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(cnts) == 0:
            return None
        return max(cnts, key=lambda c: cv2.contourArea(c))
