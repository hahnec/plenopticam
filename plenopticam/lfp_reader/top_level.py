# local imports
from plenopticam import misc
from plenopticam.misc.errors import LfpTypeError, PlenopticamError
from plenopticam.lfp_reader.lfp_decoder import LfpDecoder

import os

SUPP_FILE_EXT = ('.raw', '.lfp', '.lfr') + tuple('.c.' + str(num) for num in (0, 1, 2, 3))

class LfpReader(object):

    def __init__(self, cfg=None, sta=None, lfp_path=None):

        # input and output variables
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variables
        self._lfp_path = lfp_path if lfp_path is not None else cfg.params[cfg.lfp_path]

        # output variables
        self._lfp_img = None
        self._wht_img = None

    def main(self):

        if self._lfp_path.lower().endswith(SUPP_FILE_EXT):

            # filename and file path from previously decoded data
            dp = os.path.splitext(self._lfp_path)[0]
            fn = os.path.basename(dp)+'.tiff'
            fp = os.path.join(dp, fn)

            # load previously generated tiff if present
            if os.path.exists(fp):
                try:
                    self._lfp_img = misc.load_img_file(fp)
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
                        if self._lfp_path.lower().endswith(SUPP_FILE_EXT[1:]):
                            # LFC type decoding
                            obj.decode_lfc()
                            self.cfg.save_json(os.path.join(dp, os.path.basename(dp)+'.json'), json_dict=obj.json_dict)
                        elif self._lfp_path.lower().endswith(SUPP_FILE_EXT[0]):
                            # raw type decoding
                            obj.decode_raw()
                        self._lfp_img = obj.rgb_img
                        del obj

                        # save bayer image as file
                        misc.save_img_file(misc.Normalizer(self._lfp_img).uint16_norm(), fp, type='tiff')

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

            try:
                # try to load json file (if present)
                json_dict = self.cfg.load_json(self._lfp_path)
                self.cfg.lfpimg = LfpDecoder.filter_json(json_dict)
            except:
                pass

        # write json file
        self.cfg.save_params()

        return True

    @property
    def lfp_img(self):
        return self._lfp_img
