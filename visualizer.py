import cv2
import numpy as np
import time

from realsensecam import realsensecam
from handdetector import handdetector
from handtracker import handtracker
from shapetracker import shapetracker
from touchedshapetracker import touchedshapetracker
from shapepicker import shapepicker
from touchetmanager import touchetmanager
from touchet_s import TouchetS
from touchet_us import TouchetUS
from touchet_sb import TouchetSB
from touchet_cs import TouchetCS
from shaperegionpicker import shaperegionpicker
from shapepositionpicker import shapepositionpicker
from ui import ui
from bbox import Bbox
import icp

__visualizer_instance = None


def visualizer(*init_params):
    global __visualizer_instance
    if __visualizer_instance is None:
        __visualizer_instance = Visualizer(*init_params)
    return __visualizer_instance


class Visualizer:
    def __init__(self):
        self.lost_shapes_y = realsensecam().H + 2
        self.lost_shapes_h = 30
        self.text_h = 40
        self.text_l = 0
        self.text_r = realsensecam().W
        self.text_y0 = self.lost_shapes_y + self.lost_shapes_h + 2
        self.text_y = [self.text_y0, self.text_y0 + self.text_h - 23, self.text_y0 + self.text_h - 4]
        self.text_size = 0.9
        self.start_time = time.time()
        self.nth_frame = 0
        self.fps = 0

    def visualize(self):
        self.frame = realsensecam().bgr.copy()

        if handdetector().hand_valid:
            self.__shapes()
            self.__touchets()
            ui().visualize_menu(self)  # Due to include cycle, this must be done in UI
            self.__hand()
            self.__shaperegionpicker()
        else:
            red_pic = np.full(self.frame.shape, (0, 0, 255), dtype=self.frame.dtype)
            self.frame = cv2.addWeighted(self.frame, 1, red_pic, 0.5, 0)

        # From here on, work with border
        self.frame = cv2.copyMakeBorder(self.frame, 0, self.text_h + self.lost_shapes_h + 4, 0, 0, cv2.BORDER_CONSTANT, 0)
        self.__lost_shapes()
        self.__stats()

        self.ts_of_last_frame = time.time()
        return self.frame

    def __hand(self):
        if handdetector().hand_cnt is not None:
            cv2.drawContours(self.frame, [handdetector().hand_cnt], 0, (0, 0, 0), 2)
            cv2.drawContours(self.frame, handdetector().secondary_hand_cnts, -1, (0, 0, 200), 2)
            cv2.drawMarker(self.frame, handdetector().edgeextrem1, (255, 255, 255), cv2.MARKER_TILTED_CROSS, 10)
            cv2.drawMarker(self.frame, handdetector().edgeextrem2, (255, 255, 255), cv2.MARKER_TILTED_CROSS, 10)
            cv2.drawMarker(self.frame, handdetector().edgeextremcenter, (255, 255, 255), cv2.MARKER_DIAMOND, 10)
            for i in [3, 9, 15 + int(handdetector().fingertip_height / 4)]:
                cv2.circle(self.frame, tuple(handtracker().enhanced_fingertip_pos()), i, (0, 255, 0) if handtracker().finger_down else (255, 255, 255), 1)

            if handtracker().of_enabled:
                pts = icp.apply_transform(handtracker().of_orig_existing_pts[:, 0], handtracker().finger_transform)
                for i, pt in enumerate(pts):
                    pt = tuple(pt[:2].astype(int, copy=False))
                    color = (0, 200, 200) if handtracker().of_is_fingertip[i] == 1 else (0, 0, 0)
                    cv2.drawMarker(self.frame, pt, color, cv2.MARKER_DIAMOND, 5)

    def __shaperegionpicker(self):
        if not shaperegionpicker().active:
            return
        for pt in shaperegionpicker().picked_regions:
            cv2.drawMarker(self.frame, tuple(pt), (0, 255, 0))

    def __shapes(self):
        for id, shape in shapetracker().shapes.items():
            {
                'fresh': self.__fresh_shape,
                'visible': self.__visible_shape,
                'covered': self.__covered_shape,
            }[shape.state](id, shape)
            if shape.pressed:
                self.__pressed_shape(shape)
            for kps in shape.keypoints.values():
                for kp in kps:
                    cv2.drawMarker(self.frame, tuple(kp.astype(int)), (0, 255, 0))
        for shape in shapetracker().pending_shapes:
            self.__pending_shape(shape)

    def __lost_shapes(self):
        for idx, lost_shape in enumerate(shapetracker().lost_shapes.values()):
            fac = self.lost_shapes_h / max(lost_shape.footprint.shape)
            scaled_footprint = cv2.resize(lost_shape.footprint, (0, 0), fx=fac, fy=fac)
            nz_idx = list(np.nonzero(scaled_footprint))
            nz_idx[0] += self.lost_shapes_y
            nz_idx[1] += idx * (self.lost_shapes_h + 2)
            self.frame[tuple(nz_idx)] = (255, 255, 255)

    def __fresh_shape(self, id, shape):
        x, y = shape.bbox.center()
        cv2.rectangle(self.frame, (x - 15, y - 4), (x - 15 + int(shapetracker().percentage_for_shape(shape) * 30), y + 4), (0, 200, 0), cv2.FILLED)
        cv2.rectangle(self.frame, (x - 15, y - 4), (x + 15, y + 4), (200, 200, 200))
        cv2.drawContours(self.frame, [shape.cnt], 0, (0, 255, 0), 1)

    def __visible_shape(self, id, shape):
        cv2.rectangle(self.frame, shape.bbox.top_left(), shape.bbox.bottom_right(), shape.color, 1)
        cv2.drawContours(self.frame, [shape.cnt], 0, (255, 255, 255), 1)
        name = str(id) if not shape.action_name else "{} ({})".format(id, shape.action_name)
        cv2.putText(self.frame, name, shape.bbox.center(), cv2.FONT_HERSHEY_COMPLEX_SMALL, self.text_size, (255, 255, 255))

    def __covered_shape(self, id, shape):
        cv2.drawContours(self.frame, [shape.cnt], 0, (150, 150, 150), 1)
        name = str(id) if not shape.action_name else "{} ({})".format(id, shape.action_name)
        cv2.putText(self.frame, name, shape.bbox.center(), cv2.FONT_HERSHEY_COMPLEX_SMALL, self.text_size, (150, 150, 150))

    def __pending_shape(self, shape):
        cv2.drawContours(self.frame, [shape.cnt], 0, (0, 150, 0), 1)
        cv2.putText(self.frame, '...', shape.bbox.center(), cv2.FONT_HERSHEY_COMPLEX_SMALL, self.text_size, (255, 255, 255))

    def __pressed_shape(self, shape):
        cv2.rectangle(self.frame, shape.bbox.top_left(), shape.bbox.bottom_right(), (150, 150, 150), 1)
        color = (255, 0, 255) if shape.moving else (0, 255, 255)
        cv2.drawContours(self.frame, [shape.cnt], 0, color, 1)
        if shape.moving:
            cv2.arrowedLine(self.frame, tuple(shape.initial_move_xy), tuple(shape.current_move_xy), color, 3)
        else:
            cv2.arrowedLine(self.frame, tuple(shape.initial_swipe_xy), tuple(shape.current_swipe_xy), color, 3)

    def __touchets(self):
        for touchet in touchetmanager().touchets:
            for shape in touchet.shapes:
                cv2.putText(self.frame, type(touchet).__name__, (shape.bbox.x, shape.bbox.y2), cv2.FONT_HERSHEY_COMPLEX_SMALL, self.text_size, (150, 150, 150))
            if isinstance(touchet, TouchetS):
                pts = touchet.shapes[1].keypoints[touchet]
                cv2.line(self.frame, tuple(pts[0]), tuple(pts[1]), (0, 255, 0))
            if isinstance(touchet, TouchetSB):
                pts = touchet.shapes[0].keypoints[touchet]
                cv2.line(self.frame, tuple(touchet.shapes[0].bbox.center()), tuple(pts[0]), (0, 255, 0))
            if isinstance(touchet, TouchetCS):
                pts = touchet.shapes[1].keypoints[touchet]
                cv2.line(self.frame, tuple(touchet.shapes[1].bbox.center()), tuple(pts[0]), (0, 255, 0))
                cv2.line(self.frame, tuple(touchet.shapes[0].bbox.center()), tuple(touchet.shapes[1].bbox.center()), (0, 255, 0))
            if isinstance(touchet, TouchetUS):
                cv2.circle(self.frame, tuple(touchet.shapes[1].bbox.center_nparr().astype(int)), int(touchet.min_dist), (0, 255, 0))

    def __stats(self):
        self.nth_frame += 1
        elapsed = time.time() - self.start_time
        if elapsed > .1:
            self.fps = int(self.nth_frame / elapsed)
            self.nth_frame = 0
            self.start_time = time.time()

        self.__print("Tracking {:2d} shapes".format(len(shapetracker().shapes)), 2, self.text_l)
        self.__print("{:2d} FPS".format(self.fps), 2, self.text_r - 86)

        if not handdetector().hand_valid:
            self.__print("HAND ERROR! Too many or too long hands.", 1, self.text_l, color=(0, 0, 255))
        elif ui().menu_armed:
            self.__print("Hold the blue square to enter the menu.", 1, self.text_l, color=(255, 50, 50))
        elif ui().menu_active:
            self.__print("Pick an option from the menu.", 1, self.text_l, color=(255, 50, 50))
        elif ui().action_menu_armed:
            self.__print("Hold the blue square to enter the menu.", 1, self.text_l, color=(50, 255, 50))
        elif ui().action_menu_active:
            self.__print("Pick an option from the menu.", 1, self.text_l, color=(50, 255, 50))
        elif shapepicker().active:
            if shapepicker().must_lift_finger:
                self.__print("Please lift your finger.", 0, self.text_l, color=(0, 255, 255))
            else:
                self.__print(shapepicker().hint, 0, self.text_l, color=(0, 255, 0))
                self.__print("Press and hold the shape you want to pick ({}%)".format(int(100 * shapepicker().progress())), 1, self.text_l, color=(0, 255, 0))
        elif shaperegionpicker().active:
            if shaperegionpicker().must_lift_finger:
                self.__print("Please lift your finger (keep hand under camera).", 0, self.text_l, color=(0, 255, 255))
            else:
                self.__print("Press and hold {} in the shape ({}%)".format(shaperegionpicker().current_region_description(), int(100 * shaperegionpicker().progress())), 0, self.text_l, color=(0, 255, 0))
                self.__print("When all regions are selected, remove your hand.", 1, self.text_l, color=(0, 255, 0))
        elif shapepositionpicker().active:
            self.__print(shapepositionpicker().hint, 0, self.text_l, color=(0, 255, 0))
            self.__print("When the position has been reached, remove hand.", 1, self.text_l, color=(0, 255, 0))

    def __print(self, text, line, x_offset, color=(255, 255, 255)):
        cv2.putText(self.frame, text, (x_offset, self.text_y[line]), cv2.FONT_HERSHEY_COMPLEX_SMALL, self.text_size, color, 1)
