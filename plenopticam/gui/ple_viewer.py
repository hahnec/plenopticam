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

from PIL import Image, ImageTk
import os
from functools import partial
import glob

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.gui.constants import GENERIC_EXTS
from plenopticam.misc import Normalizer
from plenopticam import __version__


def idx_str_sort(s, mode=0):

    if mode:
        return [int(s.split('.')[0].split('_')[0]),
                int(s.split('.')[0].split('_')[1])]
    else:
        return int(s.split('.')[0])


def get_list(img_dir, vp=1):

    from plenopticam import misc
    import numpy as np

    dir_list = os.listdir(img_dir)
    dir_list.sort()
    img_list = []
    for i in dir_list:
        img_path = os.path.join(img_dir, i)
        ext = img_path.split('.')[::-1][0].lower()
        if ext in GENERIC_EXTS:

            # load image
            img = misc.load_img_file(img_path)

            # convert to uint8 if necessary
            img = Normalizer(img).uint8_norm() if str(img.dtype) != 'uint8' else img

            # append to image list
            img_list.append((i, img))

    # sort image list by indices in file names
    img_tuples = sorted(img_list, key=lambda k: idx_str_sort(k[0], 1 if vp else 0))
    _, img_list = zip(*img_tuples)

    if vp:
        vp_dim = int(np.sqrt(len(img_list)))
        img_list = np.reshape(img_list, newshape=(vp_dim, vp_dim) + img_list[0].shape, order='C')

    return img_list


class PictureWindow(tk.Canvas, LfpViewpoints):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        LfpViewpoints.__init__(self, *args, **kwargs)

        # app reltated data
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

        # window dimensions
        self._ht = self.winfo_screenheight()
        self._wd = self.winfo_screenwidth()

        vp_dirs = glob.glob(os.path.join(self.cfg.exp_path, 'viewpoints_*px'))
        rf_dirs = glob.glob(os.path.join(self.cfg.exp_path, 'refo_*px'))
        try:
            self.vp_img_arr = kwargs['vp_img_arr'] if 'vp_img_arr' in kwargs else get_list(vp_dirs[0], vp=1)
            self.refo_stack = kwargs['refo_stack'] if 'refo_stack' in kwargs else get_list(rf_dirs[0], vp=0)
        except Exception as e:
            self.sta.status_msg(msg=e, opt=self.cfg.opt_prnt)

        # light-field related data
        self._M = self.vp_img_arr.shape[0]  # self.cfg.params[self.cfg.ptc_leng]
        self._v = self._u = self._M // 2
        self._a = 0
        self._k = -1
        self.move_coords = self.get_move_coords(pattern='circle', arr_dims=self.vp_img_arr.shape[:2])

        # initialize member variables
        self.vp_mode = True
        self.auto_mode = False
        self._mode_text = tk.StringVar()
        self._mode_text.set('VP' if self.vp_mode else 'RF')
        self.all_function_trigger()

        # window settings
        self['bg'] = "white"
        self.master.title("PlenoptiCam Viewer")

        # display initial image
        self.next_frame()

    def show_image(self):

        # set new frame considering view/refo mode
        if self.vp_mode:
            next_frame = self.vp_img_arr[self._v, self._u, ...]
        else:
            next_frame = self.refo_stack[self._a]

        # set tk frame as member variable as it gets lost otherwise
        self.tk_frame = ImageTk.PhotoImage(Image.fromarray(next_frame))

        self.delete(self.find_withtag("bacl"))
        self.allready = self.create_image(self.winfo_screenwidth()/4, self.winfo_screenheight()/4,
                                          image=self.tk_frame, anchor='center', tag="bacl")
        self.find_withtag("bacl")

    def _adapt_coords(self, arg=None):

        arg = -1 if arg is None else arg

        # consider which button was pressed
        if self.vp_mode:
            if arg == 0:
                self._u += 1 if self._u < self._M-1 else 0
            if arg == 1:
                self._u -= 1 if self._u > 0 else 0
            if arg == 2:
                self._v += 1 if self._v < self._M-1 else 0
            if arg == 3:
                self._v -= 1 if self._v > 0 else 0
        else:
            if arg == 0:
                self._a += 1 if self._a < len(self.refo_stack)-1 else 0
            if arg == 1:
                self._a -= 1 if self._a > 0 else 0

        return True

    def next_frame(self, arg=None):

        # compute new light-field positions depending on pressed button
        self._adapt_coords(arg)

        # display new frame
        self.show_image()

        return True

    def all_function_trigger(self):

        self.create_buttons()
        self.window_settings()
        return True

    def window_settings(self):

        self['width'] = self._wd/2
        self['height'] = self._ht/2

        return True

    def create_buttons(self):

        # auto-play button
        btn_auto_text = tk.StringVar()
        btn_auto_text.set("↻")
        self.btn_auto = tk.Button(self, textvariable=btn_auto_text, command=self.auto_play, height=1, width=2)
        self.btn_auto.place(x=self._wd/2*.05, y=self._ht/2*.05, anchor=tk.CENTER)

        # mode button
        self.btn_mode = tk.Button(self, textvariable=self._mode_text, command=self.switch_mode, height=1, width=2)
        self.btn_mode.place(x=self._wd/2*.05, y=self._ht/2*.15, anchor=tk.CENTER)

        # instantiate button objects for light-field
        self.btn_arrows = list()
        btn_pos = [[self._wd/2*.95, self._wd/2*.05, self._wd/4, self._wd/4],
                   [self._ht/4, self._ht/4, self._ht/2*.05, self._ht/2*.95]]
        for i, text in enumerate([" ▶ ", " ◀ ", " ▲ ", " ▼ "]):
            next_frame_arg = partial(self.next_frame, i)
            self.btn_arrows.append(tk.Button(self, text=text, command=next_frame_arg, height=1, width=1))
            self.btn_arrows[i].place(x=btn_pos[0][i], y=btn_pos[1][i], anchor=tk.CENTER)

        return True

    def switch_mode(self):

        # switch mode
        self.vp_mode = not self.vp_mode

        # disable buttons in 1-D mode
        for idx in range(2, 4):
            self.btn_arrows[idx]['state'] = tk.NORMAL if tk.DISABLED else tk.DISABLED

        # alternate button text
        self._mode_text.set('VP' if self.vp_mode else 'RF')
        self.btn_mode.config(textvariable=self._mode_text)

        # reset indices
        self._u, self._v, self._a = (self._M//2+1, self._M//2+1, 0)

        # load image
        self.next_frame()

    def auto_play(self):

        self.auto_mode = not self.auto_mode

        if self.auto_mode:
            #self.btn_auto.focus_set()
            self.btn_auto.configure(bg="green")
        else:
            self.btn_auto.configure(bg="red")

        self.auto_loop()

    def auto_loop(self):

        if self.auto_mode:

            if self.vp_mode:
                self._k = 0 if self._k >= len(self.move_coords) else self._k
                self._u, self._v = self.move_coords[self._k]
                self.after(100, self.auto_loop)
            else:
                self._k = 0 if self._k >= len(self.refo_stack) else self._k
                self._a = self._k
                self.after(1000, self.auto_loop)

            self.show_image()
            self._k += 1

def main():

    # Creating Window
    root = tk.Tk(className="PlenoptiCam Viewer "+__version__)
    # Creating Canvas Widget
    PictureWindow(root).pack(expand="no", fill="both")
    # Not Resizable
    root.resizable(width=0, height=0)
    # Window Mainloop
    root.mainloop()

    return True


if __name__ == '__main__':

    main()
