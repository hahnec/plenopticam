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

from plenopticam.gui.constants import PX, PY, BTN_W


# make object for command widget
class CmndWidget(tk.Frame):

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.cfg = parent.cfg
        self.btn_list = []

        # button for light field processing
        run_btn = tk.Button(self, text='Process', width=BTN_W, command=self.parent.process)
        run_btn.grid(row=0, column=0, padx=PX, pady=PY)
        self.btn_list.append(run_btn)

        # button for settings configuration
        cfg_btn = tk.Button(self, text='Settings', width=BTN_W, command=self.parent.cfg_change)
        cfg_btn.grid(row=0, column=1, padx=PX, pady=PY)
        self.btn_list.append(cfg_btn)

        # button to stop/cancel process
        viw_btn = tk.Button(self, text='Viewer', width=BTN_W, command=self.parent.view)
        viw_btn.grid(row=0, column=2, padx=PX, pady=PY)
        self.btn_list.append(viw_btn)

        # button for application shutdown
        qit_btn = tk.Button(self, text='Quit', width=BTN_W, command=self.parent.exit)
        qit_btn.grid(row=0, column=3, padx=PX, pady=PY)
        self.btn_list.append(qit_btn)
