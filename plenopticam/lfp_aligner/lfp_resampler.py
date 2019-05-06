# local imports
from plenopticam import misc
from plenopticam.lfp_extractor.lfp_cropper import LfpCropper

# external libs
import numpy as np
import os
import pickle
from scipy.interpolate import interp2d#, RectBivariateSpline, griddata

class LfpResampler(object):

    def __init__(self, lfp_raw, cfg, sta=None, method='cubic'):

        # input variables
        self.lfp_raw = lfp_raw
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variables
        self._method = method

        # output variable
        self._lfp_out = np.zeros(lfp_raw.shape)

    def main(self):
        ''' cropping micro images to square shape while interpolating around their detected center (MIC) '''

        centroids = np.asarray(self.cfg.calibs[self.cfg.mic_list])
        patch_size = LfpCropper.pitch_max(self.cfg.calibs[self.cfg.mic_list])

        lens_y_max = int(max(centroids[:, 2]))
        lens_x_max = int(max(centroids[:, 3]))

        m, n, P = self.lfp_raw.shape if len(self.lfp_raw.shape) == 3 else (self.lfp_raw.shape[0], self.lfp_raw.shape[1], 1)

        # initialize variables required for micro image cropping process
        c = int((patch_size - 1)/2)

        # print status
        self.sta.status_msg('Light field alignment', self.cfg.params[self.cfg.opt_prnt])

        if self.cfg.calibs[self.cfg.pat_type] == 'rec':

            self._lfp_out = np.zeros([lens_y_max * patch_size, lens_x_max * patch_size, P])

            # iterate over each MIC
            for ly in range(lens_y_max):
                for lx in range(lens_x_max):

                    # find MIC by indices
                    curr_mic = centroids[(centroids[:, 3] == lx) & (centroids[:, 2] == ly), [0, 1]]

                    # interpolate each micro image with its MIC as the center with consistent micro image size
                    window = self.lfp_raw[int(curr_mic[0])-c-1:int(curr_mic[0])+c+2, int(curr_mic[1])-c-1:int(curr_mic[1])+c+2]
                    self._lfp_out[ly * patch_size:(ly+1) * patch_size, lx * patch_size:(lx+1) * patch_size] = \
                        self._patch_align(window, curr_mic, method=self._method)[1:-1, 1:-1]

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # print progress status for on console
                self.sta.progress((ly+1)/lens_y_max*100, self.cfg.params[self.cfg.opt_prnt])

        elif self.cfg.calibs[self.cfg.pat_type] == 'hex':

            patch_stack = np.zeros([lens_x_max, patch_size, patch_size, P])
            hex_stretch = int(np.round(2*lens_x_max / np.sqrt(3)))
            interpol_stack = np.zeros([hex_stretch, patch_size, patch_size, P])
            self._lfp_out = np.zeros([lens_y_max * patch_size, hex_stretch * patch_size, P])

            # check if lower neighbor of upper left MIC is shifted to left or right
            hex_odd = self._get_hex_direction(centroids)

            # iterate over each MIC
            for ly in range(lens_y_max):
                for lx in range(lens_x_max):

                    # find MIC by indices
                    curr_mic = centroids[(centroids[:, 3] == lx) & (centroids[:, 2] == ly), [0, 1]]

                    # interpolate each micro image with its MIC as the center with consistent micro image size
                    window = self.lfp_raw[int(curr_mic[0])-c-1:int(curr_mic[0])+c+2, int(curr_mic[1])-c-1: int(curr_mic[1])+c+2]
                    patch_stack[lx, :, :] = self._patch_align(window, curr_mic, method=self._method)[1:-1, 1:-1]

                    # do interpolation of two adjacent micro images
                    if np.mod(ly+hex_odd, 2) and lx > 0:
                        patch_stack[lx-1, :, :, :] = (patch_stack[lx-1, :, :, :]+patch_stack[lx, :, :, :])/2.

                # image stretch interpolation in x-direction to compensate for hex-alignment
                for y in range(patch_size):
                    for x in range(patch_size):
                        for p in range(P):
                            # stack of micro images elongated in x-direction
                            interpol_vals = np.arange(hex_stretch)/hex_stretch*lens_x_max
                            interpol_stack[:, y, x, p] = np.interp(interpol_vals, range(lens_x_max), patch_stack[:, y, x, p])

                self._lfp_out[ly*patch_size:ly*patch_size+patch_size, :] = np.concatenate(interpol_stack, axis=1).reshape((patch_size, hex_stretch * patch_size, P))

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # print progress status
                self.sta.progress((ly+1)/lens_y_max*100, self.cfg.params[self.cfg.opt_prnt])

        elif self.cfg.calibs[self.cfg.pat_type] == 'hex_alt':

            hex_stretch = int(np.round(2*lens_x_max / np.sqrt(3)))
            interpol_stack = np.zeros([hex_stretch, patch_size, patch_size, P])
            self._lfp_out = np.zeros([lens_y_max * patch_size, hex_stretch * patch_size, P])

            # get interpolation weights according to micro lens arrangement
            tb_weight = 1/(1+np.sqrt(3)) / 2
            lr_weight = np.sqrt(3)/(1+np.sqrt(3)) / 2

            # check if lower neighbor of upper left MIC is shifted to left or right
            hex_odd = self._get_hex_direction(centroids)

            # iterate over each MIC
            for ly in range(lens_y_max):

                patch_stack = np.zeros([2*lens_x_max+1, patch_size, patch_size, P])

                for lx in range(lens_x_max):

                    # interpolate each micro image with its MIC as the center with consistent micro image size
                    r_mic = centroids[(centroids[:, 3] == lx) & (centroids[:, 2] == ly), [0, 1]]
                    r_win = self.lfp_raw[int(r_mic[0])-c-1:int(r_mic[0])+c+2, int(r_mic[1])-c-1: int(r_mic[1])+c+2, :]
                    r = self._patch_align(r_win, r_mic, method=self._method)[1:-1, 1:-1, :]

                    patch_stack[2*lx, :, :, :] = r

                    # do bilinear interpolation of adjacent micro images (do linear if at borders)
                    if lx > 0:

                        l = patch_stack[2*lx-2, :, :, :]
                        if ly > 0 and lens_y_max-ly > 0:
                            # interpolate upper adjacent patch while considering hex shift alignment (take same column if row "left-handed", next otherwise)
                            t_mic = centroids[(centroids[:, 3] == lx-np.mod(ly+hex_odd, 2)) & (centroids[:, 2] == ly-1), [0, 1]]
                            t_win = self.lfp_raw[int(t_mic[0])-c-1:int(t_mic[0])+c+2, int(t_mic[1])-c-1: int(t_mic[1])+c+2, :]
                            t = self._patch_align(t_win, t_mic, method=self._method)[1:-1, 1:-1, :]

                            b_mic = centroids[(centroids[:, 3] == lx-np.mod(ly+hex_odd, 2)) & (centroids[:, 2] == ly+1), [0, 1]]
                            b_win = self.lfp_raw[int(b_mic[0])-c-1:int(b_mic[0])+c+2, int(b_mic[1])-c-1: int(b_mic[1])+c+2, :]
                            b = self._patch_align(b_win, b_mic, method=self._method)[1:-1, 1:-1, :]

                            patch_stack[2*lx-1, :, :, :] = t*tb_weight + b*tb_weight + l*lr_weight + r*lr_weight
                        else:
                            patch_stack[2*lx-1, :, :, :] = (l+r)/2.

                # shift patch_stack by adding one patch to the front to compensate for hexagonal structure
                if np.mod(ly+hex_odd-1, 2):  # shift first and every other row to left if "they are right-handed"
                    patch_stack[1:, :, :, :] = patch_stack[:-1, :, :, :]
                    patch_stack[0, :, :, :] = np.zeros_like(patch_stack[0, :, :, :])

                # image stretch interpolation in x-direction to compensate for hex-alignment
                for y in range(patch_size):
                    for x in range(patch_size):
                        for p in range(P):
                            # stack of micro images shrinked in x-direction
                            interpol_vals = np.arange(hex_stretch) / hex_stretch * (2*lens_x_max+1)
                            interpol_stack[:, y, x, p] = np.interp(interpol_vals, range(2*lens_x_max+1), patch_stack[:, y, x, p])

                self._lfp_out[ly*patch_size:ly*patch_size+patch_size, :] = np.concatenate(interpol_stack, axis=1).reshape((patch_size, hex_stretch*patch_size, P))

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # print progress status
                self.sta.progress((ly+1)/lens_y_max*100, self.cfg.params[self.cfg.opt_prnt])

        self._write_lfp_align()

        return True

    def _write_lfp_align(self):

        # convert to 16bit unsigned integer
        self._lfp_out = misc.uint16_norm(self._lfp_out)

        out_path = self.cfg.params[self.cfg.lfp_path].split('.')[0]

        # create output data folder
        misc.mkdir_p(self.cfg.params[self.cfg.lfp_path].split('.')[0], self.cfg.params[self.cfg.opt_prnt])

         # write aligned light field as pickle file to avoid recalculation
        pickle.dump(self._lfp_out, open(os.path.join(out_path, 'lfp_img_align.pkl'), 'wb'))

        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(self._lfp_out, os.path.join(out_path, 'lfp_img_align.tiff'))

    @staticmethod
    def _patch_align(window, mic, method='linear'):

        # get window dimensions
        m, n, P = window.shape if len(window.shape) == 3 else (window.shape[0], window.shape[1], 1)

        # create new axis (for colour channel) if window is monochromatic 2D image (prevents error)
        window = window[..., np.newaxis] if P == 1 else window

        output = np.zeros(window.shape)
        for p in range(P):
            # careful: interp2d() takes x first and y second
            fun = interp2d(range(n), range(m), window[:, :, p], kind=method, copy=False)
            output[:, :, p] = fun(np.arange(n)+mic[1]-int(mic[1]), np.arange(m)+mic[0]-int(mic[0]))

            # treatment of interpolated values being below or above original extrema
            output[:, :, p][output[:, :, p] < window.min()] = window.min()
            output[:, :, p][output[:, :, p] > window.max()] = window.max()

        return output

    @staticmethod
    def _get_hex_direction(centroids):
        """ check if lower neighbor of upper left MIC is shifted to left or right in hex grid """

        # get upper left MIC
        first_mic = centroids[(centroids[:, 3] == 0) & (centroids[:, 2] == 0), [0, 1]]

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
