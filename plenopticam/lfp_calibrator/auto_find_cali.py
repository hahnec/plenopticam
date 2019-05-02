# local imports
from plenopticam.misc import safe_get
from plenopticam.misc.status import PlenopticamStatus

# external libs
import json
from os.path import join, exists, isdir
from os import listdir

try:
    import tarfile
except ImportError:
    raise ImportError('Please install tarfile package.')

class CaliFinder(object):

    def __init__(self, cfg, sta=None):

        # input variables
        self.cfg = cfg
        self.sta = sta if sta is not None else PlenopticamStatus()

        # internal variables
        self._lfp_json = {}
        self._georef = None
        self._serial = None
        self._cal_fn = None
        self._raw_data = None
        self._file_found = None
        self._opt_prnt = self.cfg.params[self.cfg.opt_prnt]
        self._path = self.cfg.params[self.cfg.cal_path]

        # output variables
        self._wht_img = None

    def main(self):

        # auto calibration can only be used if calibration source path is either directory or tar archive
        if isdir(self._path) or self._path.endswith('.tar'):

            # read JSON file from selected *.lfp image
            self._lfp_json = self.cfg.load_json(self.cfg.params[self.cfg.lfp_path])

            # extract calibration reference data
            frames = safe_get(self._lfp_json, "frames")
            if frames:
                self._georef = safe_get(frames[0], 'frame', 'geometryCorrectionRef')
            else:
                self._georef = ''

            # extract serial number to support search
            self._serial = safe_get(self._lfp_json, 'camera', 'serialNumber')

            # print status
            if not self._serial and isdir(self._path):
                self.sta.status_msg('No serial number found in JSON file. Provide calibration file instead of folder',
                                    self._opt_prnt)
                self.sta.interrupt = True

            # when path is directory
            if isdir(self._path):

                # look for geo data in calibration folders
                self._search_cal_dirs()

                # look for geo data in calibration tar-files (skip if already found in folders with file_found==True)
                self._search_cal_file()

            elif self._path.endswith('.tar'):

                # look for geo data in provided calibration tar-file
                self._search_tar_file(self._path)

            if self._file_found:
                # print status
                self.sta.status_msg('Found white image file '+self._cal_fn, self._opt_prnt)
            else:
                # print status and interrupt process
                self.sta.status_msg('White image file not found. Revise calibration path settings', self._opt_prnt)
                self.sta.interrupt = True

            # load if file found and rotation option is set or calibration data is missing or re-calibration is required
            cond = self.cfg.params[self.cfg.opt_rota] or not exists(self.cfg.params[self.cfg.cal_meta]) or self.cfg.params[self.cfg.opt_cali]
            if self._file_found and cond:
                # convert raw data to image array and get metadata
                self._raw2img()

        return True

    def _raw2img(self):
        ''' decode raw data to obtain bayer image and settings data '''

        # skip if calibrated json file already exists, otherwise perform centroid calibration
        if self._raw_data:

            from plenopticam.lfp_reader.lfp_decoder import LfpDecoder

            # decode raw data
            obj = LfpDecoder(self._raw_data, self.cfg, self.sta)
            obj.decode_raw()
            self._wht_img = obj.rgb_img
            del obj

        return True

    def _match_georef(self, json_dict):
        ''' compare georef hash value with that in provided json dictionary '''

        # search for georef hash value in geometry files of calibration folder
        for item in json_dict['calibrationFiles']:
            if item['hash'] == self._georef:  # stop when hash values match
                self._cal_fn = item['name'].replace('.GCT', '.RAW')     # save calibration file
                break

        return True

    def _search_cal_dirs(self):
        ''' look for geo data in calibration folders '''

        # skip if file already found or if provided path is not a directory
        if not self._file_found:
            onlydirs = [d for d in listdir(self._path)]
            dirnames = [self._serial] if onlydirs.count(self._serial) else onlydirs

            # iterate through directories
            for dirname in dirnames:
                cali_manifest = join(join(self._path, dirname), 'cal_file_manifest.json')
                if exists(cali_manifest):
                    with open(cali_manifest, 'r') as f:
                        json_dict = json.load(f)
                        self._match_georef(json_dict)
                        if self._cal_fn is not None:
                            self._file_found = True

                            # update config
                            self.cfg.params[self.cfg.cal_meta] = join(join(self._path.split('.')[0], self._serial), self._cal_fn)

                            # load raw data
                            self._raw_data = open(self.cfg.params[self.cfg.cal_meta], mode='rb')

                            break

        return True

    def _search_cal_file(self):
        ''' look for geo data in calibration tar-files '''

        # skip if file already found
        if not self._file_found:
            onlyfiles = [f for f in listdir(self._path) if f.endswith('.tar')]
            tarstring = 'caldata-'+str(self._serial)+'.tar'
            tarnames = [tarstring] if onlyfiles.count(tarstring) else onlyfiles #

            # iterate through tar-files
            for tarname in tarnames:
                self._search_tar_file(tarname)
                break

        return True

    def _search_tar_file(self, tarname):

        # read mla_calibration JSON file from tar archive
        try:
            tar_obj = tarfile.open(join(self._path, tarname), mode='r')
            cal_manifest = tar_obj.extractfile('unitdata/cal_file_manifest.json')
            json_dict = json.loads(cal_manifest.read().decode('utf-8'))
            self._match_georef(json_dict)
            if self._cal_fn:
                self._file_found = True

                # update config
                self._serial = tarname.split('-')[-1].split('.')[0]
                self.cfg.params[self.cfg.cal_meta] = join(self._path.split('.')[0],
                                                          self._serial, self._cal_fn.replace('.RAW', '.json'))

                # load raw data
                self._raw_data = tar_obj.extractfile('unitdata/' + self._cal_fn)

        except FileNotFoundError:
            self.sta.status_msg('Did not find calibration file.', opt=True)
        except KeyError:
            self.sta.status_msg('Did not find "cal_file_manifest.json" in tar archive', opt=True)
        except Exception:
            pass

    @property
    def raw_data(self):

        return self._raw_data

    @property
    def wht_img(self):

        return self._wht_img