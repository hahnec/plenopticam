try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

import os

from plenopticam.gui.widget_path import PathWidget
from plenopticam.gui.constants import PX, PY

class FileWidget(tk.Frame):

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.cfg = parent.cfg

        # supported file extensions
        LFP_EXTS = [('Generic image files', '*.bmp *.png *.tiff *.jpeg *.jpg'), ('Lytro files', '*.lfp *.lfr *.raw')]
        CAL_EXTS = [('Generic image files', '*.bmp *.png *.tiff *.jpeg *.jpg'), ('Lytro files', '*.tar *.raw')]

        # instantiate light field path widget
        tk.Label(self, text='Light field image: ').grid(row=0, column=0, sticky='W')
        self.lfp_wid = PathWidget(self, path=self.cfg.params[self.cfg.lfp_path], path_type=False, file_exts=LFP_EXTS)
        self.lfp_wid.grid(row=0, column=1, padx=PX, pady=PY)
        self.lfp_wid.bind_to(self.set_lfp_path)     # observe change in path variable

        # instantiate calibration path widget
        tk.Label(self, text='Calibration source: ').grid(row=1, column=0, sticky='W')
        self.cal_wid = PathWidget(self, path=self.cfg.params[self.cfg.cal_path], path_type=False, file_exts=CAL_EXTS)
        self.cal_wid.grid(row=1, column=1, padx=PX, pady=PY)
        self.cal_wid.bind_to(self.set_cal_path)     # observe change in path variable

        # radio button to enable change from path to file type
        self.cal_wid.path_type = os.path.isdir(self.cfg.params[self.cfg.cal_path])
        self.chk_var = tk.BooleanVar(value=bool(self.cal_wid.path_type))
        self.chk_btn = tk.Checkbutton(self, text='Pick folder', variable=self.chk_var, command=self.btn_update)
        self.chk_btn.grid(row=1, column=2, sticky='W')

    def btn_update(self):
        # toggle path type in PathWidget for calibration
        self.cal_wid.path_type = not self.cal_wid.path_type

    def set_lfp_path(self, val):

        self.cfg.params[self.cfg.lfp_path] = val
        self.cfg.save_params()

    def set_cal_path(self, val):

        self.cfg.params[self.cfg.cal_path] = val
        self.cfg.save_params()