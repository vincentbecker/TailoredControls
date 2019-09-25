import numpy as np


class Bbox:
    def __init__(self, x, y, w_or_x2, h_or_y2, use_w_h=True):
        if use_w_h:
            self.update_from_xywh(x, y, w_or_x2, h_or_y2)
        else:
            self.update_from_xyx2y2(x, y, w_or_x2, h_or_y2)

    def update_from_xywh(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.x2 = x + w
        self.y2 = y + h

    def update_from_xyx2y2(self, x, y, x2, y2):
        if x > x2 or y > y2:
            return
        self.x = x
        self.y = y
        self.w = x2 - x
        self.h = y2 - y
        self.x2 = x2
        self.y2 = y2

    def extend_to_xy(self, xy):
        x, y = xy
        new_x = min(x, self.x)
        new_y = min(y, self.y)
        new_x2 = max(x, self.x2)
        new_y2 = max(y, self.y2)
        self.update_from_xyx2y2(new_x, new_y, new_x2, new_y2)

    def extend_to_bbox(self, other_bbox):
        self.extend_to_xy(other_bbox.top_left())
        self.extend_to_xy(other_bbox.bottom_right())

    def extend_by(self, amount_pixels):
        self.update_from_xyx2y2(self.x - amount_pixels,
                                self.y - amount_pixels,
                                self.x2 + amount_pixels,
                                self.y2 + amount_pixels)

    def shrink_by(self, amount_pixels):
        self.update_from_xyx2y2(self.x + amount_pixels,
                                self.y + amount_pixels,
                                self.x2 - amount_pixels,
                                self.y2 - amount_pixels)

    def shift_by(self, dxy):
        new_x = self.x + dxy[0]
        new_y = self.y + dxy[1]
        self.update_from_xywh(new_x, new_y, self.w, self.h)

    def position(self, np_format=False):
        return (self.y, self.x) if np_format else (self.x, self.y)

    def size(self, np_format=False):
        return (self.h, self.w) if np_format else (self.w, self.h)

    def top_left(self, np_format=False):
        return self.position(np_format)

    def top_left_nparr(self, np_format=False):
        return np.array(self.top_left(np_format))

    def top_right(self, np_format=False):
        return (self.y, self.x2) if np_format else (self.x2, self.y)

    def top_right_nparr(self, np_format=False):
        return np.array(self.top_right(np_format))

    def bottom_left(self, np_format=False):
        return (self.y2, self.x) if np_format else (self.x, self.y2)

    def bottom_left_nparr(self, np_format=False):
        return np.array(self.bottom_left(np_format))

    def bottom_right(self, np_format=False):
        return (self.y2, self.x2) if np_format else (self.x2, self.y2)

    def bottom_right_nparr(self, np_format=False):
        return np.array(self.bottom_right(np_format))

    def xywh(self):
        return self.x, self.y, self.w, self.h

    def center(self):
        return (int(self.x + self.w / 2), int(self.y + self.h / 2))

    def center_nparr(self):
        return np.array(self.center())

    def area(self):
        return self.x * self.y

    def contains(self, x, y):
        return self.x <= x and self.x2 >= x and self.y <= y and self.y2 >= y

    def contains_bbox(self, other_bbox):
        return self.x <= other_bbox.x and self.y <= other_bbox.y and self.x2 >= other_bbox.x2 and self.y2 >= other_bbox.y2

    def intersects_with_bbox(self, other_bbox):
        return self.x2 >= other_bbox.x and other_bbox.x2 >= self.x and self.y2 >= other_bbox.y and other_bbox.y2 >= self.y

    def copy(self):
        return Bbox(*self.xywh())

    def crop(self, img):
        return img[self.y:self.y2, self.x:self.x2]
