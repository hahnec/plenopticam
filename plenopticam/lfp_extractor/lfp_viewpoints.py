from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus

import numpy as np

class LfpViewpoints(object):

    def __init__(self, *args, **kwargs):

        self._vp_img_arr = kwargs['vp_img_arr'].astype('float64') if 'vp_img_arr' in kwargs else None
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()
        self._M = self.cfg.params[self.cfg.ptc_leng]

    @property
    def vp_img_arr(self):
        return self._vp_img_arr.copy() if self._vp_img_arr is not None else False

    @property
    def central_view(self):
        return self._vp_img_arr[self._M//2+1, self._M//2+1].copy() if self._vp_img_arr is not None else None

    def proc_vp_arr(self, fun, **kwargs):
        ''' process viewpoint images based on provided function handle and argument data '''

        msg = kwargs['msg'] if 'msg' in kwargs else 'Viewpoint process'

        self.sta.status_msg(msg, self.cfg.params[self.cfg.opt_dbug])

        args = [kwargs[key] for key in kwargs.keys() if key not in ('cfg', 'sta', 'msg')]

        try:
            for j in range(self._vp_img_arr.shape[0]):
                for i in range(self._vp_img_arr.shape[1]):

                    self._vp_img_arr[j, i, :, :, :] = fun(self._vp_img_arr[j, i, :, :, :], *args)

                    # progress update
                    percent = (j*self._vp_img_arr.shape[1]+i+1)/np.dot(*self._vp_img_arr.shape[:2])*100
                    self.sta.progress(percent, self.cfg.params[self.cfg.opt_dbug])

                # check interrupt status
                if self.sta.interrupt:
                    return False

        except:
            if len(self.vp_img_arr.shape) != 5:
                raise NotImplementedError

        return True
