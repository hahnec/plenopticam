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

from plenopticam import __version__
from plenopticam.gui.constants import PX, PY, BTN_W


# make object for config window
class AbtWidget(object):

    def __init__(self):

        # open about window
        self.abt_widget = tk.Toplevel(padx=PX, pady=PY)

        # window title
        self.abt_widget.wm_title("About")

        # name and version
        line = tk.Label(master=self.abt_widget, text="Plenopticam "+__version__)
        line.grid(row=0, padx=PX, pady=PY, sticky='NWSE')

        # website
        link = tk.Label(master=self.abt_widget, text=r"http://www.plenoptic.info")
        link.grid(row=1, padx=PX, pady=PY, sticky='NWSE')

        # license
        license = tk.Label(master=self.abt_widget, text=__license__)
        license.grid(row=2, padx=PX, sticky='NWSE')

        btn = tk.Button(self.abt_widget, text="Close", width=BTN_W, command=self.close)
        btn.grid(row=3, padx=PX, pady=PY)

    def close(self):
        """ close about window """

        self.abt_widget.destroy()

        return True
