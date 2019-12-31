# local imports
from plenopticam import misc
from plenopticam.misc.type_checks import rint
from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses

# external libs
import numpy as np
import os
import pickle
import functools
from scipy.interpolate import interp2d, RectBivariateSpline
from scipy.ndimage import shift


class LfpResampler(LfpMicroLenses):

    def __init__(self, *args, **kwargs):
        super(LfpResampler, self).__init__(*args, **kwargs)

        # interpolation method initialization
        method = kwargs['method'] if 'method' in kwargs else None
        method = method if method in ['linear', 'cubic', 'quintic'] else None
        interp2d_method = functools.partial(interp2d, kind=method) if method is not None else interp2d
        self._interpol_method = RectBivariateSpline if method is None else interp2d_method

        # output variable
        if self._lfp_img is not None:
            self._lfp_out = np.zeros(self._lfp_img.shape)

    def main(self):
        ''' cropping micro images to square shape while interpolating around their detected center (MIC) '''

        # print status
        self.sta.status_msg('Light field alignment', self.cfg.params[self.cfg.opt_prnt])

        # start resampling process (taking micro lens arrangement into account)
        if self.cfg.calibs[self.cfg.pat_type] == 'rec':
            self.resample_rec()
        elif self.cfg.calibs[self.cfg.pat_type] == 'hex':
            self.resample_hex()
        elif self.cfg.calibs[self.cfg.pat_type] == 'hex_alt':
            self.resample_hex_alt()

        # save aligned image to hard drive
        self._write_lfp_align()

        return True

    def _write_lfp_align(self):

        # convert to 16bit unsigned integer
        self._lfp_out = misc.Normalizer(self._lfp_out).uint16_norm()

        # create output data folder
        misc.mkdir_p(self.cfg.exp_path, self.cfg.params[self.cfg.opt_prnt])

        # write aligned light field as pickle file to avoid recalculation
        with open(os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl'), 'wb') as f:
            pickle.dump(self._lfp_out, f)

        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(self._lfp_out, os.path.join(self.cfg.exp_path, 'lfp_img_align.tiff'))

    def _patch_align(self, window, mic):

        # initialize patch
        patch = np.zeros(window.shape)

        for p in range(window.shape[2]):
#
            fun = self._interpol_method(range(window.shape[1]), range(window.shape[0]), window[:, :, p])
#
            patch[:, :, p] = fun(np.arange(window.shape[1])+mic[1]-rint(mic[1]),
                                 np.arange(window.shape[0])+mic[0]-rint(mic[0]))

        #shift_coords = (mic[1]-rint(mic[1]), mic[0]-rint(mic[0]), 0)
        #patch = shift(window, shift=shift_coords) #tbt

        return patch

    @staticmethod
    def _get_hex_direction(centroids):
        """ check if lower neighbor of upper left MIC is shifted to left or right in hex grid """

        # get upper left MIC
        first_mic = centroids[(centroids[:, 2] == 0) & (centroids[:, 3] == 0), [0, 1]]

        # retrieve horizontal micro image shift (to determine search range borders)
        central_row_idx = int(centroids[:, 3].max()/2)
        mean_pitch = np.mean(np.diff(centroids[centroids[:, 3] == central_row_idx, 0]))

        # try to find MIC in lower left range (considering hexagonal order)
        found_mic = centroids[(centroids[:, 0] > first_mic[0]+mean_pitch/2) &
                              (centroids[:, 0] < first_mic[0]+3*mean_pitch/2) &
                              (centroids[:, 1] < first_mic[1]) &
                              (centroids[:, 1] > first_mic[1]-3*mean_pitch/4)].ravel()

        # true if MIC of next row lies on the right (false otherwise)
        hex_odd = True if found_mic.size == 0 else False

        return hex_odd

    @property
    def lfp_out(self):
        return self._lfp_out.copy()

    def resample_rec(self):

        # initialize variables required for micro image resampling process
        self._lfp_out = np.zeros([self._LENS_Y_MAX * self._M, self._LENS_X_MAX * self._M, self._DIMS[2]])

        # iterate over each MIC
        for ly in range(self._LENS_Y_MAX):
            for lx in range(self._LENS_X_MAX):

                # find MIC by indices
                mic = self.get_coords_by_idx(ly=ly, lx=lx)

                # interpolate each micro image with its MIC as the center with consistent micro image size
                window = self._lfp_img[rint(mic[0]) - self._C - 1:rint(mic[0]) + self._C + 2, rint(mic[1]) - self._C - 1:rint(mic[1]) + self._C + 2]
                self._lfp_out[ly * self._M:(ly + 1) * self._M, lx * self._M:(lx + 1) * self._M] = \
                    self._patch_align(window, mic)[1:-1, 1:-1]

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status for on console
            self.sta.progress((ly + 1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])

        return True

    def resample_hex(self):

        # initialize variables required for micro image resampling process
        patch_stack = np.zeros([self._LENS_X_MAX, self._M, self._M, self._DIMS[2]])
        hex_stretch = int(np.round(2 * self._LENS_X_MAX / np.sqrt(3)))
        interpol_stack = np.zeros([hex_stretch, self._M, self._M, self._DIMS[2]])
        self._lfp_out = np.zeros([self._LENS_Y_MAX * self._M, hex_stretch * self._M, self._DIMS[2]])

        # check if lower neighbor of upper left MIC is shifted to left or right
        hex_odd = self._get_hex_direction(self._CENTROIDS)

        # iterate over each MIC
        for ly in range(self._LENS_Y_MAX):
            for lx in range(self._LENS_X_MAX):

                # find MIC by indices
                mic = self.get_coords_by_idx(ly=ly, lx=lx)

                # interpolate each micro image with its MIC as the center and consistent micro image size
                window = self._lfp_img[rint(mic[0])-self._C-1:rint(mic[0])+self._C+2, rint(mic[1])-self._C-1:rint(mic[1])+self._C+2]
                patch_stack[lx, :, :] = self._patch_align(window, mic)[1:-1, 1:-1]

                # do interpolation of two adjacent micro images
                if np.mod(ly + hex_odd, 2) and lx > 0:
                    patch_stack[lx - 1, :, :, :] = (patch_stack[lx - 1, :, :, :] + patch_stack[lx, :, :, :]) / 2.

            # image stretch interpolation in x-direction to compensate for hex-alignment
            for y in range(self._M):
                for x in range(self._M):
                    for p in range(self._DIMS[2]):
                        # stack of micro images elongated in x-direction
                        interpol_vals = np.arange(hex_stretch) / hex_stretch * self._LENS_X_MAX
                        interpol_stack[:, y, x, p] = np.interp(interpol_vals, range(self._LENS_X_MAX), patch_stack[:, y, x, p])

            self._lfp_out[ly*self._M:ly*self._M+self._M, :] = \
                np.concatenate(interpol_stack, axis=1).reshape((self._M, hex_stretch * self._M, self._DIMS[2]))

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((ly + 1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])

    def resample_hex_alt(self):

        # initialize variables required for micro image resampling process
        hex_stretch = int(np.round(2 * self._LENS_X_MAX / np.sqrt(3)))
        interpol_stack = np.zeros([hex_stretch, self._M, self._M, self._DIMS[2]])
        self._lfp_out = np.zeros([self._LENS_Y_MAX * self._M, hex_stretch * self._M, self._DIMS[2]])

        # get interpolation weights according to micro lens arrangement
        tb_weight = 1 / (1 + np.sqrt(3)) / 2
        lr_weight = np.sqrt(3) / (1 + np.sqrt(3)) / 2

        # check if lower neighbor of upper left MIC is shifted to left or right
        hex_odd = self._get_hex_direction(self._CENTROIDS)

        # iterate over each MIC
        for ly in range(self._LENS_Y_MAX):

            patch_stack = np.zeros([2 * self._LENS_X_MAX + 1, self._M, self._M, self._DIMS[2]])

            for lx in range(self._LENS_X_MAX):

                # interpolate each micro image with its MIC as the center with consistent micro image size
                r_mic = self._CENTROIDS[(self._CENTROIDS[:, 3] == lx) & (self._CENTROIDS[:, 2] == ly), [0, 1]]
                r_win = self._lfp_img[int(r_mic[0]) - self._C - 1:int(r_mic[0]) + self._C + 2,
                        int(r_mic[1])-self._C-1:int(r_mic[1])+self._C+2, :]
                r = self._patch_align(r_win, r_mic)[1:-1, 1:-1, :]

                patch_stack[2 * lx, :, :, :] = r

                # do interpolation of adjacent micro images (do linear if at borders)
                if lx > 0:

                    l = patch_stack[2 * lx - 2, :, :, :]
                    if ly > 0 and self._LENS_Y_MAX - ly > 0:
                        # interpolate upper adjacent patch while considering hex shift alignment (take same column if row "left-handed", next otherwise)
                        t_mic = self._CENTROIDS[
                            (self._CENTROIDS[:, 3] == lx - np.mod(ly + hex_odd, 2)) & (self._CENTROIDS[:, 2] == ly - 1), [0, 1]]
                        t_win = self._lfp_img[int(t_mic[0]) - self._C - 1:int(t_mic[0]) + self._C + 2,
                                int(t_mic[1])-self._C-1:int(t_mic[1])+self._C+2, :]
                        t = self._patch_align(t_win, t_mic)[1:-1, 1:-1, :]

                        b_mic = self._CENTROIDS[
                            (self._CENTROIDS[:, 3] == lx - np.mod(ly + hex_odd, 2)) & (self._CENTROIDS[:, 2] == ly + 1), [0, 1]]
                        b_win = self._lfp_img[int(b_mic[0]) - self._C - 1:int(b_mic[0]) + self._C + 2,
                                int(b_mic[1])-self._C-1:int(b_mic[1])+self._C+2, :]
                        b = self._patch_align(b_win, b_mic)[1:-1, 1:-1, :]

                        patch_stack[2 * lx - 1, :, :, :] = t * tb_weight + b * tb_weight + l * lr_weight + r * lr_weight
                    else:
                        patch_stack[2 * lx - 1, :, :, :] = (l + r) / 2.

            # shift patch_stack by adding one patch to the front to compensate for hexagonal structure
            if np.mod(ly + hex_odd - 1, 2):  # shift first and every other row to left if "they are right-handed"
                patch_stack[1:, :, :, :] = patch_stack[:-1, :, :, :]
                patch_stack[0, :, :, :] = np.zeros_like(patch_stack[0, :, :, :])

            # image stretch interpolation in x-direction to compensate for hex-alignment
            for y in range(self._M):
                for x in range(self._M):
                    for p in range(self._DIMS[2]):
                        # stack of micro images shrinked in x-direction
                        interpol_vals = np.arange(hex_stretch) / hex_stretch * (2 * self._LENS_X_MAX + 1)
                        interpol_stack[:, y, x, p] = np.interp(interpol_vals, range(2 * self._LENS_X_MAX + 1),
                                                               patch_stack[:, y, x, p])

            self._lfp_out[ly * self._M:ly * self._M + self._M, :] = \
                np.concatenate(interpol_stack, axis=1).reshape((self._M, hex_stretch * self._M, self._DIMS[2]))

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((ly + 1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])
