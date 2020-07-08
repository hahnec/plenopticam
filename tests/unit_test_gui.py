#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2020 Christopher Hahne <inbox@christopherhahne.de>

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

import unittest

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus

from plenopticam.gui.widget_about import AbtWidget
from plenopticam.gui.widget_cmnd import CmndWidget
from plenopticam.gui.widget_cnfg import CnfgWidget
from plenopticam.gui.widget_ctrl import CtrlWidget
from plenopticam.gui.widget_file import FileWidget
from plenopticam.gui.widget_menu import MenuWidget
from plenopticam.gui.widget_path import PathWidget
from plenopticam.gui.widget_pbar import PbarWidget
from plenopticam.gui.widget_view import ViewWidget
from plenopticam.gui.top_level import PlenopticamApp
from plenopticam.gui.constants import PX, PY


class TKinterTestCase(unittest.TestCase):
    """These methods are going to be the same for every GUI test,
    so refactored them into a separate class
    """
    def setUp(self):
        self.root = tk.Tk()
        self.cfg = PlenopticamConfig()
        self.sta = PlenopticamStatus()
        self.root.cfg = self.cfg
        self.root.sta = self.sta
        self.pump_events()

    def tearDown(self):
        if self.root:
            self.root.destroy()
            self.pump_events()

    def pump_events(self):
        while self.root.dooneevent(tk._tkinter.ALL_EVENTS | tk._tkinter.DONT_WAIT):
            pass


class PlenoptiCamTesterGui(TKinterTestCase):

    def test_plenopticam_app(self):

        wid = PlenopticamApp()
        self.pump_events()
        wid.destroy()

    def test_about_widget(self):

        wid = AbtWidget()
        self.pump_events()
        wid.abt_widget.destroy()

    def test_cmnd_widget(self):

        wid = CmndWidget(CtrlWidget(self.root))
        self.pump_events()
        wid.destroy()

    def test_cnfg_widget(self):

        wid = CnfgWidget(self.root)
        self.pump_events()

        wid.btn.focus_set()
        wid.btn.event_generate('<Return>')
        wid.destroy()

    def test_ctrl_widget(self):

        wid = CtrlWidget(self.root)
        self.pump_events()
        wid.destroy()

    def test_file_widget(self):

        wid = FileWidget(self.root)
        self.pump_events()
        wid.destroy()

    def test_menu_widget(self):

        wid = MenuWidget(CtrlWidget(self.root))
        self.pump_events()
        wid.destroy()

    def test_path_widget(self):

        wid = PathWidget(self.root)
        self.pump_events()
        wid.destroy()

    def test_pbar_widget(self):

        self.root.sta = self.sta
        wid = PbarWidget(self.root)
        wid.pack(fill='both', expand=True, side='bottom', padx=PX, pady=PY)

        proc_name = 'Test'
        wid.update_stat_msg(proc_name)
        self.assertEqual(proc_name, wid.tk_stat.__getitem__('text'))

        exp_val = 50
        wid.update_prog_bar(exp_val)
        self.assertEqual(exp_val, wid.tk_prog_bar['value'])

        exp_val = 0
        wid.update_prog_msg(exp_val)
        self.assertEqual(str(exp_val)+' %', wid.s.configure("LabeledProgressbar", 'text').strip())

        exp_val = '1'
        wid.update_prog_msg(exp_val)
        self.assertEqual(exp_val, wid.s.configure("LabeledProgressbar", 'text').strip())

        wid.destroy()

    def test_view_widget(self):

        # dummy button with state key
        btn = {'state': 'normal'}

        wid = ViewWidget(self.root, cfg=self.cfg, sta=self.sta, btn=btn)

        # verify view button has been disabled after view widget instantiation
        self.assertEqual(btn['state'], 'disabled')

        self.pump_events()
        wid.btn_mode.focus_set()
        wid.btn_auto.event_generate('<Return>')
        wid.btn_auto.focus_set()
        wid.btn_auto.event_generate('<Return>')
        self.pump_events()

        wid.destroy()

        # verify view button has been enabled
        self.assertEqual(btn['state'], 'normal')

    def test_all(self):

        self.test_plenopticam_app()
        self.test_about_widget()
        self.test_cmnd_widget()
        self.test_cnfg_widget()
        self.test_ctrl_widget()
        self.test_file_widget()
        self.test_menu_widget()
        self.test_path_widget()
        self.test_pbar_widget()
        self.test_view_widget()
