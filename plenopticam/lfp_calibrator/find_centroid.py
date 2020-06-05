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


def find_centroid(centroids, ref_point, pitch, axis, pattern='hex', odd=True, e=3):

    # set indices for horizontal or vertical search respectively
    i, j = [1, 0] if axis == 1 else [0, 1]

    # consider hexagonal shift alternation which is expected along vertical axis=0
    h, g = [1, 1] if pattern == 'rec' or axis == 1 else [0, e/2] if odd else [e/2, 0]

    # find centroid given the pattern
    found_centroid = centroids[(centroids[:, i] > ref_point[i] + pitch[i]/2) &
                               (centroids[:, i] < ref_point[i]+e*pitch[i]/2) &
                               (centroids[:, j] > ref_point[j]-h*pitch[j]/2) &
                               (centroids[:, j] < ref_point[j]+g*pitch[j]/2)].ravel()

    return found_centroid


def find_centroid_backwards(centroids, ref_point, pitch, axis, pattern='hex', odd=True, e=3):

    # set indices for horizontal or vertical search respectively
    i, j = [1, 0] if axis == 1 else [0, 1]

    # consider hexagonal shift alternation which is expected along vertical axis=0
    h, g = [1, 1] if pattern == 'rec' or axis == 1 else [0, e/2] if odd else [e/2, 0]

    # find centroid given the pattern (note that "hexagonal shift alternation" is expected along vertical axis=0)
    found_centroid = centroids[(centroids[:, i] < ref_point[i] - pitch[i]/2) &
                               (centroids[:, i] > ref_point[i]-e*pitch[i]/2) &
                               (centroids[:, j] > ref_point[j]-h*pitch[j]/2) &
                               (centroids[:, j] < ref_point[j]+g*pitch[j]/2)].ravel()

    return found_centroid
