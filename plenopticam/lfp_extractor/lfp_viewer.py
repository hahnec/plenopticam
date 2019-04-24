import numpy as np

#from plenopticam import misc
from plenopticam.lfp_extractor.lfp_exporter import export_viewpoints, gif_vp_img
from plenopticam.lfp_extractor.img_proc import *

class LfpViewer(object):

    def __init__(self, lfp_img_align, patch_len, cfg=None, sta=None):

        self._lfp_img_align = lfp_img_align
        self._patch_len = patch_len
        self.cfg = cfg
        self.sta = sta

        # initialize output image array
        if len(self._lfp_img_align.shape) == 3:
            m, n, p = self._lfp_img_align.shape
        else:
            m, n, p = (self._lfp_img_align.shape[0], self._lfp_img_align.shape[1], 1)
        self._vp_img_arr = np.zeros([int(patch_len), int(patch_len), int(m/patch_len), int(n/patch_len), p])

    def main(self):

        # print status
        self.sta.status_msg('Viewpoint extraction', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # convert to uint16
        self._lfp_img_align = misc.uint16_norm(self._lfp_img_align).astype('float32')

        # when viewpoint option is set
        if self.cfg.params[self.cfg.opt_view]:

            # extract viewpoints
            self.viewpoint_extraction()

            # remove pixel outliers (yields bad results at this stage)
            self._vp_img_arr = proc_vp_arr(correct_luma_outliers, self._vp_img_arr)

            # automatic contrast handling
            central_view = self._vp_img_arr[int((self._vp_img_arr.shape[0]-1)/2),
                                            int((self._vp_img_arr.shape[1]-1)/2), ...].copy()
            contrast, brightness = auto_contrast(central_view, p_lo=0.001, p_hi=0.999)
            self._vp_img_arr = proc_vp_arr(correct_contrast, self._vp_img_arr, contrast, brightness)

            if self.cfg.params[self.cfg.opt_awb_]:

                # print status
                self.sta.status_msg('Automatic white balance', self.cfg.params[self.cfg.opt_prnt])
                self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

                # simplest color balancing (similar to auto contrast in photoshop)
                #self._vp_img_arr = proc_vp_arr(contrast_per_channel, self._vp_img_arr)

                # robust awb
                gains = robust_awb(central_view)
                self._vp_img_arr = proc_vp_arr(correct_awb, self._vp_img_arr, gains)

                # color balance
                #sat_contrast, sat_brightness = auto_contrast(central_view, ch=1)
                #vp_img_arr = proc_vp_arr(correct_contrast, vp_img_arr, sat_contrast, sat_brightness, central_view.min(), central_view.max(), 1)

                # print status
                self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

            # print status
            self.sta.status_msg('Write viewpoint images', self.cfg.params[self.cfg.opt_prnt])
            self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

            # write viewpoint image files to hard drive
            export_viewpoints(self._vp_img_arr, self.cfg, type='png')

            # write
            img = misc.uint8_norm(self._vp_img_arr)
            gif_vp_img(img, duration=.1, fp=self.cfg.params[self.cfg.lfp_path].split('.')[0], fn='view_animation')

            # print status
            self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def viewpoint_extraction(self):

        # rearrange light field to multi-view image representation
        for j in range(self._patch_len):
            for i in range(self._patch_len):

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # extract viewpoint by pixel rearrangement
                self._vp_img_arr[j, i, :, :, :] = self._lfp_img_align[j::self._patch_len, i::self._patch_len, :]

                # print status
                percentage = (((j*self._patch_len+i+1)/self._patch_len**2)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    @property
    def vp_img_arr(self):
        return self._vp_img_arr.copy()