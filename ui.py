import cv2
import numpy as np
import time
from conf import conf
import requests

from publisher import Publisher
from handtracker import handtracker
from bbox import Bbox
from realsensecam import realsensecam
from shapetracker import shapetracker
from menu import Menu
from touchetmanager import touchetmanager

from shapepicker import shapepicker

from touchet_b import TouchetB
from touchet_hb import TouchetHB
from touchet_pb import TouchetPB
from touchet_phb import TouchetPHB
from touchet_r import TouchetR
from touchet_s import TouchetS
from touchet_us import TouchetUS
from touchet_t import TouchetT
from touchet_fs import TouchetFS
from touchet_2t import Touchet2T
from touchet_2fs import Touchet2FS
from touchet_sb import TouchetSB
from touchet_cs import TouchetCS


__ui_instance = None


def ui(*init_params):
    global __ui_instance
    if __ui_instance is None:
        __ui_instance = UI(*init_params)
    return __ui_instance


class UI(Publisher):
    def __init__(self):
        super().__init__()
        self.finger_down_ts = 0

        self.menu_active = False
        self.menu_armed = False
        self.menu_progress = 0
        self.menu = Menu((100, 20, 0))
        self.menu.add_item(0, 1, 'Exit menu', self.__menu_close)
        self.menu.add_item(0, 5, 'Create CS touchet', self.create_touchet, TouchetCS)
        self.menu.add_item(1, 0, 'Create B touchet', self.create_touchet, TouchetB)
        self.menu.add_item(1, 1, 'Create HB touchet', self.create_touchet, TouchetHB)
        self.menu.add_item(1, 2, 'Create PB touchet', self.create_touchet, TouchetPB)
        self.menu.add_item(1, 3, 'Cr. PHB touchet', self.create_touchet, TouchetPHB)
        self.menu.add_item(1, 4, 'Cr. SB touchet', self.create_touchet, TouchetSB)
        self.menu.add_item(1, 5, 'Create R touchet', self.create_touchet, TouchetR)
        self.menu.add_item(2, 0, 'Create S touchet', self.create_touchet, TouchetS)
        self.menu.add_item(2, 1, 'Create US touchet', self.create_touchet, TouchetUS)
        self.menu.add_item(2, 2, 'Create T touchet', self.create_touchet, TouchetT)
        self.menu.add_item(2, 3, 'Create FS touchet', self.create_touchet, TouchetFS)
        self.menu.add_item(2, 4, 'Create 2T touchet', self.create_touchet, Touchet2T)
        self.menu.add_item(2, 5, 'Cr. 2FS touchet', self.create_touchet, Touchet2FS)

        self.action_menu_active = False
        self.action_menu_armed = False
        self.action_menu_progress = 0
        self.action_menu = Menu((0, 120, 0))
        self.action_menu.add_item(0, 1, 'Exit action menu', self.__action_menu_close)
        self.action_menu.add_item(0, 2, '(none)', self.__set_shape_action, "")

    def on_key(self, key):
        if key == ord('m'):
            if self.menu_active:
                self.__menu_close()
            else:
                self.__menu_open()
        if key == ord('a'):
            if self.action_menu_active:
                self.__action_menu_close()
            else:
                self.__action_menu_open()

    def on_finger_pressing(self, _, data):
        xy = data['fingertip_pos']
        if self.menu_active:
            self.menu.on_finger_pressing(xy)
        elif self.action_menu_active:
            self.action_menu.on_finger_pressing(xy)
        elif 50 <= xy[0] <= realsensecam().W - 50 or xy[1] >= 50:
            self.on_finger_up(None, data)
        elif self.menu_armed:
            self.menu_progress = min(1, time.time() - self.finger_down_ts)
            if self.menu_progress >= 1:
                self.__menu_open()
        elif self.action_menu_armed:
            self.action_menu_progress = min(1, time.time() - self.finger_down_ts)
            if self.action_menu_progress >= 1:
                self.__action_menu_open()
        else:
            self.on_finger_down(None, data)

    def on_finger_down(self, _, data):
        xy = data['fingertip_pos']
        if xy[1] < 50:
            if xy[0] < 50:
                self.menu_armed = True
                self.finger_down_ts = time.time()
            elif xy[0] > realsensecam().W - 50:
                self.action_menu_armed = True
                self.finger_down_ts = time.time()

    def on_finger_up(self, _, data):
        if self.menu_armed and self.menu_progress >= 1:
            self.__menu_open()
        if self.action_menu_armed and self.action_menu_progress >= 1:
            self.__action_menu_open()
        self.menu_armed = False
        self.menu_progress = 0
        self.action_menu_armed = False
        self.action_menu_progress = 0

    def visualize_menu(self, visualizer):
        visualizer.frame[0:50, 0:50] = (100, 20, 0)
        visualizer.frame[0:50, -50:] = (0, 120, 0)
        if self.menu_active:
            self.menu.visualize(visualizer)
        elif self.menu_armed:
            bg = np.full_like(visualizer.frame, (100, 20, 0))
            visualizer.frame = cv2.addWeighted(visualizer.frame, 1 - .8 * self.menu_progress, bg, self.menu_progress * 1, 0)
        elif self.action_menu_active:
            self.action_menu.visualize(visualizer)
        elif self.action_menu_armed:
            bg = np.full_like(visualizer.frame, (0, 120, 0))
            visualizer.frame = cv2.addWeighted(visualizer.frame, 1 - .8 * self.action_menu_progress, bg, self.action_menu_progress * 1, 0)

    def create_touchet(self, touchet_class):
        self.__menu_close()
        touchetmanager().mktouchet(touchet_class)

    def __menu_open(self):
        self.menu_active = True
        self.menu_armed = False
        self.menu_progress = 0

    def __menu_close(self):
        self.menu_active = False

    def __action_menu_open(self):
        self.action_menu_active = True
        self.action_menu_armed = False
        self.action_menu_progress = 0

        # Contact NodeRed and load available actions
        try:
            r = requests.get(conf()['actions_url'])
            matrix = list(np.ndindex(3, 6))[3:]
            self.action_menu.clear_items()
            self.action_menu.add_item(0, 1, 'Exit action menu', self.__action_menu_close)
            self.action_menu.add_item(0, 2, '(none)', self.__set_shape_action, "")
            for pos, action in enumerate(r.json()):
                if pos == len(matrix):
                    print("Cannot display all actions in menu, not enough space!")
                self.action_menu.add_item(*tuple(matrix[pos]), action, self.__set_shape_action, action)
        except requests.exceptions.RequestException as e:
            print("An error occured while attempting to connect to NodeRed:")
            print(e)

    def __action_menu_close(self):
        self.action_menu_active = False

    def __set_shape_action(self, action):
        self.__action_menu_close()
        shapepicker().pick(self.__set_shape_action_callback, "Pick the shape to set to {}".format(action), action)

    def __set_shape_action_callback(self, shape, action):
        shape.action_name = action
