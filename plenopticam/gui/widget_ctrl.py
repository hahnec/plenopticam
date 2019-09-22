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

import sys
import pickle
from os.path import join, dirname, exists, isdir
import threading
import queue
import types
import os
import traceback

# local python files
from plenopticam.gui.constants import PX, PY
from plenopticam.gui.widget_menu import MenuWidget
from plenopticam.gui.widget_file import FileWidget
from plenopticam.gui.widget_cmnd import CmndWidget
from plenopticam.gui.widget_cnfg import CnfgWidget
from plenopticam.cfg import PlenopticamConfig
from plenopticam import misc

from plenopticam import lfp_calibrator
from plenopticam import lfp_aligner
from plenopticam import lfp_reader
from plenopticam import lfp_extractor

# constants
POLLING_RATE = 100  # millisecs

class CtrlWidget(tk.Frame):
    ''' Control widget class '''

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent

        # instantiate status
        self.sta = parent.sta
        self.sta.bind_to_interrupt(self.stop_thread)

        # instantiate config settings
        self.cfg = PlenopticamConfig()

        # instantiate menu widget
        self.men_wid = MenuWidget(self)
        self.men_wid.grid()

        # instantiate config widget
        self.fil_wid = FileWidget(self)
        self.fil_wid.grid(padx=PX, pady=PY)

        # instantiate command widget
        self.cmd_wid = CmndWidget(self)
        self.cmd_wid.grid(padx=PX, pady=PY)

        self.var_init()

    def var_init(self):

        # image variables
        self.lfp_img = None
        self.wht_img = None
        self.lfp_img_align = None

        # threading
        self.job_queue = queue.Queue()
        self.cur_thread = None

    def fetch_paths(self):

        # compare config path with path in user interface (detect change)
        if self.fil_wid.lfp_wid.ent.get() != self.cfg.params[self.cfg.lfp_path]:
            # pass path to config
            self.cfg.params[self.cfg.lfp_path] = self.fil_wid.lfp_wid.path
            # reset light field image
            self.lfp_img = None

        # compare config path with path in user interface (detect change)
        if self.fil_wid.cal_wid.ent.get() != self.cfg.params[self.cfg.cal_path]:
            # pass path to config
            self.cfg.params[self.cfg.cal_path] = self.fil_wid.cal_wid.path
            # reset calibration image
            self.wht_img = None

        # reset calibration metadata path (if roots in paths do not match)
        if dirname(dirname(self.cfg.params[self.cfg.cal_meta])) not in dirname(self.cfg.params[self.cfg.cal_path]):
            self.cfg.params[self.cfg.cal_meta] = ''

        # save config to hard drive
        self.cfg.save_params()

    def start_thread(self, func, cond, *args):

        # return value of bound method conditions
        cond = cond() if isinstance(cond, types.MethodType) else cond

        # start next thread if condition is met
        if cond and self.cur_thread is None:
            self.cur_thread = PropagatingThread(target=func, args=args)
            self.cur_thread.start()

    def stop_thread(self):

        #self.cur_thread.join(POLLING_RATE) if self.cur_thread else None

        while not self.job_queue.empty():
            self.job_queue.get(block=True, timeout=POLLING_RATE)
            self.job_queue.task_done()

        # reset member variables
        self.var_init()

    def poll(self):

        if self.cur_thread is not None:
            if not self.cur_thread.is_alive():
                self.cur_thread.join()
                self.cur_thread = None
        # any more jobs to do?
        elif not self.job_queue.empty():
            try:
                job_info = self.job_queue.get_nowait()  # non-blocking
                self.start_thread(*job_info)
            except queue.Empty:
                pass

        elif self.job_queue.empty() and self.cur_thread is None:
            # enable button activity
            self.toggle_btn_list(self.cmd_wid.btn_list+self.fil_wid.btn_list)
            # step out of loop
            return True

        self.after(POLLING_RATE, self.poll)

    def process(self):

        # status update
        self.sta.status_msg('Starting ...', self.cfg.params[self.cfg.opt_dbug])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_dbug])

        # reset
        self.var_init()
        self.sta.interrupt = False

        # disable button activity
        self.toggle_btn_list(self.cmd_wid.btn_list+self.fil_wid.btn_list)

        # read light field photo and calibration source paths
        self.fetch_paths()

        # remove output folder if option is set
        misc.rmdir_p(self.cfg.params[self.cfg.lfp_path].split('.')[0]) if self.cfg.params[self.cfg.dir_remo] else None

        # remove calibrated light-field if calibration option is set
        if self.cfg.params[self.cfg.opt_cali]:
            misc.rmdir_p(join(self.cfg.params[self.cfg.lfp_path].split('.')[0], 'lfp_img_align.pkl'))
            misc.rmdir_p(self.cfg.params[self.cfg.cal_meta])

        # create output data folder
        misc.mkdir_p(self.cfg.params[self.cfg.lfp_path].split('.')[0], self.cfg.params[self.cfg.opt_prnt])

        # put tasks in the job queue to be run
        for task_info in (
                         (self.load_lfp, self.cfg.cond_load_limg, self.cfg.params[self.cfg.lfp_path]),
                         (self.auto_find, self.cfg.cond_auto_find),
                         (self.load_lfp, self.cfg.cond_load_wimg, self.cfg.params[self.cfg.cal_path], True),
                         (self.cal, self.cfg.cond_perf_cali),
                         (self.cfg.load_cal_data, self.cfg.cond_lfp_align),
                         (self.lfp_align, self.cfg.cond_lfp_align),
                         (self.load_pickle_file, True),
                         (self.lfp_extract, True)
                        ):
            self.job_queue.put(task_info)

        # start polling
        self.after(POLLING_RATE, self.poll)

        # cancel if file paths not provided
        self.sta.validate(checklist=[self.cfg.params[self.cfg.lfp_path], self.cfg.params[self.cfg.cal_path]],
                          msg='Canceled due to missing image file path')

    def lfp_align(self):

        # align light field
        lfp_obj = lfp_aligner.LfpAligner(self.lfp_img, self.cfg, self.sta, self.wht_img)
        lfp_obj.main()
        self.lfp_img_align = lfp_obj.lfp_img
        del lfp_obj

    def load_pickle_file(self):

        # file path
        fp = join(self.cfg.params[self.cfg.lfp_path].split('.')[0], 'lfp_img_align.pkl')

        try:
            # load previously computed light field alignment
            self.lfp_img_align = pickle.load(open(fp, 'rb'))
        except EOFError:
            os.remove(fp)

    def lfp_extract(self):

        # export light field data
        exp_obj = lfp_extractor.LfpExtractor(self.lfp_img_align, self.cfg, self.sta)
        exp_obj.main()
        del exp_obj

    def cal(self):

        # perform centroid calibration
        cal_obj = lfp_calibrator.LfpCalibrator(self.wht_img, self.cfg, self.sta)
        cal_obj.main()
        self.cfg = cal_obj.cfg
        del cal_obj

    def auto_find(self):

        if self.wht_img is None:
            # find calibration file automatically
            obj = lfp_calibrator.CaliFinder(self.cfg, self.sta)
            obj.main()
            self.wht_img = obj._wht_img
            del obj

    def load_lfp(self, lfp_path=None, wht_opt=False):

        # decode light field image
        lfp_obj = lfp_reader.LfpReader(cfg=self.cfg, sta=self.sta, lfp_path=lfp_path)
        lfp_obj.main()
        if wht_opt:
            self.wht_img = lfp_obj.lfp_img
        else:
            self.lfp_img = lfp_obj.lfp_img
        del lfp_obj

    @staticmethod
    def toggle_btn_state(btn):

        btn['state'] = tk.DISABLED if btn['state'] != tk.DISABLED else tk.NORMAL

    @classmethod
    def toggle_btn_list(cls, btn_list):

        for btn in btn_list:
            cls.toggle_btn_state(btn)

    def cfg_change(self):

        # disable button activity
        self.toggle_btn_list(self.cmd_wid.btn_list+self.fil_wid.btn_list)

        # create settings frame
        CnfgWidget(self.cfg)

        # enable buttons
        self.toggle_btn_list(self.cmd_wid.btn_list+self.fil_wid.btn_list)

    def stp(self):
        ''' stop app '''

        # set interrupt in status
        self.sta.interrupt = True

    def qit(self):
        ''' quit app '''

        self.stop_thread()

        # destroy tkinter object
        self.parent.destroy()
        sys.exit()


class PropagatingThread(threading.Thread):
    ''' Child threading class for exception handling and error traceback '''

    def __init__(self, cfg=None, sta=None, *args, **kwargs):
        super(PropagatingThread, self).__init__(*args, **kwargs)
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else misc.PlenopticamStatus()

    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except Exception:
            self.exc = traceback.format_exc()

    def join(self):
        super(PropagatingThread, self).join()
        if self.exc:
            raise misc.errors.PlenopticamError(self.exc, cfg=self.cfg, sta=self.sta)
        return self.ret