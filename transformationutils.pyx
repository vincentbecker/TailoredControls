import numpy as np
import cv2


# Private variables used for angle evaluation in calculate_best_transformation_from_img
ae_pixels1 = None
ae_pixels2 = None
ae_centroid = None
ae_shape = None


# Used in shape.py
def calculate_centroid(points):
    moments = cv2.moments(points)  # Calculate moments
    c_x = -1
    c_y = -1
    if moments['m00'] != 0:
        c_x = int(moments['m10'] / moments['m00'])
        c_y = int(moments['m01'] / moments['m00'])
    return np.array([c_x, c_y])


def calculate_centroid_set(points):
    return np.mean(points, axis=0)


def rotate_points(points, pivot, angle):
    rotation_matrix = cv2.getRotationMatrix2D(tuple(pivot), angle, 1)
    concat_pixels = np.concatenate((points, np.ones((points.shape[0], 1))), axis=1)
    return rotation_matrix.dot(concat_pixels.T).T.astype(int)


def get_pixel_set(img):
    x, y = np.nonzero(img)
    return np.stack((x, y), axis=1)


def linear_min_search(f, domain):
    return domain[np.argmin(list(f(domain)))]


def ternary_min_search(f, domain):
    length = len(domain)
    if length <= 3:
        min_index = np.argmin(f(domain))
        return domain[min_index]
    low = int(length / 3)
    high = int(2 * length / 3)
    low_score = f(domain[low])
    high_score = f(domain[high])
    if low_score < high_score:
        return ternary_min_search(f, domain[:high])
    else:
        return ternary_min_search(f, domain[(low + 1):])


def angle_mapper(angle):
    # Rotate white pixels
    rotation_matrix = cv2.getRotationMatrix2D(tuple(ae_centroid), angle, 1)
    concat_pixels = np.concatenate((ae_pixels1, np.ones((ae_pixels1.shape[0], 1))), axis=1)
    candidate = rotation_matrix.dot(concat_pixels.T).T.astype(int)

    # Remove invalid indices
    global ae_pixels2
    candidate = candidate[(candidate[:, 0] >= 0) &
                          (candidate[:, 1] >= 0) &
                          (candidate[:, 0] < ae_shape[0]) &
                          (candidate[:, 1] < ae_shape[1])]
    ae_pixels2 = ae_pixels2[(ae_pixels2[:, 0] >= 0) &
                            (ae_pixels2[:, 1] >= 0) &
                            (ae_pixels2[:, 0] < ae_shape[0]) &
                            (ae_pixels2[:, 1] < ae_shape[1])]

    # xor and count
    img1 = np.zeros(ae_shape, np.uint8)
    img1[tuple(candidate.T)] = 255
    img2 = np.zeros(ae_shape, np.uint8)
    img2[tuple(ae_pixels2.T)] = 255
    return np.count_nonzero(cv2.bitwise_xor(img1, img2))


# Used in shape.py
def calculate_best_transformation(shape1, finger1, shape2, finger2, starting_angle, shape):
    img1 = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(img1, shape1, 255)
    cv2.fillConvexPoly(img1, finger1, 0)
    img2 = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(img2, shape2, 255)
    cv2.fillConvexPoly(img2, finger2, 0)

    return calculate_best_transformation_from_img(img1, img2, starting_angle)


# Used in shape.py
def calculate_best_transformation_from_img(img1, img2, starting_angle):
    # Get pixel sets
    pixels_1 = get_pixel_set(img1)
    pixels_2 = get_pixel_set(img2)

    # Calculate translation
    centroid_1 = calculate_centroid_set(pixels_1)
    centroid_2 = calculate_centroid_set(pixels_2)
    best_translation = (centroid_2 - centroid_1).astype(np.int)

    # Apply translation to pixel set 1
    pixels_1 = pixels_1 + best_translation

    # Find the best rotation
    search_domain = -starting_angle + np.linspace(-10, 10, 41)

    # Ternary search
    global ae_pixels1
    global ae_pixels2
    global ae_centroid
    global ae_shape
    ae_pixels1 = pixels_1
    ae_pixels2 = pixels_2
    ae_centroid = centroid_2
    ae_shape = img1.shape
    angle_mapper_npfunc = np.frompyfunc(angle_mapper, 1, 1)
    best_angle = ternary_min_search(angle_mapper_npfunc, search_domain)

    return best_translation, -best_angle
