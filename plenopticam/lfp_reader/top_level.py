# local imports
from plenopticam import misc
from plenopticam.misc.errors import LfpTypeError, PlenopticamError
from plenopticam.lfp_reader.lfp_decoder import LfpDecoder

import os

class LfpReader(object):

    def __init__(self, cfg=None, sta=None, lfp_path=None):

        # input and output variables
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variables
        self._lfp_path = lfp_path.lower() if lfp_path is not None else cfg.params[cfg.lfp_path].lower()

        # output variables
        self._lfp_img = None
        self._wht_img = None

    def main(self):

        if self._lfp_path.endswith(('.lfp', '.lfr', '.raw')):

            # load previously generated tiff if present
            if os.path.exists(self._lfp_path.split('.')[0]+'.tiff'):
                try:
                    self._lfp_img = misc.load_img_file(self._lfp_path.split('.')[0]+'.tiff')
                except TypeError as e:
                    self.sta.status_msg(e, self.cfg.params[self.cfg.opt_prnt])
                    self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])
                    raise LfpTypeError(e)
                except FileNotFoundError as e:
                    # print status
                    self.sta.status_msg('File {0} not found'.format(self._lfp_path), self.cfg.params[self.cfg.opt_prnt])
                    self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])
                    raise PlenopticamError(e)

            else:
                try:
                    # Lytro type decoding
                    with open(self._lfp_path, mode='rb') as file:

                        # print status
                        self.sta.status_msg('Decode Lytro image file', self.cfg.params[self.cfg.opt_prnt])
                        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

                        # LFC and raw type decoding
                        obj = LfpDecoder(file, self.cfg, self.sta)
                        if self._lfp_path.endswith(('.lfp', '.lfr')):
                            # LFC type decoding
                            obj.decode_lfc()
                        elif self._lfp_path.endswith('.raw'):
                            # raw type decoding
                            obj.decode_raw()
                        self._lfp_img = obj.rgb_img
                        del obj

                        # save bayer image as file (only in debug mode)
                        if self.cfg.params[self.cfg.opt_dbug]:
                            misc.save_img_file(misc.uint16_norm(self._lfp_img), file.name.split('.')[0]+'.tiff', type='tiff')

                        # print status
                        self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

                except FileNotFoundError as e:
                    # print status
                    self.sta.status_msg('File {0} not found'.format(self._lfp_path), self.cfg.params[self.cfg.opt_prnt])
                    self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])
                    raise PlenopticamError(e)
        else:
            try:
                # read and decode generic image file type
                self._lfp_img = misc.load_img_file(self._lfp_path)
            except TypeError as e:
                raise LfpTypeError(e)

            self.load_lfp_settings()

        # write json file
        self.cfg.save_params()

        return True

    @property
    def lfp_img(self):
        return self._lfp_img

    def load_lfp_settings(self):
        ''' load LFP json data for tiff images if file present '''
        try:
            import json
            json_path = self._lfp_path.split('.')[0]+'.json'
            with open(json_path, 'r') as f:
                json_dict = json.load(f)
                self.cfg.lfpimg = LfpDecoder.filter_json(json_dict)
        except:
            pass

        return True