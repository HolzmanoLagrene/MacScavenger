import collections
import itertools
import random

import numpy as np
from scipy.ndimage import label
from scipy.ndimage.filters import gaussian_filter
from scipy.optimize import least_squares
from shapely.geometry import Polygon, LineString, Point


class MacScavengerLocalizer:

    def __init__(self, ap_dict_pos):
        self.ap_dict_pos = ap_dict_pos
        self.bounds = self._get_bounds_from_positions()
        self.amount_of_draws = 20
        self.meter_per_bin = 0.5
        self.n = 2
        self.f_scale = 1

    def localize(self, measurement):
        transformed_data = {self.ap_dict_pos[a]: b for a, b in measurement.items()}
        approximation = self._calculate_multilateration_nonlinear(transformed_data)
        regions = self._get_heatmap_peaks(approximation)
        return regions

    def is_equal(self, previous_regions, possible_actual_regions, timed_interval, km_per_h):
        distances = []
        possible_combinations = itertools.product(previous_regions, possible_actual_regions)
        for prev, actual in possible_combinations:
            if len(prev) >= 3:
                previous_region = Polygon(prev)
            elif len(prev) == 2:
                previous_region = LineString(prev)
            else:
                previous_region = Point(prev[0])
            if len(actual) >= 3:
                actual_region = Polygon(actual)
            elif len(actual) == 2:
                actual_region = LineString(actual)
            else:
                actual_region = Point(actual[0])

            max_possible_distance = timed_interval * (km_per_h / 3.6)
            distance = previous_region.distance(actual_region) * self.meter_per_bin
            distances.append(distance)
            if distance <= max_possible_distance:
                return True, prev, actual, distance
        return False, None, None, min(distances)

    def _distance_function(self, x, data, variance, var_impact):
        element_a = np.power([t[0] for t in data[:, 0]] - x[0], 2)
        element_b = np.power([t[1] for t in data[:, 0]] - x[1], 2)
        if var_impact == 'none':
            element_c = np.power(np.power(10, (np.absolute(data[:, 1]) - np.array(30)) / (10 * self.n)), 2)
        elif var_impact == 'add':
            element_c = np.power(np.power(10, (np.absolute(data[:, 1]) - (np.array(30) + variance)) / (10 * self.n)), 2)
        elif var_impact == 'subtract':
            element_c = np.power(np.power(10, (np.absolute(data[:, 1]) - (np.array(30) - variance)) / (10 * self.n)), 2)
        else:
            raise Exception
        return np.array(element_a + element_b - element_c, dtype=float)

    def _calculate_multilateration_nonlinear(self, data):
        if self.amount_of_draws:
            x = [random.uniform(self.bounds[0][0], self.bounds[1][0]) for a in range(self.amount_of_draws)]
            y = [random.uniform(self.bounds[0][1], self.bounds[1][1]) for a in range(self.amount_of_draws)]
            x0s = np.array((x, y)).transpose()
        else:
            x0s = np.array([[random.uniform(self.ap_dict_pos[0][0], self.ap_dict_pos[1][0]), random.uniform(self.ap_dict_pos[0][1], self.ap_dict_pos[1][1]), min(data['rssi'])]])
        location = []
        mean_measurements = [[[k[0], k[1]], np.mean(v)] for k, v in data.items()]
        for x0 in x0s:
            res_lsq_none = least_squares(self._distance_function, x0, loss='cauchy', f_scale=self.f_scale, bounds=self.bounds, args=(np.array(mean_measurements), 0, 'none'))
            location.append([res_lsq_none.cost, res_lsq_none.x[0], res_lsq_none.x[1]])
        return np.array(location)

    def _get_bounds_from_positions(self):
        positions = np.array(list(self.ap_dict_pos.values()))
        min_x, max_x, min_y, max_y = min(positions[:, 0]), max(positions[:, 0]), min(positions[:, 1]), max(positions[:, 1])
        return ([min_x, min_y], [max_x, max_y])

    def _calculate_normalized_weights(self, weights, from_=0.1, to_=0.9):
        r = [from_ + (((x - min(weights)) * (to_ - from_)) / (max(weights) - min(weights))) for x in weights]
        r_ = [1 - weight for weight in r]
        return np.array(r_)

    def _get_number_of_bins(self):
        return [int(self.bounds[1][0] / self.meter_per_bin), int(self.bounds[1][1] / self.meter_per_bin)]

    def _get_convex_hull(self, points):
        point = collections.namedtuple("point", "x y")
        points = [point(e[0], e[1]) for e in points]

        def cross(p1, p2, p3):
            return (p2.x - p1.x) * (p3.y - p1.y) - (p2.y - p1.y) * (p3.x - p1.x)

        def slope(p1, p2):
            return 1.0 * (p1.y - p2.y) / (p1.x - p2.x) if p1.x != p2.x else float('inf')

        def dis(p1, p2):
            return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

        start = min(points, key=lambda p: (p.x, p.y))
        points.pop(points.index(start))

        points_slopes = [(p, slope(p, start)) for p in points]
        points_slopes.sort(key=lambda e: e[1])
        points = []
        i = 0
        for j in range(1, len(points_slopes)):
            if points_slopes[j][1] != points_slopes[i][1]:
                if j - i == 1:
                    points.append(points_slopes[i])
                else:
                    points_cl = sorted(points_slopes[i:j], key=lambda e: dis(start, e[0]))
                    points.extend(points_cl)
                i = j
        points_cl = sorted(points_slopes[i:], key=lambda e: -dis(start, e[0]))
        points.extend(points_cl)
        points = [p[0] for p in points]

        ans = [start]
        for p in points:
            ans.append(p)
            while len(ans) > 2 and cross(ans[-3], ans[-2], ans[-1]) < 0:
                ans.pop(-2)
        return [[a[0], a[1]] for a in ans]

    def _get_heatmap_peaks(self, approx_points):
        weights = self._calculate_normalized_weights(approx_points[:, 0])
        histogram2d_90deg_clockwise, _, _ = np.histogram2d(np.array(approx_points)[:, 1], np.array(approx_points)[:, 2], weights=weights, density=True, range=[[0, 8], [0, 5]],
                                                           bins=self._get_number_of_bins())
        histogram2d = np.rot90(histogram2d_90deg_clockwise)
        heatmap = gaussian_filter(histogram2d, sigma=1)
        threshold = np.quantile(heatmap.flatten(), 0.95)
        masked_heatmap = np.where(heatmap < threshold, 0, 1)
        labels, numL = label(masked_heatmap)
        label_indices = [(labels == i).nonzero() for i in range(1, numL + 1)]

        regions = []
        for label_index in label_indices:
            region = np.array(label_index).transpose()
            hull = self._get_convex_hull(region)
            hull = [[int(b) for b in a] for a in hull]
            regions.append(hull)
        return regions
