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
from os.path import join, dirname, abspath, exists
from os import makedirs, utime, listdir

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.misc import rmdir_p, rm_file

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
        self.set_file_path()
        self.pump_events()

    def set_file_path(self):

        # folder and path handling
        self.fp = join(dirname(dirname(abspath(__file__))), 'examples', 'data')
        makedirs(self.fp) if not exists(self.fp) else None
        self.dummy_fn = 'test_dummy.lfp'
        self.dummy_path = join(self.fp, self.dummy_fn)

    def create_dummy_file(self):
        """ create a dummy file for tests """

        # create dummy file with wrong file format
        with open(self.cfg.params[self.cfg.lfp_path], 'a'):
            utime(self.cfg.params[self.cfg.lfp_path], None)

    def remove_dummy_file(self):
        """ remove dummy data after test """

        rm_file(self.cfg.params[self.cfg.lfp_path])
        rmdir_p(self.cfg.exp_path)

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

        # test path fetching
        wid.fil_wid.lfp_wid.ent.delete(0, "end")
        wid.fil_wid.cal_wid.ent.delete(0, "end")
        wid.fil_wid.lfp_wid.ent.insert(0, self.dummy_path)
        wid.fil_wid.cal_wid.ent.insert(0, self.dummy_path)
        self.cfg.params[self.cfg.lfp_path] = ''
        self.cfg.params[self.cfg.cal_path] = ''
        wid.fetch_paths()
        self.assertEqual(self.dummy_path, self.cfg.params[self.cfg.lfp_path])
        self.assertEqual(self.dummy_path, self.cfg.params[self.cfg.cal_path])

        self.pump_events()
        wid.destroy()

    def test_file_widget(self):

        wid = FileWidget(self.root)
        self.pump_events()
        wid.destroy()

    def test_menu_widget(self):

        wid = MenuWidget(CtrlWidget(self.root))
        self.pump_events()
        wid.open_docs()
        wid.open_about_dialog()
        wid.destroy()

    def test_path_widget(self):

        wid = PathWidget(self.root)

        # test getter and setter
        wid.path = self.dummy_path
        self.assertEqual(self.dummy_path, wid.path)

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

        # provide path from previously computed data
        lfp_list = [file for file in listdir(self.fp) if file.endswith(('lfr', 'lfp'))]
        self.cfg.params[self.cfg.lfp_path] = join(self.fp, lfp_list[0])

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
