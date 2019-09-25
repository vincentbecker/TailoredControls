import cv2
import numpy as np

import icp
from publisher import Publisher
from bbox import Bbox
from realsensecam import realsensecam
from shapetracker import shapetracker
from handdetector import handdetector
from handtracker import handtracker
import transformationutils


class Shape(Publisher):
    def __init__(self, cnt):
        super().__init__()

        # Calculate the bbox
        bbox = Bbox(*cv2.boundingRect(cnt))

        # Draw an isolated footprint of the shape
        offset = tuple(- np.array(bbox.position()))
        isolated = np.zeros(bbox.size(True), np.uint8)
        cv2.drawContours(isolated, [cnt], 0, 255, -1, offset=offset)
        footprint = cv2.copyMakeBorder(isolated, 15, 15, 15, 15, cv2.BORDER_CONSTANT, 0)

        # Determine the color of the shape
        x, y, w, h = bbox.xywh()
        patch = realsensecam().bgr[y:y + h, x:x + w, :][int(h / 3):int(2 * h / 3), int(w / 3):int(2 * w / 3), :]
        patch = cv2.GaussianBlur(patch, (51, 51), 0)
        if patch is None:
            color = (0, 0, 0)
        else:
            ph, pw, _ = patch.shape
            color = patch[int(ph / 2), int(pw / 2)]
            color = tuple([int(x) for x in color])
            color_hsv = cv2.cvtColor(np.array([[color]], np.uint8), cv2.COLOR_BGR2HSV)[0][0]

        self.cnt = cnt
        self.bbox = bbox
        self.color = color
        self.color_hsv = color_hsv
        self.footprint = footprint
        self.angle = 0
        self.state = 'fresh'
        self.state_stable_since = shapetracker().epoch
        self.pressed = False
        self.moving = False
        self.initial_swipe_xy = None
        self.current_swipe_xy = None
        self.initial_move_xy = None
        self.current_move_xy = None
        self.initial_degs = 0
        self.current_degs = None
        self.cnt_on_down = None
        self.needs_transform_to_fit_shape = False
        self.keypoints = {}
        self.keypoints_on_down = None
        self.action_name = ""

    def update_from(self, other):
        self.cnt = other.cnt
        self.bbox = other.bbox
        self.color = other.color
        self.angle = other.angle

    def set_state(self, new_state):
        self.state = new_state
        self.state_stable_since = shapetracker().epoch

    # Recommended threshold for detecting another shape: 2%
    def position_difference(self, other_shape):
        return np.linalg.norm(other_shape.bbox.center_nparr() - self.bbox.center_nparr()) / realsensecam().diagonal

    # Recommended threshold for detecting another shape: 1%
    def hue_difference(self, other_shape):
        hs = self.color_hsv[0] * 2  # Due to 8 bit resolution in OpenCV, H is between 0 and 180 -> multiply by 2
        ho = other_shape.color_hsv[0] * 2
        return (180 - abs(abs(hs - ho) - 180)) / 360

    # Recommended threshold for detecting another shape: 10%
    def shape_difference(self, other_shape):
        return min(1, cv2.matchShapes(self.cnt, other_shape.cnt, 1, 0))

    def on_finger_down(self, data, do_not_check_xy=False, initiated_by_shape=False):
        xy = np.array(data['fingertip_pos'])
        degs = data['finger_deg_delta']
        if do_not_check_xy or self.bbox.contains(*xy):
            self.pressed = True
            self.initial_swipe_xy = xy
            self.current_swipe_xy = xy
            self.initial_move_xy = xy
            self.current_move_xy = xy
            self.initial_degs = degs
            self.current_degs = degs
            self.cnt_on_down = self.cnt.copy()
            self.keypoints_on_down = self.keypoints.copy()
            handtracker().touched_shape = self
            self.publish('finger_down', {
                **data,
                'shape': self,
                'shape_fingertip_pos': self.__offset_by_my_position(xy),
                'initiated_by_shape': initiated_by_shape
            })

    def on_finger_up(self, data, initiated_by_shape=False):
        xy = np.array(data['fingertip_pos'])
        if self.pressed:
            self.pressed = False
            self.needs_transform_to_fit_shape = True
            self.publish('finger_up', {
                **data,
                'shape': self,
                'shape_fingertip_pos': self.__offset_by_my_position(xy),
                'shape_was_moving': self.moving,
                'shape_move_delta': self.current_move_xy - self.initial_move_xy,
                'shape_swipe_delta': self.current_swipe_xy - self.initial_swipe_xy,
                'shape_degs': self.current_degs - self.initial_degs,
                'initiated_by_shape': initiated_by_shape
            })
            self.moving = False
            self.initial_swipe_xy = None
            self.current_swipe_xy = None
            self.initial_move_xy = None
            self.current_move_xy = None
            self.initial_degs = None
            self.current_degs = None
            self.cnt_on_down = None
            self.keypoints_on_down = None
            handtracker().touched_shape = None

    def on_finger_moved(self, data):
        self.on_finger_pressing(data, has_moved=True)

    def on_finger_pressing(self, data, has_moved=False):
        xy = np.array(data['fingertip_pos'])
        degs = data['finger_deg_delta']
        if self.pressed:
            if self.intersects_with(xy):
                self.publish('finger_moved' if has_moved else 'finger_pressing', {
                    **data,
                    'shape': self,
                })
                if self.moving:
                    self.current_move_xy = xy
                    self.initial_swipe_xy = xy  # Reset swipe vector because the shape has moved
                    self.current_swipe_xy = xy
                    self.publish('moved', {
                        **data,
                        'shape': self,
                        'shape_move_delta': self.current_move_xy - self.initial_move_xy,
                        'shape_degs': self.current_degs - self.initial_degs
                    })
                else:
                    self.current_swipe_xy = xy
                    self.current_move_xy = xy
                    self.publish('swiped', {
                        **data,
                        'shape': self,
                        'shape_swipe_delta': self.current_swipe_xy - self.initial_swipe_xy,
                        'shape_degs': self.current_degs - self.initial_degs
                    })
            else:
                if not self.moving:  # Prevent finger_up while moving
                    self.on_finger_up(data, initiated_by_shape=True)
        elif self.intersects_with(xy):
            self.on_finger_down(data, True, initiated_by_shape=True)

    def start_moving(self, xy):
        self.initial_move_xy = xy
        self.current_move_xy = xy
        self.initial_swipe_xy = xy  # Reset swipe vector because the shape has moved
        self.current_swipe_xy = xy
        self.moving = True
        self.publish('start_moving', {'shape': self, 'fingertip_pos': xy})

    def stop_moving(self):
        if self.moving:
            self.publish('stop_moving', {'shape': self})
        self.moving = False

    def intersects_with(self, xy):
        if not self.bbox.contains(*xy):  # Faster check with no false negatives
            return False
        if not handdetector().cnt_intersects_with_hand(self.cnt):  # More thorough check to avoid false positives
            return False
        return True

    def transform_to_fit_shape(self, other_shape):
        my_mask = np.zeros((realsensecam().H, realsensecam().W), np.uint8)
        other_mask = np.zeros_like(my_mask)
        cv2.drawContours(my_mask, [self.cnt], 0, 255, -1)
        cv2.drawContours(other_mask, [other_shape.cnt], 0, 255, -1)
        translation, angle = self.transform_to_fit_masks(my_mask, other_mask, origin_is_on_down=False)
        if abs(angle) < 8:  # Otherwise we will need to do this again
            self.needs_transform_to_fit_shape = False
        self.publish('transformation_adjusted', {'shape': self, 'shape_move_delta': translation, 'shape_degs': -angle})

    def transform_to_fit_masks(self, origin_mask, target_mask, starting_angle=0, origin_is_on_down=True):
        # Calculate best fit
        translation, angle = transformationutils.calculate_best_transformation_from_img(
            origin_mask, target_mask, starting_angle
        )

        # Translate
        # Distinguish if we are looking at the delta between the shape position on finger down or the at last frame
        if origin_is_on_down:
            self.cnt = self.cnt_on_down + np.flip(translation)
            for touchet in self.keypoints.keys():
                self.keypoints[touchet] = self.keypoints_on_down[touchet] + np.flip(translation)
        else:
            self.cnt += np.flip(translation)
            for touchet in self.keypoints.keys():
                self.keypoints[touchet] += np.flip(translation)

        # Rotate
        unpacked_cnt = self.cnt[:, 0]
        centroid = transformationutils.calculate_centroid(unpacked_cnt)
        unpacked_cnt = transformationutils.rotate_points(unpacked_cnt, centroid, angle)
        for touchet in self.keypoints.keys():
            self.keypoints[touchet] = transformationutils.rotate_points(self.keypoints[touchet], centroid, angle)
        self.cnt = unpacked_cnt.reshape(-1, 1, 2)

        # Adjust bbox and save most recent angle
        self.bbox = Bbox(*cv2.boundingRect(self.cnt))
        self.current_degs = -angle
        return translation, angle

    def __offset_by_my_position(self, xy):
        x, y = xy
        center = self.bbox.center()
        x -= center[0]
        y -= center[1]
        return x, y
