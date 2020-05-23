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

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

import os
import sys
from tempfile import mkstemp

# local python files
from plenopticam import __version__
from plenopticam.gui.constants import PX, PY, ICON
from plenopticam.gui.widget_ctrl import CtrlWidget
from plenopticam.gui.widget_pbar import PbarWidget
from plenopticam.misc.status import PlenopticamStatus


class PlenopticamApp(tk.Tk):

    REL_PATH = os.path.join('icns', '1055104.gif')

    def __init__(self, parent):

        # inheritance
        tk.Tk.__init__(self, parent)
        self.parent = parent

        # window title
        self.wm_title("PlenoptiCam-v"+__version__)

        # icon handling
        self.icon_handling()

        # initialize parameters
        self.sta = PlenopticamStatus()

        # instantiate controller
        self.ctrl_wid = CtrlWidget(self)
        self.ctrl_wid.pack(fill='both', expand=True, side='top', padx=PX, pady=PY)

        # instantiate view
        self.pbar_wid = PbarWidget(self)
        self.pbar_wid.pack(fill='both', expand=True, side='bottom', padx=PX, pady=PY)

    def icon_handling(self):
        """ use OS temp folder if present or current working directory """

        # icon path for app bundle (tmp) or non-bundled package (cwd)
        cwd = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.REL_PATH)
        fp = os.path.join(sys._MEIPASS, self.REL_PATH) if hasattr(sys, '_MEIPASS') else cwd

        if sys.platform == 'linux':
            # load icon on linux
            logo = tk.PhotoImage(file=fp)
            self.call('wm', 'iconphoto', self._w, logo)

        elif sys.platform == 'win32':
            # generate blank window icon
            _, ICON_PATH = mkstemp()
            with open(ICON_PATH, 'wb') as icon_file:
                icon_file.write(ICON)

            # load icon on Windows
            fp = fp.replace('gif', 'ico')
            fp = ICON_PATH if not os.path.exists(fp) else fp
            self.iconbitmap(fp)
            self.wm_iconbitmap(default=fp)


if __name__ == "__main__":

    # instantiate object
    MainWin = PlenopticamApp(None)
    # make not resizable
    MainWin.resizable(width=0, height=0)
    # run
    MainWin.mainloop()
