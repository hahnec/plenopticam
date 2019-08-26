# local imports
from plenopticam.lfp_calibrator import LfpCalibrator

# external libs
from os.path import join, isfile
from os import listdir
import tarfile

def calibrate_folder(cfg, sta):

    tarnames = [f for f in listdir(cfg.params[cfg.cal_path])
                if isfile(join(cfg.params[cfg.cal_path], f)) and f.lower().endswith(".tar")]

    for tarname in tarnames:

        tar_obj = tarfile.open(tarname, mode='r')

        for member in tar_obj.getmembers():
            wht_img = tar_obj.extractfile(member)
            LfpCalibrator(wht_img, cfg) #save metacalib.json

            # check interrupt status
            if sta.interrupt:
                return False

    return True