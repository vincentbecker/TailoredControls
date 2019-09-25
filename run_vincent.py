import cv2
from conf import *
from controller import controller
from realsensecam import realsensecam

NAME = 'sample_videos/test'

if __name__ == "__main__":
    with Conf():
        # Initialize camera
        realsensecam(list((NAME + '_rgb.mp4', NAME + '_depth.mp4')))
        # Initialize controller
        controller()

        while True:
            img = controller().next_frame()
            if img is None:
                print("Controller reports end of capture. Terminating.")
                break
            cv2.imshow('DynamicUIs', img)
            k = cv2.waitKey(1)
            if ord('q') == k:
                break
            else:
                controller().on_key(k)
        realsensecam().stop()  # Stop camera
