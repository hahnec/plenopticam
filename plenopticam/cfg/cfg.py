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
from plenopticam.misc.status import PlenopticamStatus
from plenopticam.misc.errors import PlenopticamError
from plenopticam.misc.os_ops import mkdir_p
from plenopticam.misc.type_checks import *
from plenopticam.cfg.constants import PARAMS_KEYS, PARAMS_VALS, CALIBS_KEYS

# external libs
import json
from os.path import join, abspath, dirname, basename, splitext, isdir, isfile, exists
from os import remove, stat, chmod


class PlenopticamConfig(object):

    # static class variables for key parameters
    lfp_path, cal_path, cal_meta, cal_meth, \
    ptc_leng, \
    ran_refo, \
    opt_cali, opt_vign, opt_lier, opt_cont, opt_colo, opt_awb_, opt_sat_, opt_view, opt_refo, opt_refi, opt_pflu, \
    opt_arti, opt_rota, opt_dbug, opt_prnt, dir_remo \
    = PARAMS_KEYS

    pat_type, ptc_mean, mic_list = CALIBS_KEYS

    def __init__(self):

        # dicts initialization
        self.params = {}
        self.calibs = {}
        self.lfpimg = {}

        self._file_name = 'cfg.json'
        self._dir_path = dirname(abspath(__file__))     # for pip installed versions
        if not isdir(self._dir_path) and isdir(join(abspath('.'), 'cfg')):
            self._dir_path = join(abspath('.'), 'cfg')  # for py2app contents

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
            fp = join(self._dir_path, 'cfg.json')

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
            fp = join(self._dir_path, 'cfg.json')

        try:
            # create config folder (if not already present)
            mkdir_p(self._dir_path)
            # amend write privileges of (potentially existing) config file
            if exists(fp):
                st = stat(fp)
                chmod(fp, st.st_mode | 0o111)
            # write config file
            with open(fp, 'w+') as f:
                json.dump(self.params, f, sort_keys=True, indent=4, cls=NumpyTypeEncoder)
        except PermissionError:
            raise PlenopticamError('\n\nGrant permission to write to the config file '+fp)

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
        self.params[self.ran_refo] = [0, 2]
        self.params[self.opt_refi] = False
        self.params[self.opt_awb_] = True
        self.params[self.opt_sat_] = False
        self.params[self.opt_cont] = False
        self.params[self.opt_lier] = False

    def load_cal_data(self, fp=None):

        # construct file path
        fp = self.get_file_path() if fp is None else fp

        self.calibs = self.load_json(fp=fp)

        return True

    def save_cal_data(self, fp=None, **kwargs):

        # construct file path
        fp = self.get_file_path() if fp is None else fp

        self.save_json(fp=fp, **kwargs)

        return True

    def get_file_path(self):

        # construct file path
        if not self.params[self.cal_meta]:
            if isfile(self.params[self.cal_path]):
                fp = splitext(self.params[self.cal_path])[0]+'.json'
            else:
                fp = self.params[self.cal_meta]
        else:
            fp = self.params[self.cal_meta]

        return fp

    @staticmethod
    def load_json(fp=None, sta=None):

        sta = sta if sta is not None else PlenopticamStatus()

        # file name and file path handling
        if fp is not None and splitext(fp)[-1] != '.json':
            fn = splitext(basename(fp))[0]+'.json'
            fp = join(splitext(fp)[0], fn)

        # load calibration data from json file
        if exists(fp):
            try:
                with open(fp, 'r') as f:
                    json_dict = json.load(f)
            except json.decoder.JSONDecodeError:
                remove(fp)
                sta.status_msg('Calibration JSON File may be corrupted. Attempt to delete file %s' % fp, opt=True)
                raise PlenopticamError('Calibration JSON File may be corrupted. Attempt to delete file %s' % fp)
        else:
            json_dict = None
            if splitext(fp)[-1].lower() in ('.lfp', 'lfr', '.raw'):
                sta.status_msg('Provided file %s does not exist' % fp, opt=True)

        return json_dict

    @staticmethod
    def save_json(fp=None, **kwargs):

        # filename and file path handling
        if fp is not None:

            # json extension handling
            if splitext(fp)[-1] != '.json':
                fn = basename(splitext(fp)[0])+'.json'
                fp = join(dirname(splitext(fp)[0]), fn)

            # create folder
            mkdir_p(dirname(fp), False)

        # save calibration data as json file
        json_dict = kwargs['json_dict'] if 'json_dict' in kwargs else kwargs
        try:
            # amend write privileges of (potentially existing) config file
            if exists(fp):
                st = stat(fp)
                chmod(fp, st.st_mode | 0o111)
            # write file
            with open(fp, 'wt') as f:
                json.dump(json_dict, f, sort_keys=True, indent=4)
        except TypeError:
            return False

        return True

    @property
    def exp_path(self):
        """ export directory path """
        return splitext(self.params[self.lfp_path])[0]

    def cond_load_limg(self, img=None):
        return exists(self.params[self.lfp_path]) and (img is None and self.cond_lfp_align() or self.cond_auto_find())

    def cond_auto_find(self):
        return isdir(self.params[self.cal_path]) or self.params[self.cal_path].lower().endswith('.tar')

    def cond_load_wimg(self):
        return not self.cond_auto_find() and \
               (self.params[self.opt_cali] or self.params[self.opt_vign] or self.cond_lfp_align())

    def cond_perf_cali(self):
        return self.params[self.opt_cali] or \
               (not self.cond_meta_file() and self.cond_lfp_align())

    def cond_lfp_align(self):
        return not exists(join(self.exp_path, 'lfp_img_align.pkl'))

    def cond_meta_file(self):

        # look for meta data file (optionally find json file named after calibration image file)
        pot_meta = splitext(self.params[self.cal_path])[0] + '.json'
        cal_meta = self.params[self.cal_meta]
        self.params[self.cal_meta] = pot_meta if not isfile(cal_meta) and isfile(pot_meta) else cal_meta
        exist = isfile(self.params[self.cal_meta])

        if exist:
            # load meta data file and validate content
            self.load_cal_data()
            min_res_y = max(map(lambda x: x[2], self.calibs[self.mic_list])) * self.calibs['ptc_mean'][0]
            min_res_x = max(map(lambda x: x[3], self.calibs[self.mic_list])) * self.calibs['ptc_mean'][1]
            valid = min_res_y > 0 and min_res_x > 0
        else:
            valid = False

        return exist and valid


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
