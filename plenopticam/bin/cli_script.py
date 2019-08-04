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
    print("-f <filename>, --file=<filename>  Specify image file to process")

    # img extract options
    print("-r <type>, --refo=<type>          Refocusing image synthesis flag")
    print("-v , --view                       Viewpoint extraction flag")
    print("-p , --patch                      Patch size")

    print("-d , --dir                        Provide folder for light field stack execution.")
    print("-h , --help                       Print this help message.")
    print("")

    sys.exit()

def parse_options(argv):

    # default parameters
    cfg = PlenopticamConfig()
    cfg.params[cfg.opt_prnt] = True
    cfg.params[cfg.opt_cont] = True
    cfg.params[cfg.opt_awb_] = False

    try:
        opts, args = getopt.getopt(argv, ":ghfrvpd", ["gui", "help", "file=", "refo=", "view", "patch", "dir"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    if opts:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            if opt in ("-f", "--file"):
                cfg.params[cfg.lfp_path] = arg
            if opt in ("-r", "--refo"):
                cfg.params[cfg.opt_refo] = arg
            if opt in ("-v", "--view"):
                cfg.params[cfg.opt_view] = arg
            if opt in ("-p", "--patch"):
                cfg.params[cfg.ptc_leng] = arg
            if opt in ("-d", "--dir"):
                cfg.params[cfg.lfp_path] = arg
            if opt in ("-g", "--gui"):
                obj = PlenopticamApp(None)
                obj.mainloop()
                del obj
                sys.exit()

    # create dictionary containing all parameters for the light field
    return cfg

def main():

    # parse options
    cfg = parse_options(sys.argv[1:])

    # instantiate status object
    sta = misc.PlenopticamStatus()
    sta.bind_to_interrupt(sys.exit)     # set interrupt

    # select light field image(s) considering provided folder or file
    #cfg.params[cfg.lfp_path] = "/Users/Admin/Pictures/Plenoptic/INRIA_SIROCCO/"
    if os.path.isdir(cfg.params[cfg.lfp_path]):
        lfp_filenames = [f for f in os.listdir(cfg.params[cfg.lfp_path]) if f.lower().endswith(SUPP_FILE_EXT)]
    elif not os.path.isfile(cfg.params[cfg.lfp_path]):
        lfp_filenames = [misc.select_file(cfg.params[cfg.lfp_path], 'Select plenoptic image')]
    else:
        lfp_filenames = [cfg.params[cfg.lfp_path]]

    # open selection window (at directory where current lfp file is located) to set calibration folder path
    cfg.params[cfg.cal_path] = misc.select_file(cfg.params[cfg.lfp_path], 'Select calibration image')

    # iterate through light field image(s)
    for lfp_filename in lfp_filenames:

        # change path to next filename
        cfg.params[cfg.lfp_path] = os.path.join(os.path.dirname(cfg.params[cfg.lfp_path]), lfp_filename)

        # decode light field image
        lfp_obj = lfp_reader.LfpReader(cfg, sta, cfg.params[cfg.lfp_path])
        lfp_obj.main()
        lfp_img = lfp_obj.lfp_img
        del lfp_obj

        # create output data folder
        misc.mkdir_p(cfg.params[cfg.lfp_path].split('.')[0], cfg.params[cfg.opt_prnt])

        #  check if light field alignment has been done before
        if not os.path.exists(os.path.join(cfg.params[cfg.lfp_path].split('.')[0], 'lfp_img_align.pkl')):

            # manual calibration data selection
            sta.status_msg('\r Please select white image calibration source manually', cfg.params[cfg.opt_prnt])

            if os.path.isdir(cfg.params[cfg.cal_path]) or cfg.params[cfg.cal_path].endswith('.tar'):
                # automatic calibration data selection
                obj = lfp_calibrator.CaliFinder(cfg, sta)
                obj.main()
                wht_img = obj.wht_img
                del obj
            else:
                # load white image calibration file
                wht_img = misc.load_img_file(cfg.params[cfg.cal_path])

                # save settings configuration
                cfg.save_params()

            # perform calibration if previously computed calibration data does not exist
            meta_cond = not (os.path.exists(cfg.params[cfg.cal_meta]) and cfg.params[cfg.cal_meta].endswith('json'))
            if meta_cond or cfg.params[cfg.opt_cali]:

                # perform centroid calibration
                cal_obj = lfp_calibrator.LfpCalibrator(wht_img, cfg, sta)
                cal_obj.main()
                cfg = cal_obj.cfg
                del cal_obj

            # load calibration data
            cfg.load_cal_data()

            # align light field
            lfp_obj = lfp_aligner.LfpAligner(lfp_img, cfg, sta, wht_img)
            lfp_obj.main()
            lfp_obj = lfp_obj.lfp_img
            del lfp_obj

        # load previously computed light field alignment
        lfp_img_align = pickle.load(open(os.path.join(cfg.params[cfg.lfp_path].split('.')[0], 'lfp_img_align.pkl'), 'rb'))

        # export light field data
        lfp_calibrator.CaliFinder(cfg, sta).main()
        exp_obj = lfp_extractor.LfpExtractor(lfp_img_align, cfg)
        exp_obj.main()
        del exp_obj

if __name__ == "__main__":

    sys.exit(main())
