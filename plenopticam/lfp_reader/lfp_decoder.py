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
from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import safe_get, PlenopticamStatus
from plenopticam.lfp_reader.constants import SUPP_FILE_EXT

# external libs
import json
import hashlib
import numpy as np
import os


class LfpDecoder(object):

    # static class variables
    LFP_HEADER = b'\x89\x4c\x46\x50\x0d\x0a\x1a\x0a\x00\x00\x00\x01'  # LFP header
    LFM_HEADER = b'\x89\x4c\x46\x4d\x0d\x0a\x1a\x0a\x00\x00\x00\x00'  # table of contents header
    LFC_HEADER = b'\x89\x4c\x46\x43\x0d\x0a\x1a\x0a\x00\x00\x00\x00'  # content section header
    PADDING_LEN = 4
    SHA1_LEN = 45
    SHA_PADDING_LEN = 35

    def __init__(self, file=None, cfg=None, sta=None, **kwargs):

        # input variables
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else PlenopticamStatus()
        self.file = file
        self._lfp_path = kwargs['lfp_path'] if 'lfp_path' in kwargs else self.cfg.params[self.cfg.lfp_path]

        # internal variables
        self._json_dict = kwargs['json_dict'] if 'json_dict' in kwargs else {}
        self._shape = None
        self._img_buf = None

        # output variable
        self.cfg.lfpimg = {} if not hasattr(self.cfg, 'lfpimg') else self.cfg.lfpimg
        self._bay_img = None

    def main(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # LFC type decoding
        if self._lfp_path.lower().endswith(SUPP_FILE_EXT[:2]):
            self.decode_lfc()

        # C.x bundle type decoding
        elif self._lfp_path.lower().endswith(SUPP_FILE_EXT[2:]):
            self.decode_bundle()

        # raw type decoding
        elif self._lfp_path.lower().endswith(SUPP_FILE_EXT[2]):
            self.decode_raw()

    def decode_lfc(self):

        # decode lfp file
        sections = self.read_buffer(self.file)

        # retrieve JSON data
        self._json_dict = self.read_json(sections)

        # JSON file export
        dp = os.path.splitext(self._lfp_path)[0]
        self.cfg.save_json(os.path.join(dp, os.path.basename(dp) + '.json'), json_dict=self.json_dict)

        # validate camera format support
        if not self.valid_cam_type:
            return False

        # decompose JSON data
        self._shape = [safe_get(self._json_dict, 'image', 'width'), safe_get(self._json_dict, 'image', 'height')]

        # filter LFP metadata settings
        self.cfg.lfpimg = self.filter_lfp_json(self._json_dict)

        # compose bayer image from lfp file
        sec_idx = self.get_idx(sections, int(self._shape[0] * self._shape[1] * self.cfg.lfpimg['bit'] / 8))[0]
        self._img_buf = list(sections[sec_idx])
        self.comp_bayer()

        return True

    def decode_raw(self):

        # read bytes from file
        self._img_buf = list(self.file) if isinstance(self.file, bytes) else list(self.file.read())

        if len(self._img_buf) >= int(7728*5368*10/8):
            self.cfg.lfpimg['bit'] = 10
            self._shape = [7728, 5368]
            self.cfg.lfpimg['bay'] = 'GRBG'
        elif len(self._img_buf) >= int(3280**2*10/8):
            self.cfg.lfpimg['bit'] = 12
            self._shape = [3280, 3280]
            self.cfg.lfpimg['bay'] = 'BGGR'
        else:
            self.sta.status_msg('File type not recognized')
            self.sta.error = True
            return False

        # compose bayer image from lfp file
        self.comp_bayer()

        return True

    def decode_bundle(self):

        # decode lfp file
        sections = self.read_buffer(self.file)

        # retrieve JSON data
        self._json_dict = self.read_json(sections)

        # JSON file export
        dp = os.path.splitext(self._lfp_path)[0]
        self.cfg.save_json(os.path.join(dp, os.path.basename(self._lfp_path) + '.json'), json_dict=self.json_dict)

        # decompose packed files from calibration bundle
        FILE_NUM = len(self._json_dict['files'])
        for idx, (section, file_dict) in enumerate(zip(sections[-FILE_NUM:], self._json_dict['files'])):
            # extract file name and write file
            fn = file_dict['name'].split('\\')[-1]
            with open(os.path.join(dp, fn), 'w') as f:
                try:
                    f.write(section.decode('utf-8'))
                except:
                    f.write(str(section))

        return True

    @property
    def valid_cam_type(self):
        ''' check if Lytro file format is supported '''

        # search for 2nd generation keys (filter camera serial and model )
        serial = safe_get(self._json_dict, "camera", "serialNumber")
        cam_model = serial if serial else safe_get(self._json_dict, "camera", "model")

        # search for 1st generations keys (file names)
        #files = safe_get(self._json_dict, "files")

        if cam_model is None:# and files is None:
            self.sta.status_msg('File type not recognized')
            self.sta.error = True
            return False

        return True


    @staticmethod
    def filter_lfp_json(json_dict, settings=None):
        ''' filter LFP metadata settings '''

        # variable init
        settings = {} if settings is None else settings
        channels = ['b', 'r', 'gb', 'gr']

        # filter camera serial and model
        serial = safe_get(json_dict, 'camera', 'serialNumber')
        cam_model = serial if serial else safe_get(json_dict, 'camera', 'model')

        # set decode paramaters considering camera model
        if cam_model.startswith(('A', 'F')):    # 1st generation Lytro

            # read bit packing
            settings['bit'] = safe_get(json_dict, "image", "rawDetails", "pixelPacking", "bitsPerPixel")
            if not settings['bit'] == 12:
                raise AssertionError('Unrecognized bit packing format')

            # get Bayer pattern, Automatic White Balance (AWB) gains and Color Correction Matrix (CCM)
            settings['bay'] = 'BGGR'
            settings['awb'] = [safe_get(json_dict, 'image', 'color', 'whiteBalanceGain', key) for key in channels]
            settings['ccm'] = safe_get(json_dict, 'image', 'color', 'ccmRgbToSrgbArray')
            settings['gam'] = safe_get(json_dict, 'image', 'color', 'gamma')

        elif cam_model.startswith(('B', 'I')):  # 2nd generation Lytro

            # read bit packing
            settings['bit'] = safe_get(json_dict, "image", "pixelPacking", "bitsPerPixel")
            if not settings['bit'] == 10:
                raise AssertionError('Unrecognized bit packing format')

            # get Bayer pattern, Automatic White Balance (AWB) gains and Color Correction Matrix (CCM)
            settings['bay'] = 'GRBG'
            settings['awb'] = [safe_get(json_dict, 'algorithms', 'awb', 'computed', 'gain', key) for key in channels]
            settings['ccm'] = safe_get(json_dict, 'image', 'color', 'ccm')
            settings['gam'] = safe_get(json_dict, 'master', 'picture', 'frameArray', 0, 'frame', 'metadata', 'image',
                                       'color', 'gamma')
            settings['exp'] = safe_get(json_dict, "image", "modulationExposureBias")

        return settings

    def read_buffer(self, f):

        # list init
        sections = []

        try:
            # header decomposition and validation checks
            file_header = f.read(len(self.LFP_HEADER))
            if not file_header == self.LFP_HEADER:
                raise AssertionError('File header type not recognized')
            header_length = int(f.read(4).hex(), 16)
            if not header_length == 0:
                raise AssertionError('Unexpected header length')
            while f.read(1) != b'':
                f.seek(-1, 1)   # move back one byte
                sections.append(self.read_section(f))
            f.close()
        except AssertionError:
            f.close()

        return sections

    def read_section(self, f):

        # read section header
        sect_header = f.read(len(self.LFM_HEADER))
        if not (sect_header == self.LFM_HEADER or sect_header == self.LFC_HEADER):
            raise AssertionError('Section header type not recognized')

        # read data section length
        sect_len = int(f.read(4).hex(), 16)

        # read sha1 checksum and padding
        sha1 = f.read(self.SHA1_LEN)
        padding = int(f.read(self.SHA_PADDING_LEN).hex(), 16)   # skip padding
        if not padding == 0:
            raise AssertionError('Unexpected padding length')

        # read data section and evaluate sha-1 checksum
        section = f.read(sect_len)
        if not sha1[5:] == hashlib.sha1(section).hexdigest().encode('utf-8'):
            raise AssertionError('Corrupted section %s' % section)

        # move forward to next section while ignoring padded bytes
        while True:
            padding = f.read(1)
            if padding == '' or padding != b'\x00':
                break

        if padding != b'':
            f.seek(-1, 1)   # move back one byte

        return section

    def comp_bayer(self):
        ''' inspired by Nirav Patel's lfptools '''

        # initialize column vector for bayer image array
        self._bay_img = np.zeros(self._shape[0]*self._shape[1], dtype=np.uint16)

        # determine bit packing
        bit_pac = self.cfg.lfpimg['bit'] if 'bit' in self.cfg.lfpimg.keys() else 10

        if bit_pac == 10:

            t0 = np.array(self._img_buf[0::5], 'uint16')
            t1 = np.array(self._img_buf[1::5], 'uint16')
            t2 = np.array(self._img_buf[2::5], 'uint16')
            t3 = np.array(self._img_buf[3::5], 'uint16')
            t4 = np.array(self._img_buf[4::5], 'uint16')

            t0 = t0 << 2
            t1 = t1 << 2
            t2 = t2 << 2
            t3 = t3 << 2

            t0 += (t4 & 0x03)
            t1 += (t4 & 0x0C) >> 2
            t2 += (t4 & 0x30) >> 4
            t3 += (t4 & 0xC0) >> 6

            self._bay_img = np.empty((4*t0.size,), dtype=t0.dtype)
            self._bay_img[0::4] = t0        # green-red
            self._bay_img[1::4] = t1        # red
            self._bay_img[2::4] = t2        # green-blue
            self._bay_img[3::4] = t3        # blue

        elif bit_pac == 12:

            t0 = np.array(self._img_buf[0::3], 'uint16')
            t1 = np.array(self._img_buf[1::3], 'uint16')
            t2 = np.array(self._img_buf[2::3], 'uint16')

            a0 = (t0 << 4) + ((t1 & 0xF0) >> 4)
            a1 = ((t1 & 0x0F) << 8) + t2

            self._bay_img = np.empty((2*a0.size,), dtype=t0.dtype)
            self._bay_img[0::4] = a0[0::2]  # blue
            self._bay_img[2::4] = a0[1::2]  # red
            self._bay_img[1::2] = a1        # green

        # rearrange column vector to 2-D image array
        self._bay_img = np.reshape(self._bay_img, (self._shape[1], self._shape[0]))

        # convert to float
        self._bay_img = self._bay_img.astype('float')

        return True

    @staticmethod
    def read_json(sections):
        json_dict = {}
        for i in range(len(sections)):
            try:
                json_dict.update(json.loads(sections[i].decode('utf-8')))
            except UnicodeDecodeError:
                pass
            except json.decoder.JSONDecodeError:
                pass

        return json_dict

    @staticmethod
    def get_idx(checklist, value):
        return [x for x in range(len(checklist)) if len(checklist[x]) == value]

    @property
    def bay_img(self):
        return (self._bay_img.copy()-65)/(1023-65) if self._bay_img is not None else None

    @property
    def json_dict(self):
        return self._json_dict.copy()
