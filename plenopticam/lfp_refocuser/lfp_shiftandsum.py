#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2017 Christopher Hahne <info@christopherhahne.de>

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

# local imports
from plenopticam import misc
from plenopticam.lfp_extractor.lfp_viewpoints import LfpViewpoints
from plenopticam.lfp_extractor.lfp_exporter import LfpExporter
from plenopticam.lfp_extractor.lfp_contrast import LfpContrast
from plenopticam.misc import GammaConverter

# external
import numpy as np


class LfpShiftAndSum(LfpViewpoints):

    def __init__(self, lfp_img=None, *args, **kwargs):
        super(LfpShiftAndSum, self).__init__(*args, **kwargs)

        # input variables
        self.lfp_img = lfp_img

        # validate refocusing range
        self.validate_range()

        # internal variables
        self._refo_stack = list()

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Compute refocused image stack', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # exclude views that lie outside max. radius for circular blur spots
        self.circular_view_aperture() if self.vp_img_arr is not None else None

        # do refocus computation based on provided method
        if self.vp_img_arr is not None:
            self.refo_from_vp()
        elif self.lfp_img is not None:
            if self.cfg.params[self.cfg.opt_refi]:
                self.refo_from_scratch_upsample()
            else:
                self.refo_from_scratch()

        self._refo_stack = np.asarray(self._refo_stack)

        # tbd
        self.all_in_focus()

        return True

    def refo_from_vp(self):
        """ computational refocusing based on viewpoint shift and integration """

        # print status
        self.sta.progress(0, self.cfg.params[self.cfg.opt_prnt])

        # initialize variables
        self._refo_stack = list()
        patch_len = self.cfg.params[self.cfg.ptc_leng]
        factor = self.cfg.params[self.cfg.ptc_leng] if self.cfg.params[self.cfg.opt_refi] else 1

        # divide intensity to prevent clipping in shift and sum process
        self._vp_img_arr /= patch_len

        # iterate through refocusing parameter a
        ran_refo = self.cfg.params[self.cfg.ran_refo]
        a_list = tuple([factor*a for a in ran_refo]) if self.cfg.params[self.cfg.opt_refi] else ran_refo
        for a in range(*a_list):

            overlap = abs(a) * (patch_len - 1)
            img_slice = np.zeros(np.append(np.array(self._vp_img_arr.shape[2:-1]) * factor + [overlap, overlap], 3))
            for j in range(patch_len):
                for i in range(patch_len):

                    # perform sub-pixel refinement if required
                    vp_img = misc.img_resize(self._vp_img_arr[j, i], factor) if factor > 1 else self._vp_img_arr[j, i]

                    # get viewpoint padding for each border
                    tb = (abs(a) * j, abs(a) * (patch_len - 1 - j))    # top, bottom
                    lr = (abs(a) * i, abs(a) * (patch_len - 1 - i))    # left, right

                    # flip padding for each axis if a is negative
                    pad_width = (tb, lr, (0, 0)) if a >= 0 else (tb[::-1], lr[::-1], (0, 0))

                    # shift viewpoint image and add its values to refocused image slice
                    img_slice = np.add(img_slice, np.pad(vp_img, pad_width, 'edge'))

                    # check interrupt status
                    if self.sta.interrupt:
                        return False

                    # print status
                    percentage = ((j*patch_len+i+1)/patch_len**2+a-a_list[0])/(a_list[-1]-a_list[0])*100
                    self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

            # crop refocused image for consistent image dimensions
            crop = int(overlap/2)
            final_img = img_slice[crop:-crop, crop:-crop, :] if (a != 0) else img_slice

            # write upscaled version to hard drive
            if self.cfg.params[self.cfg.opt_refi]:
                upscale_img = LfpContrast().auto_hist_align(final_img.copy(), ref_img=final_img, opt=True)
                upscale_img = GammaConverter().srgb_conv(img=upscale_img)
                fname = np.round(a/patch_len, 2)
                LfpExporter(cfg=self.cfg, sta=self.sta).save_refo_slice(fname, upscale_img, string='upscale_')
                del upscale_img

            # spatially downscale image to original resolution (less memory required)
            final_img = misc.img_resize(final_img, 1./factor) if factor > 1 else final_img

            self._refo_stack.append(final_img)

        return True

    def refo_from_scratch(self):
        """ computational refocusing from aligned light field image """

        # print status
        self.sta.progress(0, self.cfg.params[self.cfg.opt_prnt])

        # initialize variables
        self._refo_stack = []
        patch_len = self.cfg.params[self.cfg.ptc_leng]
        if len(self.lfp_img.shape) == 3:
            m, n, P = self.lfp_img.shape
        else:
            m, n, P = self.lfp_img.shape[0], self.lfp_img.shape[1], 1
        J = int(n/patch_len)
        H = int(m/patch_len)
        c = int((patch_len-1)/2)

        # divide intensity to prevent clipping in shift and sum process
        img = self.lfp_img/patch_len

        # start synthesising a new refocused image
        a_range = np.arange(*self.cfg.params[self.cfg.ran_refo])
        for a in a_range:

            # initialize (reset) matrices for intermediate results
            overlap = abs(a) * (patch_len - 1)
            hor_refo = np.zeros([m, J + abs(a) * (patch_len-1), P])
            ver_refo = np.zeros([H + abs(a) * (patch_len-1), J + abs(a) * (patch_len-1), P])

            # horizontal shift and integrate
            for y in range(m):  # jump to next horizontal line
                for j in range(J + overlap):    # each increment is an integration for a refocused pixel
                    for i in range(-c, c+1):    # collects pixels to form refocused pixel
                        u_new = c + i
                        s_new = j + a * (c - i)
                        if a >= 0:
                            s_new -= overlap    # put output image to center
                        x = u_new + s_new * patch_len

                        # if index exceeds image boundaries, leave pixel empty
                        if (x >= 0) & (x < n):
                            fraction_hor = img[y, x, :]
                        else:
                            fraction_hor = np.zeros(P, dtype=self.lfp_img.dtype)

                        # add pixel to refocusing plane (integration)
                        hor_refo[y, j, :] += fraction_hor

            # vertical shift and integrate
            for h in range(H + overlap):
                for g in range(-c, c+1):
                    v_new = c + g
                    t_new = h + a * (c - g)
                    if a >= 0:
                        t_new -= overlap    # put output image to center
                    y = v_new + t_new * patch_len

                    # if index exceeds image boundaries, leave empty
                    if (y >= 0) & (y < m):
                        fraction_ver = hor_refo[y, :, :]
                    else:
                        fraction_ver = np.zeros([J + abs(a) * (patch_len - 1), P], dtype=self.lfp_img.dtype)

                    # add pixel to refocusing plane (integration)
                    ver_refo[h, :, :] += fraction_ver

            # crop refocused image for consistent image dimensions
            crop = int(overlap/2)
            final_img = ver_refo[crop:-crop, crop:-crop, :] if (a != 0) else ver_refo

            # append refocused image to stack
            self._refo_stack.append(final_img)

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((a-a_range[0]+1)/len(a_range)*100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def refo_from_scratch_upsample(self):

        # print status
        self.sta.progress(0, self.cfg.params[self.cfg.opt_prnt])

        # initialize variables
        self._refo_stack = []
        patch_len = self.cfg.params[self.cfg.ptc_leng]
        m, n, P = self.lfp_img.shape if len(self.lfp_img.shape) == 3 else self.lfp_img.shape[0], self.lfp_img.shape[1], 1
        factor = self.cfg.params[self.cfg.ptc_leng] if self.cfg.params[self.cfg.opt_refi] else 1

        img = self.lfp_img/patch_len    # divide to prevent clipping

        a_range = np.arange(*self.cfg.params[self.cfg.ran_refo])
        for a in a_range:

            # initialization
            overlap = abs(a) * (patch_len - 1)
            hor_refo = np.zeros([m, n + overlap, P])
            ver_refo = np.zeros([m + overlap, n + overlap, P])

            # consider negative shift
            negative_a = overlap if a < 0 else 0

            # horizontal shift and integration
            for y in range(m):
                for x in range(n):

                    # prevent from taking adjacent pixel being beyond image border
                    adj_idx = x + patch_len if x + patch_len < n else x

                    # interpolate values (spatial 1-D) of 2 adjacent pixels for all color channels
                    fraction_vec = np.array([np.ogrid[img[y, x, 0]:img[y, adj_idx, 0]:complex(patch_len)],
                                             np.ogrid[img[y, x, 1]:img[y, adj_idx, 1]:complex(patch_len)],
                                             np.ogrid[img[y, x, 2]:img[y, adj_idx, 2]:complex(patch_len)]]).T

                    # calculate horizontal shift coordinate
                    new_x = x + np.mod(x, patch_len)*(a-1) + negative_a

                    # add fractional values to refocused image row at shifted coordinate
                    hor_refo[y, new_x:new_x + patch_len, :] += fraction_vec

            # vertical shift and integration
            for y in range(m):

                # prevent from taking adjacent pixel being beyond image border
                adj_idx = y + patch_len if y + patch_len < m else y

                frac_vec = np.zeros([patch_len, n + overlap, P])
                for x in range(n + overlap):
                    # interpolate values (spatial 2-D) of 2 adjacent rows for all color channels
                    frac_vec[:, x] = np.array([np.ogrid[hor_refo[y, x, 0]:hor_refo[adj_idx, x, 0]:complex(patch_len)],
                                               np.ogrid[hor_refo[y, x, 1]:hor_refo[adj_idx, x, 1]:complex(patch_len)],
                                               np.ogrid[hor_refo[y, x, 2]:hor_refo[adj_idx, x, 2]:complex(patch_len)]]).T

                # calculate vertical shift coordinate
                new_y = y + np.mod(y, patch_len)*(a-1) + negative_a

                # add fractional values to refocused image at shifted coordinate
                ver_refo[new_y:new_y + patch_len, :, :] += frac_vec

            # crop refocused image for consistent image dimensions
            crop = int(overlap/2)
            final_img = ver_refo[crop:-crop, crop:-crop, :] if (a != 0) else ver_refo

            # write upscaled version to hard drive
            LfpExporter(cfg=self.cfg, sta=self.sta).save_refo_slice(a=a, refo_img=final_img)

            # spatially downscale image to original resolution (for less memory usage)
            final_img = misc.img_resize(final_img, 1./factor) if factor > 1 else final_img

            # append refocused image to stack
            self._refo_stack.append(final_img)

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((a-a_range[0]+1)/len(a_range)*100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def validate_range(self):

        n = len(self.cfg.params[self.cfg.ran_refo])
        if n == 2:
            one, two = self.cfg.params[self.cfg.ran_refo]
            if one >= two:
                self.cfg.params[self.cfg.ran_refo][1] = one + 1
                self.sta.status_msg('Refocusing range is not positive')
        else:
            raise ValueError("Refocusing range list is supposed to contain only two entries")

    def all_in_focus(self):
        pass

    @property
    def refo_stack(self):
        return self._refo_stack.copy()
