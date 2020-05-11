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
from os.path import join, splitext, basename
import threading
import queue
import types
import os

# local python files
from plenopticam.gui.constants import PX, PY
from plenopticam.gui.widget_menu import MenuWidget
from plenopticam.gui.widget_file import FileWidget
from plenopticam.gui.widget_cmnd import CmndWidget
from plenopticam.gui.widget_cnfg import CnfgWidget
from plenopticam.gui.widget_view import ViewWidget
from plenopticam.cfg import PlenopticamConfig
from plenopticam import misc

from plenopticam import lfp_calibrator
from plenopticam import lfp_aligner
from plenopticam import lfp_reader
from plenopticam import lfp_extractor
from plenopticam import lfp_refocuser

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

        self.all_btn_list = self.fil_wid.btn_list + self.men_wid.btn_list + self.cmd_wid.btn_list[:2]

        self.var_init()

    def var_init(self):

        # image variables
        self.lfp_img = None
        self.wht_img = None
        self.lfp_img_align = None
        self.vp_img_arr = None

        # threading
        self.sta.interrupt = False
        self.sta.error = False
        self.job_queue = queue.Queue()
        self.cur_thread = None

        # remove viewer window (if present)
        self.view_frame.destroy() if hasattr(self, 'view_frame') else None

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

        # reset calibration metadata path
        self.cfg.params[self.cfg.cal_meta] = ''

        # save config to hard drive
        self.cfg.save_params()

    def start_thread(self, func, cond, *args):

        # return value of bound method conditions
        cond = cond() if isinstance(cond, types.MethodType) else cond

        # start next thread if condition is met
        if cond and self.cur_thread is None:
            self.cur_thread = PropagatingThread(target=func, args=args, cfg=self.cfg, sta=self.sta)
            self.cur_thread.start()

    def stop_thread(self):

        #self.cur_thread.join(POLLING_RATE) if self.cur_thread else None

        while not self.job_queue.empty():
            self.job_queue.get(block=True, timeout=POLLING_RATE)
            self.job_queue.task_done()

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
            self.toggle_btn_list(self.all_btn_list)
            # step out of loop
            return True

        self.after(POLLING_RATE, self.poll)

    def process(self):

        # reset
        self.var_init()

        # status update
        self.sta.status_msg('Loading data', self.cfg.params[self.cfg.opt_prnt])
        self.sta.progress(None, self.cfg.params[self.cfg.opt_prnt])

        # disable button activity
        self.toggle_btn_list(self.all_btn_list)
        self.cmd_wid.btn_list[3].config(text='Stop')

        # read light field photo and calibration source paths
        self.fetch_paths()

        # remove output folder if option is set
        misc.rmdir_p(self.cfg.exp_path) if self.cfg.params[self.cfg.dir_remo] else None

        # remove calibrated light-field if calibration or devignetting option is set
        if self.cfg.params[self.cfg.opt_cali] or self.cfg.params[self.cfg.opt_vign]:
            misc.rm_file(join(self.cfg.exp_path, 'lfp_img_align.pkl'))
            if self.cfg.params[self.cfg.opt_cali]:
                misc.rm_file(self.cfg.params[self.cfg.cal_meta])

        # create output data folder (prevent override)
        misc.mkdir_p(self.cfg.exp_path, self.cfg.params[self.cfg.opt_prnt])

        # put tasks in the job queue to be run
        for task_info in (
                         (self.load_lfp, self.cfg.cond_load_limg, self.cfg.params[self.cfg.lfp_path]),
                         (self.auto_find, self.cfg.cond_auto_find),
                         (self.load_lfp, self.cfg.cond_load_wimg, self.cfg.params[self.cfg.cal_path], True),
                         (self.cal, self.cfg.cond_perf_cali),
                         (self.cfg.load_cal_data, self.cfg.cond_lfp_align),
                         (self.lfp_align, self.cfg.cond_lfp_align),
                         (self.load_pickle_file, True),
                         (self.lfp_extract, True),
                         (self.lfp_refo, self.cfg.params[self.cfg.opt_refo]),
                         (self.finish, True)
                         ):
            self.job_queue.put(task_info)

        # start polling
        self.after(POLLING_RATE, self.poll)

        # cancel if file paths not provided
        self.sta.validate(checklist=[self.cfg.params[self.cfg.lfp_path], self.cfg.params[self.cfg.cal_path]],
                          msg='Canceled due to missing image file path')

    def finish(self):
        """ procedure for finished process """

        self.sta.status_msg('Export finished', opt=True)
        self.sta.progress(100, opt=True)

        # open viewer window
        self.view()

        # set button to quit
        self.cmd_wid.btn_list[3].config(text='Quit')

    def lfp_refo(self):

        obj = lfp_refocuser.LfpRefocuser(self.vp_img_arr, cfg=self.cfg, sta=self.sta)
        obj.main()
        del obj

    def lfp_align(self):

        # align light field
        lfp_obj = lfp_aligner.LfpAligner(self.lfp_img, self.cfg, self.sta, self.wht_img)
        lfp_obj.main()
        self.lfp_img_align = lfp_obj.lfp_img
        del lfp_obj

    def load_pickle_file(self):

        # file path
        fp = join(self.cfg.exp_path, 'lfp_img_align.pkl')

        try:
            # load previously computed light field alignment
            self.lfp_img_align = pickle.load(open(fp, 'rb'))
        except EOFError:
            os.remove(fp)
        except FileNotFoundError:
            return False

        # load LFP metadata settings (for Lytro files only)
        fp = join(self.cfg.exp_path, splitext(basename(self.cfg.params[self.cfg.lfp_path]))[0]+'.json')
        if os.path.isfile(fp):
            json_dict = self.cfg.load_json(fp=fp, sta=None)
            from plenopticam.lfp_reader.lfp_decoder import LfpDecoder
            self.cfg.lfpimg = LfpDecoder().filter_lfp_json(json_dict, settings=self.cfg.lfpimg)

    def lfp_extract(self):

        # export light field data
        exp_obj = lfp_extractor.LfpExtractor(self.lfp_img_align, self.cfg, self.sta)
        exp_obj.main()
        self.vp_img_arr = exp_obj.vp_img_arr
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
            self.wht_img = obj._wht_bay
            del obj

        # white image demosaicing (when light field image is given as RGB)
        if self.wht_img is not None and len(self.lfp_img.shape) == 3:
            from plenopticam.lfp_aligner.cfa_processor import CfaProcessor
            cfa_obj = CfaProcessor(bay_img=self.wht_img, cfg=self.cfg, sta=self.sta)
            cfa_obj.bay2rgb()
            self.wht_img = cfa_obj.rgb_img
            del cfa_obj

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
        self.toggle_btn_list(self.cmd_wid.btn_list[:2])

        # create settings frame
        CnfgWidget(self.cfg)

        # enable buttons
        self.toggle_btn_list(self.cmd_wid.btn_list[:2])

    def exit(self):
        """ this exit function is connected to most-right menu button triggering either stop or quit """

        if self.cmd_wid.btn_list[3].cget('text') == 'Quit':
            self.quit()
        else:
            self.cmd_wid.btn_list[3].config(text='Quit')
            self.stop()

    def stop(self):
        """ stop app """

        # set interrupt in status
        self.sta.interrupt = True

    def quit(self):
        """ quit app """

        self.stop_thread()

        # destroy tkinter objects
        self.view_frame.destroy() if hasattr(self, 'view_frame') else None
        self.parent.destroy()

        sys.exit()

    def view(self):
        """ open viewer """

        # disable button activity (prevent a sequence of clicks to create several view windows)
        self.toggle_btn_state(self.cmd_wid.btn_list[2])

        view_thread = PropagatingThread(target=self.instantiate_viewer, args=[self.cmd_wid.btn_list[2]], cfg=self.cfg, sta=self.sta)
        view_thread.start()

    def instantiate_viewer(self, btn):

        self.view_frame = tk.Toplevel(padx=PX, pady=PY)  # open window
        self.view_frame.resizable(width=0, height=0)     # make window not resizable
        ViewWidget(self.view_frame, cfg=self.cfg, sta=self.sta, btn=btn).pack(expand="no", fill="both")


class PropagatingThread(threading.Thread):
    """ Child threading class for exception handling and error traceback """

    def __init__(self, cfg=None, sta=None, *args, **kwargs):
        super(PropagatingThread, self).__init__(*args, **kwargs)

        # init
        self.cfg = cfg if cfg is not None else PlenopticamConfig()
        self.sta = sta if sta is not None else misc.PlenopticamStatus()
        self.exc = None
        self.ret = None

    def run(self):

        if hasattr(self, '_Thread__target'):
            # Thread uses name mangling prior to Python 3.
            self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
        else:
            self.ret = self._target(*self._args, **self._kwargs)
            self.sta.stat_var = 'Stopped' if self.sta.interrupt and not self.sta._error else self.sta.stat_var

    def join(self, timeout=None):
        super(PropagatingThread, self).join()
        if self.exc:
            raise misc.errors.PlenopticamError(self.exc, cfg=self.cfg, sta=self.sta)
        return self.ret
