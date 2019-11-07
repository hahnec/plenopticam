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

from plenopticam.cfg import PlenopticamConfig
from plenopticam.misc import PlenopticamStatus
from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.gui.constants import GENERIC_EXTS
from plenopticam import __version__


def get_list(img_dir, vp=1):

    from plenopticam import misc
    import numpy as np

    dir_list = os.listdir(img_dir)
    dir_list.sort()
    img_list = []
    for i in dir_list:
        img_path = os.path.join(img_dir, i)
        ext = img_path.split('.')[::-1][0].lower()
        if ext in [gen_ext.replace('*.', '') for gen_ext in GENERIC_EXTS]:
            img = misc.load_img_file(img_path)
            img_list.append(img)

    if vp:
        vp_dim = int(np.sqrt(len(img_list)))
        img_list = np.asarray(img_list).reshape((vp_dim, vp_dim) + img_list[0].shape)
    else:
        img_tuples = tuple(zip(os.listdir(img_dir), img_list))
        img_tuples = sorted(img_tuples, key=lambda k: int(k[0].split('.')[0]))
        _, img_list = zip(*img_tuples)

    return img_list

# Creating Canvas Widget
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

        # light-field related data
        self._M = self.cfg.params[self.cfg.ptc_leng]    #self.vp_img_arr.shape[0]
        self._v = self._M//2+1
        self._u = self._M//2+1
        self._a = 0

        vp_dir = os.path.join(self.cfg.exp_path, 'viewpoints_'+str(self._M)+'px')
        rf_dir = os.path.join(self.cfg.exp_path, 'refo_'+str(self._M)+'px')
        self.vp_img_arr = kwargs['vp_img_arr'] if 'vp_img_arr' in kwargs else get_list(vp_dir, vp=1)
        self.refo_stack = kwargs['refo_stack'] if 'refo_stack' in kwargs else get_list(rf_dir, vp=0)

        # initialize member variables
        self.vp_mode = True
        self.auto_mode = True
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
        btn_auto_text.set("⭮")
        btn_auto = tk.Button(self, textvariable=btn_auto_text, command=self.auto_play, height=1, width=2)
        btn_auto.place(x=self._wd/2*.05, y=self._ht/2*.05, anchor=tk.CENTER)

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

        k = -1
        move_coords = self.get_move_coords(pattern='circle', arr_dims=self.vp_img_arr.shape[:2])

        while self.auto_mode == True:

            k += 1

            if self.vp_mode:
                self._u, self._v = move_coords[k]
                k = 0 if k == len(move_coords)-1 else k
            else:
                self._a = k
                k = 0 if k == len(self.refo_stack)-1 else k

            self.show_image()

            # wait
            #_ = [_ for _ in range(200000)]

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
