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
    import tkinter.ttk as ttk
except ImportError:
    import Tkinter as tk
    import Tkinter.ttk as ttk

from plenopticam.gui.constants import PX


# make object for plot widget
class PbarWidget(tk.Frame):

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent

        # instantiate status
        self.tk_stat = tk.Label(self, text=self.parent.sta.stat_var)
        self.tk_stat.pack(fill='both', expand=True, side='top')

        # style definitions
        self.s = ttk.Style(self)
        self.s.theme_use('alt')
        self.s.layout("LabeledProgressbar",
                 [('LabeledProgressbar.trough',
                   {'children': [('LabeledProgressbar.pbar',
                                  {'side': 'left', 'sticky': 'nswe'}),
                                 ("LabeledProgressbar.label",
                                  {"sticky": ""})],
                  'sticky': 'nswe'})])
        self.s.configure("LabeledProgressbar", foreground='gray1', background='SteelBlue2')    # progress bar color

        # instantiate progress bar
        self.tk_prog_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate', style="LabeledProgressbar")
        self.tk_prog_bar.pack(fill='both', expand=True, side='bottom', pady=PX, padx=PX)
        self.tk_prog_bar['value'] = 0
        self.tk_prog_bar['maximum'] = 100

        # set-up event tracking
        self.parent.sta.bind_to_stat(self.update_stat_msg)
        self.parent.sta.bind_to_prog(self.update_prog_bar)
        self.parent.sta.bind_to_prog(self.update_prog_msg)

    def update_stat_msg(self, msg):

        self.tk_stat.configure(text=msg)
        self.update()

    def update_prog_bar(self, val):

        if isinstance(val, (float, int)):
            self.tk_prog_bar['value'] = val
        elif isinstance(val, str):
            self.tk_prog_bar['value'] = 0
        self.update()

    def update_prog_msg(self, val):

        if isinstance(val, (float, int)):
            prog_msg = "{0} %       ".format(val)
        else:
            prog_msg = "{0}         ".format(val)

        self.s.configure("LabeledProgressbar", text=prog_msg)
        self.update()
