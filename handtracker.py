import cv2
import numpy as np
from scipy import optimize

import icp
from publisher import Publisher
from conf import conf
from realsensecam import realsensecam
from handdetector import handdetector
from shapetracker import shapetracker
from touchetmanager import touchetmanager


__handtracker_instance = None


def handtracker(*init_params):
    global __handtracker_instance
    if __handtracker_instance is None:
        __handtracker_instance = HandTracker(*init_params)
    return __handtracker_instance


class HandTracker(Publisher):
    def __init__(self):
        super().__init__()
        self.hand_visible = False
        self.finger_down = False
        self.touched_shape = None
        self.of_enabled = False
        self.of_feature_params = dict(maxCorners=100,  # params for ShiTomasi corner detection
                                      qualityLevel=0.01,
                                      minDistance=3,
                                      blockSize=7)
        self.of_lk_params = dict(winSize=(15, 15),  # Parameters for lucas kanade optical flow
                                 maxLevel=2,
                                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        # Datastructures since finger down
        self.finger_delta = (0, 0)
        self.finger_deg_delta = 0
        self.finger_transform = None

    # Returns False iff multiple hands are detected
    def update(self):
        if not handdetector().hand_valid:
            return False

        # Check if the visibility of the hand has changed
        now_visible = handdetector().hand_cnt is not None
        was_visible = self.hand_visible
        self.hand_visible = now_visible
        if now_visible and not was_visible:
            self.publish('hand_enter', None)
        if not now_visible and was_visible:
            self.publish('hand_exit', None)

        # Check if finger is down or not
        now_down = handdetector().fingertip_height < conf()['finger_height_threshold']
        was_down = self.finger_down
        self.finger_down = now_down

        if now_down and not was_down:
            self.__start_of_tracking()
            self.__update_of()
            data = {'fingertip_pos': self.enhanced_fingertip_pos(), 'finger_delta': self.finger_delta, 'finger_deg_delta': self.finger_deg_delta}
            self.publish('finger_down', data)
            touchetmanager().emit_global_event('finger_down', data)
            for shape in shapetracker().shapes.values():
                shape.on_finger_down(data)  # The shape will figure out if it is the target

        if not now_down and was_down:
            self.__stop_of_tracking()
            data = {'fingertip_pos': self.enhanced_fingertip_pos(), 'finger_delta': self.finger_delta, 'finger_deg_delta': self.finger_deg_delta}
            self.publish('finger_up', data)
            touchetmanager().emit_global_event('finger_up', data)
            for shape in shapetracker().shapes.values():
                shape.on_finger_up(data)  # The shape will figure out if it is the target

        if was_down and now_down:
            data = {'fingertip_pos': self.enhanced_fingertip_pos(), 'finger_delta': self.finger_delta, 'finger_deg_delta': self.finger_deg_delta}
            self.publish('finger_pressing', data)
            touchetmanager().emit_global_event('finger_pressing', data)
            for shape in shapetracker().shapes.values():
                shape.on_finger_pressing(data)  # The shape will figure out if it is the target
            if self.__update_of():  # Only trigger if the finger actually moved enough
                self.publish('finger_moved', data)
                touchetmanager().emit_global_event('finger_moved', data)
                for shape in shapetracker().shapes.values():
                    shape.on_finger_moved(data)  # The shape will figure out if it is the target
        return True

    def __start_of_tracking(self):
        self.of_enabled = True

        self.old_gray = cv2.cvtColor(realsensecam().bgr, cv2.COLOR_BGR2GRAY)
        mask = np.zeros((realsensecam().H, realsensecam().W), np.uint8)
        cv2.circle(mask, handdetector().fingertip_pos, 80, 255, -1)
        cnt_mask = np.zeros_like(mask)
        cv2.drawContours(cnt_mask, [handdetector().hand_cnt], 0, 255, -1)
        mask = cv2.bitwise_and(mask, cnt_mask)

        self.of_old_pts = p0 = cv2.goodFeaturesToTrack(self.old_gray, mask=mask, **self.of_feature_params)
        if self.of_old_pts is None:
            self.__stop_of_tracking()
            return
        self.of_orig_existing_pts = self.of_old_pts.copy()
        self.of_is_fingertip = np.array([0] * len(self.of_orig_existing_pts))

        fingertip = np.array(handdetector().fingertip_pos)
        for i, pt in enumerate(self.of_old_pts[:, 0]):
            if np.linalg.norm(np.array(pt) - fingertip) < 30:
                self.of_is_fingertip[i] = 1

    def __update_of(self):
        if not self.of_enabled:
            return

        # Calculate optical flow
        new_gray = cv2.cvtColor(realsensecam().bgr, cv2.COLOR_BGR2GRAY)
        new_pts, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, new_gray, self.of_old_pts, None, **self.of_lk_params)
        if new_pts is None:
            self.__stop_of_tracking()
            return

        # Mark points that are not on the hand as invalid
        for i, ptt in enumerate(new_pts):
            if not handdetector().cnt_intersects_with_hand(np.array([ptt]).astype(int)):
                st[i][0] = 0

        # Delete lost points
        self.of_orig_existing_pts = self.of_orig_existing_pts[st == 1]
        self.of_old_pts = self.of_old_pts[st == 1]
        self.of_is_fingertip = self.of_is_fingertip[st.flatten() == 1]
        new_pts = new_pts[st == 1]
        if len(new_pts) == 0:
            self.__stop_of_tracking()
            return

        old_finger_delta = self.finger_delta
        old_finger_deg_delta = self.finger_deg_delta

        T, R, t = icp.best_fit_transform(self.of_orig_existing_pts, new_pts)
        self.finger_delta = tuple(t)
        self.finger_deg_delta = np.rad2deg(np.arctan2(R[1, 0], R[0, 0]))
        self.finger_transform = T

        dt = np.linalg.norm(np.array(t) - np.array(old_finger_delta))
        dr = abs(old_finger_deg_delta - self.finger_deg_delta)

        # Prepare next iteration
        self.old_gray = new_gray.copy()
        self.of_old_pts = new_pts.reshape(-1, 1, 2)
        self.of_orig_existing_pts = self.of_orig_existing_pts.reshape(-1, 1, 2)

        return dt > 1 or dr > .3

    def __stop_of_tracking(self):
        self.of_enabled = False

    def enhanced_fingertip_pos(self):
        if not self.of_enabled:
            return handdetector().fingertip_pos

        fingertip_points = self.of_old_pts[self.of_is_fingertip == 1]
        if fingertip_points is None:
            return handdetector().fingertip_pos
        median = np.median(fingertip_points[:, 0], axis=0)
        if np.isnan(median).any():
            self.__stop_of_tracking()
            return handdetector().fingertip_pos

        return median
