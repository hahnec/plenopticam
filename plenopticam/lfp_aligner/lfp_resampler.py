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


class LfpResampler(LfpMicroLenses):

    def __init__(self, *args, **kwargs):
        super(LfpResampler, self).__init__(*args, **kwargs)

        # interpolation method initialization
        method = kwargs['method'] if 'method' in kwargs else None
        method = method if method in ['nearest', 'linear', 'cubic', 'quintic'] else None
        method = 'cubic' if method == 'quintic' and self._M < 5 else method
        interp2d_method = functools.partial(interp2d, kind=method) if method is not None else interp2d
        self._flip = True if 'flip' in kwargs else False

        if method is None:
            self._interpol_method = RectBivariateSpline
        elif method == 'nearest':
            self._interpol_method = self._nearest
        else:
            self._interpol_method = interp2d_method

        # output variable
        self._lfp_out = np.zeros(self._lfp_img.shape) if self._lfp_img is not None else None

    def main(self):
        """ cropping micro images to square shape while interpolating around their detected center (MIC) """

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Light-field alignment', self.cfg.params[self.cfg.opt_prnt])

        # start resampling process (taking micro lens arrangement into account)
        if self.cfg.calibs[self.cfg.pat_type] == 'rec':
            self.resample_rec()
        elif self.cfg.calibs[self.cfg.pat_type] == 'hex':
            self.resample_hex()

        # save aligned image to hard drive
        self._write_lfp_align()

        return True

    def _write_lfp_align(self):

        # print status
        self.sta.status_msg('Save aligned light-field', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # convert to 16bit unsigned integer
        self._lfp_out = misc.Normalizer(self._lfp_out).uint16_norm()

        # create output data folder
        misc.mkdir_p(self.cfg.exp_path, self.cfg.params[self.cfg.opt_prnt])

        # write aligned light field as pickle file to avoid re-calculation
        with open(os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl'), 'wb') as f:
            pickle.dump(self._lfp_out, f)

        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(self._lfp_out, os.path.join(self.cfg.exp_path, 'lfp_img_align.tiff'))

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def _patch_align(self, window, mic):

        # initialize patch
        patch = np.zeros(window.shape)

        # verify patch shapes as wrong shapes cause crashes
        if window.shape[0] == self._M+2 and window.shape[1] == self._M+2:
            # iterate through color channels
            for p in range(self._DIMS[2]):

                fun = self._interpol_method(range(window.shape[1]), range(window.shape[0]), window[:, :, p])

                patch[:, :, p] = fun(np.arange(window.shape[1])+mic[1]-rint(mic[1]),
                                     np.arange(window.shape[0])+mic[0]-rint(mic[0]))
        else:
            self.sta.status_msg('Warning: chosen micro image size exceeds light-field borders')
            return np.zeros((self._M+2,)*2+(window.shape[2],))

        # flip patch to compensate for micro lens rotation
        patch = np.flip(patch, axis=(0, 1)) if self._flip else patch

        return patch

    def _nearest(self, range0, range1, window):

        def shift_win(shifted_range0, shifted_range1):
            range0 = np.round(shifted_range0).astype('int')
            range1 = np.round(shifted_range1).astype('int')
            return window[range0[0]:range0[-1]+1, range1[0]:range0[-1]+1]

        return shift_win

    def resample_rec(self):

        # initialize variables required for micro image resampling process
        self._lfp_out = np.zeros([self._LENS_Y_MAX * self._M, self._LENS_X_MAX * self._M, self._DIMS[2]])

        # iterate over each MIC
        for ly in range(self._LENS_Y_MAX):
            for lx in range(self._LENS_X_MAX):

                # find MIC by indices
                mic = self.get_coords_by_idx(ly=ly, lx=lx)

                # interpolate each micro image with its MIC as the center with consistent micro image size
                window = self._lfp_img[rint(mic[0])-self._C-1:rint(mic[0])+self._C+2,
                                       rint(mic[1])-self._C-1:rint(mic[1])+self._C+2]
                self._lfp_out[ly*self._M:(ly+1)*self._M, lx*self._M:(lx+1)*self._M] = \
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
        interp_stack = np.zeros([hex_stretch, self._M, self._M, self._DIMS[2]])
        self._lfp_out = np.zeros([self._LENS_Y_MAX * self._M, hex_stretch * self._M, self._DIMS[2]])

        # check if lower neighbor of upper left MIC is shifted to left or right
        hex_odd = self.get_hex_direction(self._CENTROIDS)

        # iterate over each MIC
        for ly in range(self._LENS_Y_MAX):
            for lx in range(self._LENS_X_MAX):

                # find MIC by indices
                mic = self.get_coords_by_idx(ly=ly, lx=lx)

                # interpolate each micro image with its MIC as the center and consistent micro image size
                window = self._lfp_img[rint(mic[0])-self._C-1:rint(mic[0])+self._C+2,
                                       rint(mic[1])-self._C-1:rint(mic[1])+self._C+2]
                patch_stack[lx, :, :] = self._patch_align(window, mic)[1:-1, 1:-1]

            # image stretch interpolation in x-direction to compensate for hex-alignment
            for y in range(self._M):
                for x in range(self._M):
                    for p in range(self._DIMS[2]):
                        # stack of micro images elongated in x-direction
                        interp_coords = np.linspace(0, self._LENS_X_MAX, int(np.round(self._LENS_X_MAX*2/np.sqrt(3))))+\
                                        .5*np.mod(ly+hex_odd, 2)
                        interp_stack[:, y, x, p] = np.interp(interp_coords, range(self._LENS_X_MAX), patch_stack[:, y, x, p])

            self._lfp_out[ly*self._M:(ly+1)*self._M, :] = \
                np.concatenate(interp_stack, axis=1).reshape((self._M, hex_stretch*self._M, self._DIMS[2]))

            # check interrupt status
            if self.sta.interrupt:
                return False

            # print progress status
            self.sta.progress((ly+1) / self._LENS_Y_MAX * 100, self.cfg.params[self.cfg.opt_prnt])

    @property
    def lfp_out(self):
        return self._lfp_out.copy()