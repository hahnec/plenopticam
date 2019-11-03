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
    from tkinter.filedialog import askopenfilename, askdirectory
except ImportError:
    import Tkinter as tk
    from tkFileDialog import askopenfilename, askdirectory

import os

from plenopticam.gui.constants import PX, PY, BTN_W


# make object for plot widget
class PathWidget(tk.Frame):

    def __init__(self, parent, path='', title="Browse", path_type=False, file_exts=()):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent

        # store extension names and types
        self.title = title
        self.path_type = path_type
        self.file_exts = file_exts

        # create current path and entry placeholder
        self._path = tk.StringVar(value=path)
        self._path_observers = []
        self.ent = tk.Entry(self, width=2*BTN_W, textvariable=self._path)
        self.ent.grid(row=0, column=0, padx=PX, pady=PY)
        self.ent.xview_moveto(1.0)  # display path from most right

        # create search button
        self.btn = tk.Button(self, width=BTN_W, text=self.title, command=self.choose_path)
        self.btn.grid(row=0, column=1, padx=PX, pady=PY)

    def choose_path(self):
        """ choose a path on the system using tkinter's frames """

        # select path considering type option (file=True; directory=False)
        if self.path_type:
            new_path = askdirectory(title=self.title, initialdir=os.path.dirname(self._path.get()),
                                    mustexist=True)
        else:
            new_path = askopenfilename(title=self.title,
                                       initialdir=os.path.dirname(self._path.get()),
                                       initialfile=os.path.basename(self._path.get()),
                                       filetypes=self.file_exts)

        # update entry text with the new path
        if new_path:
            self.path = new_path

    # enable observer pattern to track change in self.path
    @property
    def path(self):
        return self._path.get()

    @path.setter
    def path(self, val):
        self._path.set(val)
        for callback in self._path_observers:
            callback(self._path.get())

    def bind_to(self, callback):
        self._path_observers.append(callback)
