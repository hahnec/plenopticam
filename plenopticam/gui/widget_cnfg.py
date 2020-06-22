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
from plenopticam.cfg import constants as c


class CnfgWidget(object):

    def __init__(self, cfg):

        # inherit cfg object
        self.cfg = cfg

        # open window
        self.frame = tk.Toplevel(padx=PX, pady=PY)
        self.frame.wm_title("Configuration")

        # tk variables init
        self.tk_vars = {}

        # tk widget list init
        self.obj_ents = {}

        # generate settings properties using dict consisting of lists containing names and types
        PROPERTIES = dict(zip(c.PARAMS_KEYS, (pair for pair in zip(c.PARAMS_NAME, c.PARAMS_TYPE))))

        # hide some config keys in user interface which are given as tuple
        EXCLUDED = ('opt_view', 'opt_refo', 'opt_prnt', 'opt_rota', 'opt_dbug', 'opt_colo', 'opt_lier')
        self.gui_keys = [key for key in PROPERTIES.keys() if key not in EXCLUDED]

        # place properties in tk frame
        for i, key in enumerate(self.gui_keys):
            tk.Label(self.frame, text=PROPERTIES[key][0]).grid(row=i, column=0, sticky='W')
            obj_ent = None
            if PROPERTIES[key][1] == 'str':
                self.tk_vars[key] = tk.StringVar(value=self.cfg.params[key])
                obj_ent = tk.Entry(self.frame, textvariable=self.tk_vars[key], width=2*PX)

            elif PROPERTIES[key][1] == 'int':
                self.tk_vars[key] = tk.IntVar(value=int(self.cfg.params[key]))
                obj_ent = tk.Entry(self.frame, textvariable=self.tk_vars[key], width=PX)

            elif PROPERTIES[key][1] == 'list':
                self.tk_vars[key] = tk.StringVar(value=str(self.cfg.params[key]))
                obj_ent = tk.Entry(self.frame, textvariable=self.tk_vars[key], width=PX)

            elif PROPERTIES[key][1] == 'ran':
                self.tk_vars[key] = TwoStringVars(values=self.cfg.params[key])
                obj_ent = DoubleSpinbox(self.frame, textvariable=self.tk_vars[key], width=PX)

            elif PROPERTIES[key][1] == 'sel':
                # load value range
                if key == 'cal_meth':
                    value_ran, default = (c.CALI_METH, c.CALI_METH[0])
                    value_sel = self.cfg.params[self.cfg.cal_meth] if self.cfg.cal_meth in self.cfg.params else default
                elif key == 'ptc_leng':
                    value_ran, default = (c.PTCH_SIZE, c.PTCH_SIZE[2])
                    value_sel = self.cfg.params[self.cfg.ptc_leng] if self.cfg.ptc_leng in self.cfg.params else default
                self.tk_vars[key] = tk.StringVar(value=value_sel)
                obj_ent = tk.Spinbox(self.frame, values=value_ran, textvariable=self.tk_vars[key], width=PX//2)
                self.tk_vars[key].set(value=value_sel)   # set to default necessary for tkinter's spinbox

            elif PROPERTIES[key][1] == 'bool':
                self.tk_vars[key] = tk.BooleanVar(value=bool(self.cfg.params[key]))
                obj_ent = tk.Checkbutton(self.frame, variable=self.tk_vars[key])

            # place entry
            obj_ent.grid(row=i, column=1, sticky='W')

            # display text from most right
            obj_ent.xview_moveto(1.0) if PROPERTIES[key][1] != 'bool' else None

            self.obj_ents[key] = obj_ent

        btn = tk.Button(self.frame, text="Save & Close", width=BTN_W*2, command=self.close)
        btn.grid(row=len(self.gui_keys)+1, columnspan=2, padx=PX, pady=PY)

        # makes sure no mouse or keyboard events are sent to other windows (avoid multiple simultaneous instances)
        self.frame.grab_set()

        # stop all processes until this widget is closed (e.g. self.frame is destroyed)
        self.frame.wait_window()

    def refi(self):

        # set refocus refinement option if scheimpflug focus type is desired
        if self.tk_vars[self.cfg.opt_pflu].get():
            self.tk_vars[self.cfg.opt_refi].set(value=True)
            self.obj_ents[self.cfg.opt_refi].select()
            self.cfg.params[self.cfg.opt_refi] = True

    def save_cfg(self):

        # read from tkinter variables
        for key in self.gui_keys:
            self.cfg.params[key] = self.tk_vars[key].get()
            # set refinement option if scheimpflug option set
            if key == self.cfg.opt_pflu:
                self.refi()

        # write current configuration settings to hard drive
        self.cfg.save_params()

        # load parameters to current config file
        self.cfg.read_params()

    def close(self):
        """ close about window """

        # save configuration settings
        self.save_cfg()

        # destruct frame object
        self.frame.destroy()

        return True


class TwoStringVars(tk.StringVar):

    def __init__(self, master=None, values=('', '')):
        tk.StringVar.__init__(self, master, values)

        self.set(values)

    def get(self):
        one = int(self._one.get())
        two = int(self._two.get())
        return [one, two]

    def set(self, values):
        if len(values) == 2:
            self._one = tk.StringVar(value=str(values[0]))
            self._two = tk.StringVar(value=str(values[1]))
        else:
            raise ValueError('Pass list or tuple of two values only')

    @property
    def one(self):
        return int(self._one.get())

    @property
    def two(self):
        return int(self._two.get())


class DoubleSpinbox(tk.Frame):

    def __init__(self, master=None, textvariable=None, _from=None, to=None, width=None):
        tk.Frame.__init__(self, master)

        self._v = TwoStringVars() if textvariable is None else textvariable
        self._f = -9 if _from is None else _from
        self._t = +9 if to is None else to
        self._width = 5 if width is None else width//2

        self._spinbox_one = tk.Spinbox(self, textvariable=self._v._one, from_=self._f, to=self._t, width=self._width)
        self._spinbox_one.grid(row=0, column=0, sticky='NSW')
        self._spinbox_two = tk.Spinbox(self, textvariable=self._v._two, from_=self._f+1, to=self._t+1, width=self._width)
        self._spinbox_two.grid(row=0, column=1, sticky='NSE')

    def xview_moveto(self, val):
        """ display text from most right """

        self._spinbox_one.xview_moveto(val)
        self._spinbox_two.xview_moveto(val)
