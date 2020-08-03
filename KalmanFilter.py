from pykalman import KalmanFilter
import numpy as np


def smooth_measurements(measurements):
    measurements = np.asarray(measurements)
    initial_state_mean = [measurements[0][0], 0,
                          measurements[0][1], 0]

    transition_matrix = [[1, 1, 0, 0],
                         [0, 1, 0, 0],
                         [0, 0, 1, 1],
                         [0, 0, 0, 1]]

    observation_matrix = [[1, 0, 0, 0],
                          [0, 0, 1, 0]]

    kf1 = KalmanFilter(transition_matrices=transition_matrix,
                       observation_matrices=observation_matrix,
                       initial_state_mean=initial_state_mean)

    kf1 = kf1.em(measurements, n_iter=10)
    (smoothed_state_means, smoothed_state_covariances) = kf1.smooth(measurements)

    return smoothed_state_means



