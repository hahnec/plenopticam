# local imports
from plenopticam import misc
from plenopticam.cfg import constants as c
from plenopticam.lfp_aligner.lfp_global_resampler import LfpGlobalResampler
from plenopticam.lfp_aligner.lfp_local_resampler import LfpLocalResampler

# external libs
import os
import pickle


class LfpResampler(LfpLocalResampler, LfpGlobalResampler):

    def __init__(self, *args, **kwargs):
        super(LfpResampler, self).__init__(*args, **kwargs)

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Light-field alignment', self.cfg.params[self.cfg.opt_prnt])

        # global resampling
        if self.cfg.params[self.cfg.smp_meth] == 'global' or not self.cfg.params[self.cfg.smp_meth]:
            try:
                self.global_resampling()
            except ImportError:
                self.cfg.params[self.cfg.smp_meth] = 'local'
                self.sta.status_msg('Use local resampling due to ImportError', self.cfg.params[self.cfg.opt_prnt])

        # local resampling
        if self.cfg.params[self.cfg.smp_meth] == 'local':
            self.local_resampling()

        # unrecognized resampling method
        if not self.cfg.params[self.cfg.smp_meth] in c.SMPL_METH and self.cfg.params[self.cfg.smp_meth]:
            self.sta.status_msg('Resampling method %s unrecognized.' % self.cfg.params[self.cfg.smp_meth],
                                self.cfg.params[self.cfg.opt_prnt])
            self.sta.interrupt = True

        # save aligned image to hard drive
        self._write_lfp_align()

        return True

    def _write_lfp_align(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # print status
        self.sta.status_msg('Save aligned light-field', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # convert to 16bit unsigned integer
        self._lfp_img_align = misc.Normalizer(self._lfp_img_align).uint16_norm()

        # create output data folder
        misc.mkdir_p(self.cfg.exp_path, self.cfg.params[self.cfg.opt_prnt])

        try:
            # write aligned light field as pickle file to avoid re-calculation
            with open(os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl'), 'wb') as f:
                pickle.dump(self._lfp_img_align, f)
        except pickle.UnpicklingError:
            # print status and interrupt process
            fname = os.path.join(self.cfg.exp_path, 'lfp_img_align.pkl')
            self.sta.status_msg('Pickle file may be corrupted %s' % fname, self.cfg.params[self.cfg.opt_prnt])
            self.sta.error = True

        if self.cfg.params[self.cfg.opt_dbug]:
            misc.save_img_file(self._lfp_img_align, os.path.join(self.cfg.exp_path, 'lfp_img_align.tiff'))

        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])
