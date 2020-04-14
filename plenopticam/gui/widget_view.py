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

from PIL import Image, ImageTk, ImageFont, ImageDraw
import os
from functools import partial
import glob
import numpy as np

from plenopticam.lfp_extractor import LfpViewpoints
from plenopticam.gui.constants import GENERIC_EXTS
from plenopticam.misc import Normalizer, load_img_file
from plenopticam import __version__
from plenopticam.gui.constants import PX, PY


def idx_str_sort(s, mode=0):
    '''  '''

    if mode:
        return [int(s.split('.')[0].split('_')[0]),
                int(s.split('.')[0].split('_')[1])]
    else:
        return int(s.split('.')[0])


def get_img_list(img_dir, vp=1):
    ''' obtain list of images from provided directory path '''

    dir_list = os.listdir(img_dir)
    dir_list.sort()
    img_list = []
    for i in dir_list:
        img_path = os.path.join(img_dir, i)
        ext = img_path.split('.')[::-1][0].lower()
        if ext in GENERIC_EXTS:

            # load image
            img = load_img_file(img_path)

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


class ViewWidget(tk.Canvas, LfpViewpoints):

    def __init__(self, *args, **kwargs):

        # use button status for enabling/disabling purposes
        self.btn = kwargs['btn'] if 'btn' in kwargs else {'state': 'normal'}
        kwargs.pop('btn') if 'btn' in kwargs else None
        self.btn['state'] = tk.DISABLED

        LfpViewpoints.__init__(self, *args, **kwargs)
        kwargs.pop('cfg') if 'cfg' in kwargs else None
        kwargs.pop('sta') if 'sta' in kwargs else None

        tk.Canvas.__init__(self, *args, **kwargs)

        # window settings
        self['bg'] = "white"
        self.master.title("PlenoptiCam Viewer")

        # take images from arguments or load from hard drive
        if 'vp_img_arr' in kwargs and 'refo_stack' in kwargs:
            self.vp_img_arr = kwargs['vp_img_arr']
            self.refo_stack = kwargs['refo_stack']
        else:
            self.load_data()

        # window dimensions
        self.shape = self.vp_img_arr.shape[2:] if self.vp_img_arr is not None else (200, 200, 1)
        self._ht = self.shape[0]*2 + PY*11         #self.winfo_screenheight()
        self._wd = self.shape[1]*2 + PX*15        #self.winfo_screenwidth()

        # light-field related data
        self._M = self.vp_img_arr.shape[0] if self.vp_img_arr is not None else self._M
        self.reset_indices()
        if self.vp_img_arr is not None:
            self.move_coords = self.get_move_coords(pattern='circle', arr_dims=self.vp_img_arr.shape[:2])

        # initialize member variables
        self.vp_mode = True
        self.auto_mode = False
        self._mode_text = tk.StringVar()
        self._mode_text.set('VP' if self.vp_mode else 'RF')
        self.all_function_trigger()

        # display initial image
        self.show_next_frame()

        # start with auto play mode
        self.auto_play()

    def load_data(self):
        ''' automatically look for output folders and load light field content '''

        # load list of potential directories
        vp_dirs = glob.glob(os.path.join(self.cfg.exp_path, 'viewpoints_*px'))
        rf_dirs = glob.glob(os.path.join(self.cfg.exp_path, 'refo_*px'))

        # exclude up-sampled refocused images (due to oversize)
        terms = ['upscale_']
        rf_dirs = [dir for substr in terms for dir in rf_dirs if not os.path.basename(dir).__contains__(substr)]

        # load data
        self.vp_img_arr = self.select_from_dir(vp_dirs, vp=1)
        self.refo_stack = self.select_from_dir(rf_dirs, vp=0)

        return True

    def select_from_dir(self, dirs, vp=None):

        # select current micro image size
        size_idx = 0
        for i, s in enumerate(dirs):
            size = int(s.split('_')[-1][:-2])
            if size == self.cfg.params[self.cfg.ptc_leng]:
                size_idx = i
                break

        # load image list
        try:
            ret_val = get_img_list(dirs[size_idx], vp=vp)
        except IndexError:
            ret_val = None

        return ret_val

    def show_image(self):

        # set new frame considering view/refo mode
        if self.vp_mode and self.vp_img_arr is not None:
            next_frame = Image.fromarray(self.vp_img_arr[self._v, self._u, ...])
        elif self.refo_stack is not None:
            next_frame = Image.fromarray(self.refo_stack[self._a])
        else:
            # display text message about missing image data
            next_frame = self.get_dummy

        # set tk frame as member variable as it gets lost otherwise
        self.tk_frame = ImageTk.PhotoImage(next_frame)

        self.delete(self.find_withtag("bacl"))
        self.allready = self.create_image(PX*4, PY*3, image=self.tk_frame, anchor=tk.NW, tag="bacl")
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

    def show_next_frame(self, arg=None):

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
        self._btn_auto_text = tk.StringVar()
        self._btn_auto_text.set('↻')
        self.btn_auto = tk.Button(self, textvariable=self._btn_auto_text, command=self.auto_play, height=1, width=2)
        self.btn_auto.place(x=PX, y=PY/2, anchor=tk.NW)

        # mode button
        self.btn_mode = tk.Button(self, textvariable=self._mode_text, command=self.switch_mode, height=1, width=2)
        self.btn_mode.place(x=PX, y=PY*3, anchor=tk.NW)

        # instantiate button objects for light-field
        self.btn_arrows = list()
        btn_pos = [[self.shape[1]+PX*4.5, PX*2, self._wd/4, self._wd/4],
                   [self._ht/4, self._ht/4, PY/2, self.shape[0]+PY*3.5]]
        for i, text in enumerate([' ▶ ', ' ◀ ', ' ▲ ', ' ▼ ']):
            next_frame_arg = partial(self.show_next_frame, i)
            self.btn_arrows.append(tk.Button(self, text=text, command=next_frame_arg, height=1, width=1))
            self.btn_arrows[i].place(x=btn_pos[0][i], y=btn_pos[1][i], anchor=tk.NW)

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
        self.reset_indices()

        # load image
        self.show_next_frame()

    def reset_indices(self):
        self._u, self._v, self._a, self._k, self._h = (self._M // 2 + 1, self._M // 2 + 1, -1, 0, 1)

    def auto_play(self):

        self.auto_mode = not self.auto_mode

        if self.auto_mode:
            self._btn_auto_text.set('❙❙')
        else:
            self._btn_auto_text.set('↻')

        self.auto_loop()

    def auto_loop(self):

        if self.auto_mode:

            if self.vp_mode and self.vp_img_arr is not None:

                # use k index for coordinate iteration of viewpoints
                self._k = 0 if self._k >= len(self.move_coords) else self._k
                self._u, self._v = self.move_coords[self._k]

                # wait some time before showing next image
                self.after(100, self.auto_loop)
                self.show_image()

            elif self.refo_stack is not None:

                # use k and h indices for forward and backward iteration of refocusing slice index a
                self._k, self._h = (0, -self._h) if self._k >= len(self.refo_stack) else (self._k, self._h)
                self._a = self._k*self._h if self._k != 0 or self._h > 0 else -1

                # wait some time before showing next image
                self.after(500, self.auto_loop)
                self.show_image()

            self._k += 1

    def destroy(self):
        ''' override close window event '''

        # prevent loop iteration from running after window closure
        self.auto_mode = False

        # reset button status once window is closed
        self.btn['state'] = tk.NORMAL

    @property
    def get_dummy(self):
        ''' create notification image '''

        # disable auto play mode
        self.auto_mode = False
        self._btn_auto_text.set('↻')

        # create notification image
        text = "No valid %s image data found" % ('viewpoint' if self.vp_mode else 'refocused')
        font = ImageFont.truetype("Arial.ttf", 12)
        img = Image.new("RGBA", self.shape[:2][::-1], color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = draw.textsize(text, font)
        draw.text(((self.shape[1] - w) / 2, (self.shape[0] - h) / 2), text, fill=(0, 0, 0), font=font)
        ImageDraw.Draw(img)

        return img


def main():

    # creating window
    root = tk.Tk(className="PlenoptiCam Viewer "+__version__)
    # creating canvas widget
    ViewWidget(root).pack(expand="no", fill="both")
    # make not resizable
    root.resizable(width=0, height=0)
    # window mainloop
    root.mainloop()

    return True


if __name__ == '__main__':

    main()
