import cv2
import numpy as np

from conf import conf
from publisher import Publisher
from handdetector import handdetector
from touchetmanager import touchetmanager

__shapetracker_instance = None


def shapetracker(*init_params):
    global __shapetracker_instance
    if __shapetracker_instance is None:
        __shapetracker_instance = ShapeTracker(*init_params)
    return __shapetracker_instance


class ShapeTracker(Publisher):
    def __init__(self):
        super().__init__()
        self.shapes = {}
        self.lost_shapes = {}
        self.pending_shapes = []  # Only used for visualization
        self.highest_id = 0
        self.epoch = 0

    def process_detected_shapes(self, detected_shapes):
        self.epoch += 1
        old_shape_ids = set(self.shapes.keys())
        new_shape_ids = set()
        self.pending_shapes = []

        # Attempt to match shapes by distance
        for old_id, old_shape in self.shapes.items():
            for detected_shape in detected_shapes:
                if np.linalg.norm(old_shape.bbox.center_nparr() - detected_shape.bbox.center_nparr()) < 30:
                    self.__update_shape_from(old_shape, detected_shape)
                    if old_shape.state == 'covered':
                        old_shape.set_state('visible')
                    new_shape_ids.add(old_id)
                    detected_shapes.remove(detected_shape)
                    break

        # Remove shapes that were not seen
        for missing_id in old_shape_ids - new_shape_ids:
            state = self.shapes[missing_id].state
            if state == 'fresh':
                del self.shapes[missing_id]
            if state == 'visible':
                if handdetector().cnt_intersects_with_hand(self.shapes[missing_id].cnt):
                    self.shapes[missing_id].set_state('covered')
            if state in ['visible', 'covered']:
                if not handdetector().cnt_intersects_with_hand(self.shapes[missing_id].cnt):
                    self.shapes[missing_id].set_state('lost')
                    self.lost_shapes[missing_id] = self.shapes[missing_id]
                    del self.shapes[missing_id]

        # Remaining shapes are new. Check if there is a match in the lost shapes, otherwise insert fresh shape.
        perfect_match = False
        # Special case "Perfect Match": We're looking for a single shape and found a single shape.
        # They are very likely the same, no check needed.
        if len(detected_shapes) == 1 and len(self.lost_shapes) == 1:
            perfect_match = True
        for detected_shape in detected_shapes:
            restored = False
            for id, lost_shape in self.lost_shapes.items():
                if perfect_match or detected_shape.hue_difference(lost_shape) < 0.15 and detected_shape.shape_difference(lost_shape) < 0.6:
                    lost_shape.state = 'visible'
                    self.__update_shape_from(lost_shape, detected_shape)
                    self.shapes[id] = lost_shape
                    del self.lost_shapes[id]
                    new_shape_ids.add(id)
                    restored = True
                    break
            if not restored:
                # There is no memory of the shape we're seeing -> insert fresh shape
                if handdetector().hand_cnt is None:
                    self.highest_id += 1
                    self.shapes[self.highest_id] = detected_shape
                else:
                    self.pending_shapes.append(detected_shape)

        # State changes
        for id, shape in self.shapes.items():
            if shape.state == 'fresh':
                if self.percentage_for_shape(shape) > .99:
                    shape.set_state('visible')

    def percentage_for_shape(self, shape):
        if shape.state == 'fresh':
            val = min(self.epoch - shape.state_stable_since, conf()['shape_confirm_frames'])
            return val / conf()['shape_confirm_frames']
        else:
            return 0

    # This method should be subscribed to the hand disappearing
    def clear_lost_shapes(self, *_):
        touchetmanager().clear_touchets_with_shapes(self.lost_shapes.values())
        self.lost_shapes.clear()

    def __update_shape_from(self, shape_to_update, detected_shape):
        if shape_to_update.needs_transform_to_fit_shape:
            shape_to_update.transform_to_fit_shape(detected_shape)
        else:
            shape_to_update.update_from(detected_shape)
