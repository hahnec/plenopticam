#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <info@christopherhahne.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


def find_centroid(centroids, ref_point, pitch, axis, pattern='hex', odd=True):

    # set indices for horizontal or vertical search respectively
    i, j = [1, 0] if axis == 1 else [0, 1]

    # find centroid given the pattern (note that "hexagonal shift alternation" is expected along vertical axis=0)
    if pattern == 'rec' or axis == 1:
        found_centroid = centroids[(centroids[:, i] > ref_point[i] + pitch[i]/2) &
                                   (centroids[:, i] < ref_point[i]+3*pitch[i]/2) &
                                   (centroids[:, j] > ref_point[j] - pitch[j]/2) &
                                   (centroids[:, j] < ref_point[j] + pitch[j]/2)].ravel()
    elif pattern == 'hex':
        if odd:
            found_centroid = centroids[(centroids[:, i] > ref_point[i] + pitch[i]/2) &
                                       (centroids[:, i] < ref_point[i]+3*pitch[i]/2) &
                                       (centroids[:, j] > ref_point[j]) &
                                       (centroids[:, j] < ref_point[j]+3*pitch[j]/4)].ravel()
        else:
            found_centroid = centroids[(centroids[:, i] > ref_point[i] + pitch[i]/2) &
                                       (centroids[:, i] < ref_point[i]+3*pitch[i]/2) &
                                       (centroids[:, j] < ref_point[j]) &
                                       (centroids[:, j] > ref_point[j]-3*pitch[j]/4)].ravel()
    else:
        raise Exception('pattern type not recognized.')

    return found_centroid


def find_centroid_backwards(centroids, ref_point, pitch, axis, pattern='hex', odd=True):

    # set indices for horizontal or vertical search respectively
    i, j = [1, 0] if axis == 1 else [0, 1]

    # find centroid given the pattern (note that "hexagonal shift alternation" is expected along vertical axis=0)
    if pattern == 'rec' or axis == 1:
        found_centroid = centroids[(centroids[:, i] < ref_point[i] - pitch[i]/2) &
                                   (centroids[:, i] > ref_point[i]-3*pitch[i]/2) &
                                   (centroids[:, j] > ref_point[j] - pitch[j]/2) &
                                   (centroids[:, j] < ref_point[j] + pitch[j]/2)].ravel()
    elif pattern == 'hex':
        if odd:
            found_centroid = centroids[(centroids[:, i] < ref_point[i] - pitch[i]/2) &
                                       (centroids[:, i] > ref_point[i]-3*pitch[i]/2) &
                                       (centroids[:, j] > ref_point[j]) &
                                       (centroids[:, j] < ref_point[j]+3*pitch[j]/4)].ravel()
        else:
            found_centroid = centroids[(centroids[:, i] < ref_point[i] - pitch[i]/2) &
                                       (centroids[:, i] > ref_point[i]-3*pitch[i]/2) &
                                       (centroids[:, j] < ref_point[j]) &
                                       (centroids[:, j] > ref_point[j]-3*pitch[j]/4)].ravel()
    else:
        raise Exception('pattern type not recognized.')

    return found_centroid
