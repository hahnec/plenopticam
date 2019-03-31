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

from tempfile import mkstemp
import sys

# local python files
from plenopticam.misc.status import PlenopticamStatus
from plenopticam import __version__
from plenopticam.gui.constants import PX, PY
from plenopticam.gui.widget_ctrl import CtrlWidget
from plenopticam.gui.widget_view import ViewWidget

# generate blank icon on windows
ICON = (b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x08\x00h\x05\x00\x00'
        b'\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00'
        b'\x08\x00\x00\x00\x00\x00@\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x01\x00\x00\x00\x01') + b'\x00'*1282 + b'\xff'*64
_, ICON_PATH = mkstemp()
with open(ICON_PATH, 'wb') as icon_file:
    icon_file.write(ICON)

# object for application window
class PlenopticamApp(tk.Tk):

    def __init__(self, parent):

        # inheritance
        tk.Tk.__init__(self, parent)
        self.parent = parent

        # window title
        self.wm_title("Plenopticam-"+__version__)

        # icon handling
        if sys.platform == 'win32':
            self.iconbitmap(default=ICON_PATH)

        # initialize parameters
        self.sta = PlenopticamStatus()

        # instantiate controller
        self.ctrl_wid = CtrlWidget(self)
        self.ctrl_wid.pack(fill='both', expand=True, side='top', padx=PX, pady=PY)

        # instantiate view
        self.view_wid = ViewWidget(self)
        self.view_wid.pack(fill='both', expand=True, side='bottom', padx=PX, pady=PY)

        # enable tkinter resizing
        self.resizable(True, False)

if __name__ == "__main__":

    MainWin = PlenopticamApp(None)
    MainWin.mainloop()
