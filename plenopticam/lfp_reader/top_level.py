#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <info@christopherhahne.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


# local imports
from plenopticam import misc
from plenopticam.misc.errors import LfpTypeError, PlenopticamError
from plenopticam.lfp_reader.lfp_decoder import LfpDecoder
from plenopticam.lfp_reader.constants import SUPP_FILE_EXT
from plenopticam.misc.gamma_converter import GammaConverter

import os


class LfpReader(object):

    def __init__(self, cfg=None, sta=None, lfp_path=None):

        # input and output variables
        self.cfg = cfg
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

        # internal variables
        self._lfp_path = lfp_path if lfp_path is not None else cfg.params[cfg.lfp_path]

        # output variables
        self._bay_img = None
        self._lfp_img = None
        self._json_dict = None

        # filename and file path from previously decoded data
        self.dp = os.path.splitext(self._lfp_path)[0]
        self.fn = os.path.basename(self.dp) + '.tiff'
        self.fp = os.path.join(self.dp, self.fn)

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        if self._lfp_path.lower().endswith(SUPP_FILE_EXT):

            try:
                self.decode_lytro_file()
            except FileNotFoundError:
                # print status
                self.sta.status_msg('{0} not found'.format(os.path.basename(self._lfp_path)), self.cfg.params[self.cfg.opt_prnt])
                self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])
                self.sta.error = True
            except Exception as e:
                # unrecognized LFP file type
                if not self._json_dict:
                    raise LfpTypeError(e)
                else:
                    raise PlenopticamError(e)
        else:
            try:
                # read and decode generic image file type
                self._lfp_img = misc.load_img_file(self._lfp_path)
                # inverse sRGB conversion
                self._lfp_img = GammaConverter().srgb_conv(self._lfp_img, inverse=True)
            except TypeError:
                self.sta.status_msg('File type not recognized')
                self.sta.error = True
                return False

            try:
                # try to load json file (if present)
                json_dict = self.cfg.load_json(self._lfp_path)
                self.cfg.lfpimg = LfpDecoder.filter_lfp_json(json_dict, self.cfg.lfp_img)
            except:
                pass

        # write json file
        self.cfg.save_params()

        return True

    def decode_lytro_file(self):

        # Lytro type decoding
        with open(self._lfp_path, mode='rb') as file:

            # LFC and raw type decoding
            obj = LfpDecoder(file, self.cfg, self.sta, lfp_path=self._lfp_path)
            obj.main()
            self._lfp_img = obj.bay_img
            self._json_dict = obj.json_dict
            del obj

            # save bayer image as file (if not already present)
            if not os.path.exists(self.fp) and not self.sta.interrupt:
                self.sta.status_msg(msg='Save raw image', opt=self.cfg.params[self.cfg.opt_prnt])
                self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])
                misc.save_img_file(misc.Normalizer(self._lfp_img).uint16_norm(), self.fp, file_type='tiff')
                self.sta.progress(100, self.cfg.params[self.cfg.opt_prnt])

        return True

    @property
    def lfp_img(self):
        return self._lfp_img
