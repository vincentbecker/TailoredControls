import cv2
import numpy as np
from scipy.spatial.distance import cdist

from publisher import Publisher
from conf import conf
from realsensecam import realsensecam


__handdetector_instance = None


def handdetector(*init_params):
    global __handdetector_instance
    if __handdetector_instance is None:
        __handdetector_instance = HandDetector(*init_params)
    return __handdetector_instance


class HandDetector(Publisher):
    def __init__(self):
        super().__init__()
        self.hand_cnt = None
        self.hand_valid = True
        self.fingertip_height = np.inf
        self.secondary_hand_cnts = []

    def determine_hand_cnt(self):
        # Cut along the table surface to get all objects lying above it
        _, depth_th_hand = cv2.threshold(realsensecam().depth_blurred, conf()['hand_depth_threshold'], 255, cv2.THRESH_BINARY)
        self.most_recent_mask = depth_th_hand

        # Detect the contours, the largest is assumed to be the hand
        self.hand_cnt = None
        self.secondary_hand_cnts = []
        self.hand_valid = True
        contours, _ = cv2.findContours(depth_th_hand, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0:
            sorted_cnts = sorted(contours, key=lambda c: -cv2.contourArea(c))
            if cv2.contourArea(sorted_cnts[0]) > 500:  # Largest contour is the hand
                self.hand_cnt = sorted_cnts[0]
            for cnt in sorted_cnts[1:]:  # Other large contours will be saved as secondary hands
                if cv2.contourArea(cnt) < 500:
                    break
                self.secondary_hand_cnts.append(cnt)
        if self.hand_cnt is None:
            return  # No hand detected

        # The following code is used to find out where the hand enters the camera

        # Initialize / reset datastructures
        touched_corners = set()  # This will hold the edges of the frame that are touched by the hand
        self.edgepts = []
        self.edgeextrem1 = None
        self.edgeextrem2 = None
        self.edgeextremcenter = None

        # Detect points touching an edge and account which edges are touched
        for pt in self.hand_cnt[:, 0]:
            iscorner = False
            if pt[1] <= 1:  # Top edge
                touched_corners.add(0)
                iscorner = True
            if pt[0] <= 1:  # Left edge
                touched_corners.add(1)
                iscorner = True
            if pt[1] >= realsensecam().H - 1:  # Bottom edge
                touched_corners.add(2)
                iscorner = True
            if pt[0] >= realsensecam().W - 1:  # Right edge
                touched_corners.add(3)
                iscorner = True
            if iscorner:  # If the point has touched an edge, add it to edgepts
                self.edgepts.append(pt)

        # Make sure that top and bottom (or left and right) edge are not touched simultaneously
        for i in touched_corners:
            for j in touched_corners:
                if i != j and i % 2 == j % 2:
                    # In this case, the hand is larger than the recorded area and we cannot infer anything
                    self.hand_valid = False
                    print("Hand error: Too long hand")
                    return

        # Detect where the hand is touching the edge(s)
        if len(self.edgepts) < 2:
            self.hand_valid = False
            print("Hand error: Edge points detection failed")
            return
        # Find the two points touching an edge that are furthest apart, as well as their center
        pairwise_1_norm_dists = cdist(self.edgepts, self.edgepts, 'cityblock')
        furthest_pts = np.unravel_index(np.argmax(pairwise_1_norm_dists), pairwise_1_norm_dists.shape)
        self.edgeextrem1 = tuple(self.edgepts[furthest_pts[0]])
        self.edgeextrem2 = tuple(self.edgepts[furthest_pts[1]])
        self.edgeextremcenter = (int((self.edgeextrem1[0] + self.edgeextrem2[0]) / 2), int((self.edgeextrem1[1] + self.edgeextrem2[1]) / 2))

        # The following code is for finger detection

        # Acquire slice
        slice_img = self.__get_slice_img(3, 20)
        if slice_img is None:
            self.hand_valid = False
            print("Hand error: Invalid slice img")
            return
        slice_cnts, _ = cv2.findContours(slice_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(slice_cnts) == 0:
            self.hand_valid = False
            print("Hand error: Invalid slice contours")
            return

        # Get furthest point from arm entry point
        cnts_arr = np.concatenate(slice_cnts)[:, 0]
        dists = cdist(cnts_arr, [self.edgeextremcenter])
        furthest_pt = cnts_arr[np.argmax(dists, axis=0)][0]
        self.fingertip_pos = tuple(furthest_pt)

        # Calculate height of fingertip
        x = self.fingertip_pos[0]
        y = self.fingertip_pos[1]
        r = conf()['finger_height_measure_radius']
        left = max(0, x - r)
        top = max(0, y - r)
        right = min(realsensecam().W, x + r)
        bottom = min(realsensecam().H, y + r)
        # Let the highest pixel of that surface be the fingertip height
        cropped = realsensecam().depth_blurred[top:bottom, left:right]
        observed_height = np.max(cropped)
        if self.fingertip_height == np.inf:
            self.fingertip_height = observed_height
        else:
            self.fingertip_height = 0.5 * observed_height + 0.5 * self.fingertip_height

    # Returns true iff the passed OpenCV contour intersects with the save hand contour.
    def cnt_intersects_with_hand(self, cnt, include_secondary_contours=True):
        if self.hand_cnt is None:
            return False

        # Create two empty frames, draw the contours and perform bitwise and
        hand_img = np.zeros((realsensecam().H, realsensecam().W, 1), np.uint8)
        cnt_img = hand_img.copy()
        contours_to_check = [self.hand_cnt]
        if include_secondary_contours:
            contours_to_check += self.secondary_hand_cnts
        cv2.drawContours(hand_img, contours_to_check, -1, 255, -1)
        cv2.drawContours(hand_img, contours_to_check, -1, 255, conf()['hand_shape_intersection_border'])
        cv2.drawContours(cnt_img, [cnt], 0, 255, cv2.FILLED)
        anded = np.bitwise_and(hand_img, cnt_img)

        # If there are non-zero pixels left after "and"ing, there is an intersection
        return np.any(anded)

    def on_hand_exit(self, *_):
        self.fingertip_height = np.inf

    def __get_layer_cnt(self, layer):
        _, depth_th = cv2.threshold(realsensecam().depth_blurred, layer, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(depth_th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0:
            return max(contours, key=lambda c: cv2.contourArea(c))
        else:
            return None

    def __get_slice_img(self, lowest_layer, highest_layer):
        marker_points = []
        for i in range(lowest_layer, highest_layer):
            largest_cnt = self.__get_layer_cnt(i)
            if largest_cnt is not None:
                hull = cv2.convexHull(largest_cnt, returnPoints=False)
                defects = cv2.convexityDefects(largest_cnt, hull)

                if defects is None:
                    continue

                for i in range(defects.shape[0]):
                    s, e, f, d = defects[i, 0]
                    start = tuple(largest_cnt[s][0])
                    end = tuple(largest_cnt[e][0])
                    far = tuple(largest_cnt[f][0])
                    marker_points.append(start)
                    marker_points.append(end)

        marker_img = np.zeros((realsensecam().H, realsensecam().W), np.uint8)
        for op in marker_points:
            cv2.circle(marker_img, op, 1, 255, -1)
        marker_img = cv2.morphologyEx(marker_img, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        return marker_img
