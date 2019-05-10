# local imports
from plenopticam.misc import safe_get, PlenopticamStatus
from plenopticam.misc.errors import LfpTypeError, LfpAttributeError
from plenopticam.lfp_reader.cfa_processor import CfaProcessor

# external libs
import json
import hashlib

class LfpDecoder(object):

    # static class variables
    LFP_HEADER = b'\x89\x4c\x46\x50\x0d\x0a\x1a\x0a\x00\x00\x00\x01'  # LFP header
    LFM_HEADER = b'\x89\x4c\x46\x4d\x0d\x0a\x1a\x0a\x00\x00\x00\x00'  # table of contents header
    LFC_HEADER = b'\x89\x4c\x46\x43\x0d\x0a\x1a\x0a\x00\x00\x00\x00'  # content section header
    PADDING_LEN = 4
    SHA1_LEN = 45
    SHA_PADDING_LEN = 35

    def __init__(self, file=None, cfg=None, sta=None):

        # input variables
        self.cfg = cfg
        self.sta = sta if sta is not None else PlenopticamStatus()
        self.file = file
        if not self.file:
            raise LfpAttributeError('File not passed to LfcDecoder class')

        # internal variables
        self._bay_img = None
        self._json_dict = {}

        # output variable
        self.cfg.lfpimg = {}
        self._rgb_img = None

    def decode_lfc(self):

        # decode lfp file
        sections = self.read_buffer(self.file)

        # analyze JSON data
        self._json_dict = self.read_json(sections)

        # decompose JSON data
        h, w = [safe_get(self._json_dict, 'image', 'width'), safe_get(self._json_dict, 'image', 'height')]

        # filter LFP metadata settings
        self.cfg.lfpimg = self.filter_json(self._json_dict)

        # compose bayer image from lfp file
        sec_idx = self.get_idx(sections, int(h * w * self.cfg.lfpimg['bit'] / 8))

        # perform color filter array management and obtain rgb image
        cfa_obj = CfaProcessor(img_buf=list(sections[sec_idx]), shape=(h, w), cfg=self.cfg, sta=self.sta)
        cfa_obj.main()
        self._rgb_img = cfa_obj.rgb_img
        del cfa_obj

        return True

    def decode_raw(self):

        # read bytes from file
        raw_data = list(self.file.read())

        if len(raw_data) >= int(7728*5368*10/8):
            self.cfg.lfpimg['bit'] = 10
            img_size = [7728, 5368]
            self.cfg.lfpimg['bay'] = 'GRBG'
        elif len(raw_data) >= int(3280**2*10/8):
            self.cfg.lfpimg['bit'] = 12
            img_size = [3280, 3280]
            self.cfg.lfpimg['bay'] = 'BGGR'
        else:
            raise LfpTypeError('File type not recognized')

        # perform color filter array management and obtain rgb image
        cfa_obj = CfaProcessor(img_buf=raw_data, shape=img_size, cfg=self.cfg, sta=self.sta)
        cfa_obj.main()
        self._rgb_img = cfa_obj.rgb_img
        del cfa_obj

        return True

    @staticmethod
    def filter_json(json_dict):
        ''' filter LFP metadata settings '''

        # variable init
        settings = {}
        channels = ['b', 'r', 'gb', 'gr']

        # filter camera serial and model
        serial = safe_get(json_dict, "camera", "serialNumber")
        cam_model = serial if serial else safe_get(json_dict, "camera", "model")

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

        else:
            raise LfpTypeError('Camera type not recognized')

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
            while (f.read(1) != b''):
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

    @staticmethod
    def read_json(sections):
        json_dict = {}
        for i in range(len(sections)):
            try:
                json_dict.update(json.loads(sections[i].decode('utf-8')))
            except UnicodeDecodeError:
                pass

        return json_dict

    @staticmethod
    def get_idx(checklist, value):
        return [x for x in range(len(checklist)) if len(checklist[x]) == value][0]

    @property
    def rgb_img(self):
        return self._rgb_img.copy()

    @property
    def json_dict(self):
        return self._json_dict.copy()