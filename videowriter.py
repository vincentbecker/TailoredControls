import cv2
import threading
import time


# A threaded video writer that ensures correct FPS
def threaded_rec(framerate, bgr_stream, depth_stream, robust):
    t = threading.current_thread()
    nextwakeup = time.time() + 1 / framerate
    while not t.stop:
        if t.frames is not None:
            bgr_stream.write(t.frames[0])
            depth_stream.write(t.frames[1])
        nextwakeup += 1 / framerate
        delay = nextwakeup - time.time()
        if delay < 0:
            if robust:
                nextwakeup = time.time() + 1 / framerate
            print("Warning: Cannot reach framerate {} for video writing".format(framerate))
        else:
            time.sleep(delay)


class VideoWriter:
    def __init__(self, filename_bgr, filename_depth, framerate, framesize, robust=True, threaded=True):
        self.threaded = threaded
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.bgr_stream = cv2.VideoWriter(filename_bgr, fourcc, framerate, framesize)
        self.depth_stream = cv2.VideoWriter(filename_depth, fourcc, framerate, framesize)

        if self.threaded:
            self.thread = threading.Thread(target=threaded_rec, args=(framerate, self.bgr_stream, self.depth_stream, robust))
            self.thread.stop = False
            self.thread.frames = None
            self.thread.start()

    def process_frame(self, bgr, depth):
        if self.threaded:
            self.thread.frames = [bgr, cv2.cvtColor(depth, cv2.COLOR_GRAY2BGR)]
        else:
            self.bgr_stream.write(bgr)
            self.depth_stream.write(cv2.cvtColor(depth, cv2.COLOR_GRAY2BGR))

    def stop(self):
        if self.threaded:
            self.thread.stop = True
            self.thread.join()
        self.bgr_stream.release()
        self.depth_stream.release()
