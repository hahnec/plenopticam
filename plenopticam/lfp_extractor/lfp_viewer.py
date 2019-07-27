
from plenopticam.lfp_extractor.lfp_exporter import export_viewpoints, export_thumbnail, gif_vp_img
from plenopticam.lfp_extractor.img_proc import *

import numpy as np
import os

class LfpViewer(object):

    def __init__(self, lfp_img_align, cfg=None, sta=None):

        self._lfp_img_align = lfp_img_align
        self.cfg = cfg
        self.sta = sta

        self.var_init()

    def var_init(self):

        self._M =self.cfg.params[self.cfg.ptc_leng]

        # initialize output image array
        if len(self._lfp_img_align.shape) == 3:
            m, n, p = self._lfp_img_align.shape
        else:
            m, n, p = (self._lfp_img_align.shape[0], self._lfp_img_align.shape[1], 1)

        self._vp_img_arr = np.zeros([int(self._M), int(self._M), int(m/self._M), int(n/self._M), p])

    def main(self):

        # convert to uint16
        self._lfp_img_align = misc.uint16_norm(self._lfp_img_align).astype('float32')

        # when viewpoint option is set
        if self.cfg.params[self.cfg.opt_view]:

            # extract viewpoints
            self.viewpoint_extraction()

            # remove pixel outliers
            #self._vp_img_arr = proc_vp_arr(correct_luma_outliers, self._vp_img_arr, cfg=self.cfg, sta=self.sta, msg='Remove pixel outliers')

            # automatic contrast handling
            central_view = self._vp_img_arr[int((self._vp_img_arr.shape[0]-1)/2),
                                            int((self._vp_img_arr.shape[1]-1)/2), ...].copy()
            contrast, brightness = auto_contrast(central_view, p_lo=0.001, p_hi=0.999)
            self._vp_img_arr = proc_vp_arr(correct_contrast, self._vp_img_arr, cfg=self.cfg, sta=self.sta,
                                           msg='Contrast correction', c=contrast, b=brightness)

            # automatic white balance if option is set
            if self.cfg.params[self.cfg.opt_awb_]:

                # print status
                self.sta.status_msg('Automatic white balance', self.cfg.params[self.cfg.opt_prnt])
                self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

                # simplest color balancing (similar to auto contrast in photoshop)
                #self._vp_img_arr = proc_vp_arr(contrast_per_channel, self._vp_img_arr)

                # robust awb
                gains = robust_awb(central_view)
                self._vp_img_arr = proc_vp_arr(correct_awb, self._vp_img_arr, g=gains)

                # color balance
                #sat_contrast, sat_brightness = auto_contrast(central_view, ch=1)
                #vp_img_arr = proc_vp_arr(correct_contrast, vp_img_arr, sat_contrast, sat_brightness, central_view.min(), central_view.max(), 1)

                # print status
                self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

            # print status
            self.sta.status_msg('Write viewpoint images', self.cfg.params[self.cfg.opt_prnt])
            self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

            # write central view as thumbnail image
            export_thumbnail(self._vp_img_arr, self.cfg, type='png')

            # write viewpoint image files to hard drive
            export_viewpoints(self._vp_img_arr, self.cfg, type='png')

            # write
            img = misc.uint8_norm(self._vp_img_arr)
            fn = 'view_animation_'+str(self.cfg.params[self.cfg.ptc_leng])+'px'
            gif_vp_img(img, duration=.1, fp=os.path.splitext(self.cfg.params[self.cfg.lfp_path])[0], fn=fn)

            # print status
            self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def viewpoint_extraction(self):

        # print status
        self.sta.status_msg('Viewpoint extraction', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # rearrange light field to multi-view image representation
        for j in range(self._M):
            for i in range(self._M):

                # check interrupt status
                if self.sta.interrupt:
                    return False

                # extract viewpoint by pixel rearrangement
                self._vp_img_arr[j, i, :, :, :] = self._lfp_img_align[j::self._M, i::self._M, :]

                # print status
                percentage = (((j*self._M+i+1)/self._M**2)*100)
                self.sta.progress(percentage, self.cfg.params[self.cfg.opt_prnt])

        return True

    @property
    def vp_img_arr(self):
        return self._vp_img_arr.copy()