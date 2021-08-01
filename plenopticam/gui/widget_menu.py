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

        menu_bar = tk.Menu(self)

        file_menu = MenuBtns(menu_bar, tearoff=0)
        file_menu.add_command(label="Process", command=self.parent.process)
        file_menu.add_command(label="Settings", command=self.parent.cfg_change)
        file_menu.add_separator()
        file_menu.add_command(label="Stop", command=self.parent.stop)
        file_menu.add_command(label="Quit", command=self.parent.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About...", command=self.open_about_dialog)
        help_menu.add_command(label="Help...", command=self.open_docs)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.parent.parent.config(menu=menu_bar)

        self.btn_list = [file_menu]

    @staticmethod
    def open_about_dialog():
        """ open about window """

        # instantiate about widget
        AbtWidget()

        return True

    @staticmethod
    def open_docs():
        """ open documentation in webbrowser """

        # relative path for html documentation
        rel_path = "docs/build/html/index.html"

        # current working directory
        cwd = os.getcwd()

        # compose url
        if os.path.exists(os.path.join(cwd, rel_path)):
            url = "file:///" + os.path.join(cwd, rel_path)
        elif hasattr(sys, '_MEIPASS') and os.path.exists(os.path.join(sys._MEIPASS, rel_path)):
            url = "file:///" + os.path.join(sys._MEIPASS, rel_path)
        elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(cwd)), rel_path)):
            url = "file:///" + os.path.join(os.path.dirname(os.path.dirname(cwd)), rel_path)
        else:
            url = 'https://hahnec.github.io/plenopticam/build/html/index.html'

        # open in a new tab, if possible
        if sys.platform != 'linux':
            import webbrowser
            webbrowser.open(url, new=2)
        else:
            # workaround for linux app bundle inspired by https://github.com/pyinstaller/pyinstaller/issues/3668
            my_env = dict(os.environ)
            my_env['XDG_DATA_DIRS'] = '/usr/local/share:/usr/share:/var/lib/snapd/desktop'
            import subprocess
            subprocess.Popen(["xdg-open", url], env=my_env)
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
