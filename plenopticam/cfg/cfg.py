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
from plenopticam.misc import mkdir_p, PlenopticamStatus, PlenopticamError
from plenopticam.misc.type_checks import *
from plenopticam.cfg.constants import PARAMS_KEYS, PARAMS_VALS, CALIBS_KEYS

# external libs
import json
import os

class PlenopticamConfig(object):

    # static class variables for key parameters
    lfp_path, cal_path, cal_meta, \
    ptc_leng, \
    ran_refo, \
    opt_cali, opt_vign, opt_hotp, opt_cont, opt_awb_, opt_view, opt_refo, opt_refi, opt_pflu, opt_rota, opt_dbug, \
    opt_prnt, dir_remo, \
    = PARAMS_KEYS

    pat_type, ptc_mean, mic_list = CALIBS_KEYS

    def __init__(self):

        # dicts initialization
        self.params = {}
        self.calibs = {}
        self.lfpimg = {}

        self._file_name = 'cfg.json'
        self._dir_path = os.path.dirname(os.path.abspath(__file__)) # for pip installed versions
        if not os.path.isdir(self._dir_path):
            self._dir_path = os.path.join(os.path.abspath('.'), 'cfg') # for py2app contents

        try:
            self.read_params()
            # test if config parameters present
            if not self.params.keys():
                raise PlenopticamError('Config file could not be loaded')
            # number of values in loaded config is supposed to equal config constants specified in the tool
            if not len(self.params.keys()) == len(PARAMS_KEYS):
                raise PlenopticamError('Config file corrupted')
        except Exception:
            self.default_values()
            self.save_params()

    def read_params(self, fp=None):

        if not fp:
            fp = os.path.join(self._dir_path, 'cfg.json')

        try:
            with open(fp, 'r') as f:
                json_data = json.load(f)

            # transfer parameters to config object
            for key in json_data:
                self.params[key] = str2type(json_data[key])

        except FileNotFoundError:
            pass

        return True

    def save_params(self, fp=None):

        if not fp:
            fp = os.path.join(self._dir_path, 'cfg.json')

        try:
            # create config folder (if not already present)
            mkdir_p(self._dir_path)
            # write config file
            with open(fp, 'w+') as f:
                json.dump(self.params, f, sort_keys=True, indent=4, cls=NumpyTypeEncoder)
        except PermissionError:
            pass    # raise PlenopticamError('\n\nGrant permission to write to the config file '+fp)

        return True

    def default_values(self):

        # reconstruct dict from constants
        self.params = dict(zip(PARAMS_KEYS, PARAMS_VALS))

        # write to json file
        self.save_params()

        return True

    def reset_values(self):

        self.params[self.lfp_path] = ''
        self.params[self.cal_path] = ''
        self.params[self.cal_meta] = ''
        self.params[self.opt_awb_] = False
        self.params[self.opt_cont] = False
        self.params[self.opt_hotp] = False

    def load_cal_data(self):

        # construct file path
        fp = self.get_file_path()

        self.calibs = self.load_json(fp=fp)

        return True

    def save_cal_data(self, **kwargs):

        # construct file path
        fp = self.get_file_path()

        self.save_json(fp=fp, **kwargs)

        return True

    def get_file_path(self):

        # construct file path
        if not self.params[self.cal_meta]:
            if os.path.isfile(self.params[self.cal_path]):
                fp = os.path.splitext(self.params[self.cal_path])[0]+'.json'
            else:
                fp = self.params[self.cal_meta]
        else:
            fp = self.params[self.cal_meta]

        return fp

    @staticmethod
    def load_json(fp=None, sta=None):

        sta = sta if sta is not None else PlenopticamStatus()

        # filename and filepath handling
        if fp is not None and os.path.splitext(fp)[-1] != '.json':
            fn = os.path.splitext(os.path.basename(fp))[0]+'.json'
            fp = os.path.join(os.path.splitext(fp)[0], fn)

        # load calibration data from json file
        try:
            with open(fp, 'r') as f:
                json_dict = json.load(f)
        except json.decoder.JSONDecodeError:
            os.remove(fp)
            sta.status_msg('Calibration JSON File may be corrupted. Attempt to delete file %s' % fp, opt=True)
            raise PlenopticamError('Calibration JSON File may be corrupted. Attempt to delete file %s' % fp)
        except IsADirectoryError:
            sta.status_msg('Provided location %s is a directory' % fp, opt=True)
            raise PlenopticamError('Provided location %s is a directory' % fp)
        except FileNotFoundError:
            sta.status_msg('Provided file %s does not exist' % fp, opt=True)
            raise PlenopticamError('Provided file %s does not exist' % fp)

        return json_dict

    @staticmethod
    def save_json(fp=None, **kwargs):

        # filename and file path handling
        if fp is not None:

            # json extension handling
            if os.path.splitext(fp)[-1] != '.json':
                fn = os.path.basename(os.path.splitext(fp)[0])+'.json'
                fp = os.path.join(os.path.dirname(os.path.splitext(fp)[0]), fn)

            # create folder
            mkdir_p(os.path.dirname(fp), False)

        # save calibration data as json file
        json_dict = kwargs['json_dict'] if 'json_dict' in kwargs else kwargs
        try:
            with open(fp, 'wt') as f:
                json.dump(json_dict, f, sort_keys=True, indent=4)
        except:
            return False

        return True

class NumpyTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyTypeEncoder, self).default(obj)