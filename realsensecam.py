import pyrealsense2 as rs
import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy import ndimage

__realsensecam_instance = None


def realsensecam(*init_params):
    global __realsensecam_instance
    if __realsensecam_instance is None:
        print("Starting camera")
        try:
            __realsensecam_instance = RealsenseCam(*init_params)
        except:
            print("Could not initialize RealSense camera! Make sure it is supported by pyrealsense2. Try re-plugging it (maybe to a different USB port).")
            raise
    return __realsensecam_instance


class RealsenseCam:
    W = 640
    H = 480

    # If you want to use files instead of the actual cam, you may pass an array [bgr_filename, depth_filename] as argument
    def __init__(self, video_files=None):
        # Initialize RealSense intrinsics
        self.diagonal = np.linalg.norm((self.W, self.H))
        self.pipeline = rs.pipeline()
        self.aligner = rs.align(rs.stream.color)
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, 640, 360, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, self.W, self.H, rs.format.bgr8, 30)
        self.temporal_filter = rs.temporal_filter()
        self.hole_filling_filter = rs.hole_filling_filter()
        self.from_file = video_files is not None
        self.max_dist_mm = None

        if self.from_file:
            self.stream_bgr = cv2.VideoCapture(video_files[0])
            self.stream_depth = cv2.VideoCapture(video_files[1])
        else:
            # Start up camera
            profile = self.pipeline.start(self.config)

            # Set camera options
            sensor = profile.get_device().first_depth_sensor()
            sensor.set_option(rs.option.enable_auto_exposure, 1)
            # sensor.set_option(rs.option.exposure, 5000)

            # Acquire an initial set of frames used for calibration
            # Flush 10 frames to get the Intel temporal filter warmed up
            for i in range(30):
                self.__acquire_raw_aligned()

            # Save a snapshot of the background for later subtraction, blur it for denoising purposes
            self.__depth_background = ndimage.gaussian_filter(self.__depth_raw_aligned, 20)

            # Auto-detect table height
            self.max_dist_mm = np.max(self.__depth_background) + 100

    def __acquire_raw_aligned(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.aligner.process(frames)

        # Store color bitmap from the regular sensor as a numpy array (suitable for OpenCV)
        self.bgr = np.asanyarray(aligned_frames.get_color_frame().get_data())

        # Get denoised distance bitmap of depth (larger (brighter) pixel is further from sensor)
        # In this intermediate result, objects have different coordinates than in the bgr image
        depth_frame = aligned_frames.get_depth_frame()
        depth_frame = self.temporal_filter.process(depth_frame)
        depth_frame = self.hole_filling_filter.process(depth_frame)
        self.__depth_raw_aligned = np.asanyarray(depth_frame.get_data())

    def acquire_frames(self):
        if self.from_file:
            ret, self.bgr = self.stream_bgr.read()
            if not ret:
                return False
            self.depth_processed = cv2.cvtColor(self.stream_depth.read()[1], cv2.COLOR_BGR2GRAY)
            self.depth_blurred = cv2.GaussianBlur(self.depth_processed, (19, 19), 0)
        else:
            # First, acquire fresh frames and retrieve the aligned but still raw depth
            self.__acquire_raw_aligned()

            # Remove the background captured in the first picture (fill negative results with 0s)
            depth = np.zeros_like(self.__depth_raw_aligned)
            allowed_indices = self.__depth_background > self.__depth_raw_aligned  # Find uint16 underflows
            depth[allowed_indices] = (self.__depth_background - self.__depth_raw_aligned)[allowed_indices]

            # Remove elements that are higher than the auto-detected maximum
            depth[depth > self.max_dist_mm] = self.max_dist_mm

            # For later usage, cv2 requires us to convert stuff to uint8
            scale_by = np.iinfo(np.uint8).max / self.max_dist_mm
            self.depth_processed = (depth * scale_by).astype(np.uint8)
            self.depth_blurred = cv2.GaussianBlur(self.depth_processed, (19, 19), 0)
        return True

    # Show a curve visualizing the distribution of the depth across all pixels
    def visualize_depth_distribution(self):
        x, y = np.unique(self.depth_processed, return_counts=True)
        plt.plot(x, y)
        plt.show()

    # You MUST call this upon program exit (even on exception), otherwise the cam will fail to start the next time.
    def stop(self):
        if self.from_file:
            self.stream_bgr.release()
            self.stream_depth.release()
        else:
            self.pipeline.stop()
            print("Cam stopped")
