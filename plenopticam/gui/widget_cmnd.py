try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

from plenopticam.gui.constants import PX, PY, BTN_W

# make object for plot widget
class CmndWidget(tk.Frame):

    def __init__(self, parent):

        # inheritance
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.cfg = parent.cfg
        self.btn_list = []

        # button for light field processing
        run_btn = tk.Button(self, text='Process', width=BTN_W, command=self.parent.process)
        run_btn.grid(row=0, column=0, padx=PX, pady=PY)
        self.btn_list.append(run_btn)

        # button for settings configuration
        cfg_btn = tk.Button(self, text='Settings', width=BTN_W, command=self.parent.cfg_change)
        cfg_btn.grid(row=0, column=1, padx=PX, pady=PY)
        self.btn_list.append(cfg_btn)

        # button to stop/cancel process
        stp_btn = tk.Button(self, text='Stop', width=BTN_W, command=self.parent.stp)
        stp_btn.grid(row=0, column=2, padx=PX, pady=PY)

        # button for application shutdown
        qit_btn = tk.Button(self, text='Quit', width=BTN_W, command=self.parent.qit)
        qit_btn.grid(row=0, column=3, padx=PX, pady=PY)
