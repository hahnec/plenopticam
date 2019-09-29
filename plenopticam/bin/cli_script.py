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

import getopt
import sys, os
import pickle

# local imports
from plenopticam import lfp_calibrator
from plenopticam import lfp_aligner
from plenopticam import lfp_extractor
from plenopticam import lfp_reader
from plenopticam.lfp_reader.top_level import SUPP_FILE_EXT
from plenopticam import misc
from plenopticam.cfg import PlenopticamConfig
from plenopticam import __version__
from plenopticam.gui import PlenopticamApp

def usage():

    print("\nPlenopticam " + __version__ + " by Christopher Hahne")
    print("Usage: plenopticam <options>\n")
    print("Options:")
    print("-g                                Open up graphical user interface")
    print("-f <filepath>, --file=<filepath>  Specify image file or folder to process")
    print("-c <calipath>, --cali=<calipath>  Specify calibration file to process")
    print("-p <number>,   --patch=<number>   Patch size")
    print("-r <list>,     --refo=[0, 2]      Refocusing range")

    # boolean options
    print("--refi                            Refocusing refinement flag")
    print("--vgn                             De-vignetting flag")
    print("--awb                             Auto white balance flag")
    print("--con                             Contrast automation flag")
    print("--hot                             Hot pixel treatment flag")
    print("--sat                             Saturation automation flag")

    print("-h , --help                       Print this help message.")
    print("")

    sys.exit()

def parse_options(argv, cfg):

    try:
        opts, args = getopt.getopt(argv, "ghf:c:p:r:",
                                        ["gui", "help", "file=", "cali=", "patch=", "refo=", "refi",
                                         "vgn", "awb", "con", "hot", "sat"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    if opts:
        for (opt, arg) in opts:
            if opt in ("-g", "--gui"):
                PlenopticamApp(None).mainloop()
                sys.exit()
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            if opt in ("-f", "--file"):
                cfg.params[cfg.lfp_path] = arg
            if opt in ("-c", "--cali"):
                cfg.params[cfg.cal_path] = arg
            if opt in ("-p", "--patch"):
                cfg.params[cfg.ptc_leng] = misc.str2type(arg)
            if opt in ("-r", "--refo"):
                refo_range = misc.str2list(arg)
                cfg.params[cfg.ran_refo] = refo_range if isinstance(refo_range, list) else [0, 2]
            if opt == "--refi":
                cfg.params[cfg.opt_refi] = True
            if opt == "--vgn":
                cfg.params[cfg.opt_vign] = True
            if opt == "--awb":
                cfg.params[cfg.opt_awb_] = True
            if opt == "--con":
                cfg.params[cfg.opt_cont] = True
            if opt == "--hot":
                cfg.params[cfg.opt_hotp] = True
            if opt == "--sat":
                cfg.params[cfg.opt_sat_] = True

    # create dictionary containing all parameters for the light field
    return cfg

def main():

    # create config object
    cfg = PlenopticamConfig()
    cfg.default_values()
    cfg.reset_values()

    # parse options
    cfg = parse_options(sys.argv[1:], cfg)

    # instantiate status object
    sta = misc.PlenopticamStatus()
    sta.bind_to_interrupt(sys.exit)     # set interrupt

    # select light field image(s) considering provided folder or file
    if os.path.isdir(cfg.params[cfg.lfp_path]):
        lfp_filenames = [f for f in os.listdir(cfg.params[cfg.lfp_path]) if f.lower().endswith(SUPP_FILE_EXT)]
    elif not os.path.isfile(cfg.params[cfg.lfp_path]):
        lfp_filenames = [misc.select_file(cfg.params[cfg.lfp_path], 'Select plenoptic image')]
    else:
        lfp_filenames = [cfg.params[cfg.lfp_path]]

    if not cfg.params[cfg.cal_path]:
        # open selection window (at current lfp file directory) to set calibration folder path
        cfg.params[cfg.cal_path] = misc.select_file(cfg.params[cfg.lfp_path], 'Select calibration image')

    # cancel if file paths not provided
    sta.validate(checklist=lfp_filenames+[cfg.params[cfg.lfp_path]], msg='Canceled due to missing image file path')

    # iterate through light field image(s)
    for lfp_filename in lfp_filenames:

        # change path to next filename
        cfg.params[cfg.lfp_path] = os.path.join(os.path.dirname(cfg.params[cfg.lfp_path]), lfp_filename)
        sta.status_msg(msg=cfg.params[cfg.lfp_path], opt=cfg.params[cfg.opt_prnt])

        try:
            # decode light field image
            lfp_obj = lfp_reader.LfpReader(cfg, sta, cfg.params[cfg.lfp_path])
            lfp_obj.main()
            lfp_img = lfp_obj.lfp_img
            del lfp_obj
        except Exception as e:
            misc.PlenopticamError(e)
            continue

        # create output data folder
        misc.mkdir_p(cfg.exp_path, cfg.params[cfg.opt_prnt])

        if cfg.cond_auto_find:
            # automatic calibration data selection
            obj = lfp_calibrator.CaliFinder(cfg, sta)
            obj.main()
            wht_img = obj.wht_img
            del obj

        else:
            # manual calibration data selection
            sta.status_msg('\r Please select white image calibration source manually', cfg.params[cfg.opt_prnt])
            # load white image calibration file
            wht_img = misc.load_img_file(cfg.params[cfg.cal_path])
            # save settings configuration
            cfg.save_params()

        # perform calibration if previously computed calibration data does not exist
        meta_cond = not (os.path.exists(cfg.params[cfg.cal_meta]) and cfg.params[cfg.cal_meta].lower().endswith('json'))
        if meta_cond or cfg.params[cfg.opt_cali]:
            # perform centroid calibration
            cal_obj = lfp_calibrator.LfpCalibrator(wht_img, cfg, sta)
            cal_obj.main()
            cfg = cal_obj.cfg
            del cal_obj

        # load calibration data
        cfg.load_cal_data()

        #  check if light field alignment has been done before
        if cfg.cond_lfp_align:
            # align light field
            lfp_obj = lfp_aligner.LfpAligner(lfp_img, cfg, sta, wht_img)
            lfp_obj.main()
            lfp_obj = lfp_obj.lfp_img
            del lfp_obj

        # load previously computed light field alignment
        with open(os.path.join(cfg.exp_path, 'lfp_img_align.pkl'), 'rb') as f:
            lfp_img_align = pickle.load(f)

        # export light field data
        lfp_calibrator.CaliFinder(cfg).main()
        exp_obj = lfp_extractor.LfpExtractor(lfp_img_align, cfg)
        exp_obj.main()
        del exp_obj

if __name__ == "__main__":

    sys.exit(main())
