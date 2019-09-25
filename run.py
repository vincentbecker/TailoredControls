#!/usr/bin/env python

import cv2
import argparse
from conf import *
from controller import controller
from realsensecam import realsensecam
from videowriter import VideoWriter
from logger import Logger


def filename_from_name(name):
    return "{}_rgb.mp4".format(name), "{}_depth.mp4".format(name)


with Conf():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--video-output',
                        help="File name for storing the camera feed as a video")
    parser.add_argument('-i', '--video-input',
                        help="File name of the video pair used instead of the camera feed")
    parser.add_argument('-b' '--breakpoints', nargs='+', type=int,
                        help="Pause at the specified frames and wait for a key to be pressed")
    parser.add_argument('-l', '--logfile')
    args = parser.parse_args()

    if args.video_output is not None and args.video_input is not None:
        print("Error: You may not use -i and -o simultaneously. Please use only up to one of them at a time.")
        exit(-1)

    # Initialize camera
    if args.video_input is not None:
        realsensecam(list(filename_from_name(args.video_input)))
    else:
        realsensecam()

    if args.logfile is not None:
        logger = Logger()
    else:
        logger = None
    controller(logger)

    if args.video_output is not None:
        videowriter = VideoWriter(*filename_from_name(args.video_output), 30, (realsensecam().W, realsensecam().H), threaded=False)

    breakpoints = args.b__breakpoints or []
    while(True):
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
        if args.video_output is not None:
            videowriter.process_frame(realsensecam().bgr, realsensecam().depth_processed)
        if controller().frame in breakpoints:
            print("Paused at breakpoint", controller().frame)
            print("Press Space to advance by a single frame")
            k = cv2.waitKey()
            if k == ord(' '):
                breakpoints.append(controller().frame + 1)
    realsensecam().stop()  # Stop camera
    if args.video_output is not None:
        videowriter.stop()

    if logger is not None:
        logger.dump(args.logfile)
