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

from plenopticam.gui.widget_about import AbtWidget
import os
import sys


# make object for plot widget
class MenuWidget(tk.Frame):

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.parent.parent.createcommand('tkAboutDialog', self.open_about_dialog)

        menubar = tk.Menu(self)

        filemenu = MenuBtns(menubar, tearoff=0)
        filemenu.add_command(label="Process", command=self.parent.process)
        filemenu.add_command(label="Settings", command=self.parent.cfg_change)
        filemenu.add_separator()
        filemenu.add_command(label="Stop", command=self.parent.stop)
        filemenu.add_command(label="Quit", command=self.parent.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About...", command=self.open_about_dialog)
        helpmenu.add_command(label="Help...", command=self.open_docs)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.parent.parent.config(menu=menubar)

        self.btn_list = [filemenu]

    def open_about_dialog(self):
        ''' open about window '''

        # instantiate about widget
        AbtWidget()

        return True

    def open_docs(self):
        """ open documentation in webbrowser """

        # relative path for html documentation
        REL_PATH = "docs/build/html/index.html"

        # current working directory
        cwd = os.getcwd()

        # compose url
        if os.path.exists(os.path.join(cwd, REL_PATH)):
            url = "file:///" + os.path.join(cwd, REL_PATH)
        elif hasattr(sys, '_MEIPASS') and os.path.exists(os.path.join(sys._MEIPASS, REL_PATH)):
            url = "file:///" + os.path.join(sys._MEIPASS, REL_PATH)
        elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(cwd)), REL_PATH)):
            url = "file:///" + os.path.join(os.path.dirname(os.path.dirname(cwd)), REL_PATH)
        else:
            url = 'https://hahnec.github.io/plenopticam/build/html/index.html'

        # open in a new tab, if possible
        if sys.platform != 'linux':
            import webbrowser
            webbrowser.open(url, new=2)
        else:
            # workaround for linux app bundle inspired by https://github.com/pyinstaller/pyinstaller/issues/3668
            myEnv = dict(os.environ)
            myEnv['XDG_DATA_DIRS'] = '/usr/local/share:/usr/share:/var/lib/snapd/desktop'
            import subprocess
            subprocess.Popen(["xdg-open", url], env=myEnv)
            print(url)

class MenuBtns(tk.Menu):
    """ child of menu class that supports "state" as key for disabling menu buttons """

    def __init__(self, *args, **kwargs):
        super(MenuBtns, self).__init__(*args, **kwargs)

        self._labels = []
        self._state = tk.NORMAL

    def add_command(self, cnf={}, **kw):

        # keep track of labels
        self._labels.append(kw['label']) if 'label' in kw else None

        # add command
        self.add('command', cnf or kw)

    def __getitem__(self, key):

        return self._state if key == 'state' else self[key]

    def __setitem__(self, key, value):

        if key == 'state' and self._labels:
            if value == tk.NORMAL or value == tk.DISABLED:
                for i, label in enumerate(self._labels):
                    if label not in ('Stop', 'Quit'):
                        self.entryconfig(index=i, state=value)
                        self._state = value
        else:
            self[key] = value
