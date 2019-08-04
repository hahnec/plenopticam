import numpy as np

from plenopticam.misc import Normalizer
from plenopticam.lfp_extractor import LfpViewpoints, LfpExporter
from plenopticam.lfp_extractor.lfp_colors import ContrastHandler, LfpColors

class LfpRearranger(LfpViewpoints):

    def __init__(self, lfp_img_align=None, *args, **kwargs):
        super(LfpRearranger, self).__init__(*args, **kwargs)

        self._lfp_img_align = Normalizer(lfp_img_align).uint16_norm() if lfp_img_align is not None else None

    def var_init(self):

        # initialize output image array
        if len(self._lfp_img_align.shape) == 3:
            m, n, p = self._lfp_img_align.shape
        else:
            m, n, p = (self._lfp_img_align.shape[0], self._lfp_img_align.shape[1], 1)

        self._vp_img_arr = np.zeros([int(self._M), int(self._M), int(m/self._M), int(n/self._M), p])

    def main(self):

        # initialize basic light-field parameters
        self.var_init()

        # rearrange lightfield to viewpoint representation
        self.viewpoint_extraction()

        # remove pixel outliers
        # self.proc_vp_arr(correct_luma_outliers, msg='Remove pixel outliers')

        # contrast automation if option is set
        if self.cfg.params[self.cfg.opt_cont]:
            obj = ContrastHandler(vp_img_arr=self._vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.main()
            self._vp_img_arr = obj.vp_img_arr
            del obj

        # automatic white balance if option is set
        if self.cfg.params[self.cfg.opt_awb_]:
            obj = LfpColors(vp_img_arr=self._vp_img_arr, cfg=self.cfg, sta=self.sta)
            obj.main()
            self._vp_img_arr = obj.vp_img_arr
            del obj

        # write viewpoint data to hard drive
        if self.cfg.params[self.cfg.opt_view]:
            LfpExporter(vp_img_arr=self._vp_img_arr, cfg=self.cfg, sta=self.sta).write_viewpoint_data()

        # print status
        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

    def viewpoint_extraction(self):

        # initialize light-field variables
        self.var_init()

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