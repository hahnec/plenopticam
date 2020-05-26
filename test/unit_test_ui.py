#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <inbox@christopherhahne.de>

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

import sys
import unittest

from test.unit_test_baseclass import PlenoptiCamTester
from plenopticam.bin.cli_script import main
from plenopticam.cfg.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.gui.widget_view import ViewWidget, PX, PY


class PlenoptiCamTesterUI(PlenoptiCamTester):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterUI, self).__init__(*args, **kwargs)

    def setUp(self):

        # set config for unit test purposes
        self.sta = PlenopticamStatus()
        self.cfg = PlenopticamConfig()
        self.cfg.reset_values()
        self.cfg.params[self.cfg.opt_dbug] = True
        self.cfg.params[self.cfg.opt_prnt] = True

    def test_cli_help(self):

        for kw in ['-h', '--help']:
            # print help message
            sys.argv.append(kw)
            try:
                ret = main()
            except SystemExit:
                ret = True

            self.assertEqual(True, ret)

    def test_viewer(self):

        try:
            import tkinter as tk
        except ImportError:
            import Tkinter as tk

        # dummy button with state key
        btn = {'state': 'normal'}

        # instantiate viewer
        self.view_frame = tk.Toplevel(padx=PX, pady=PY)  # open window
        self.view_frame.resizable(width=0, height=0)  # make window not resizable
        ViewWidget(self.view_frame, cfg=self.cfg, sta=self.sta, btn=btn).pack(expand="no", fill="both")

        # close frame
        self.view_frame.destroy()

        return True


if __name__ == '__main__':
    unittest.main()
