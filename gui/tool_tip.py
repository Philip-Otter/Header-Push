import tkinter as tk
from tkinter import ttk

class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')

    def show(self, _=None):
        if self.window or not self.text:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(
            f'+{self.widget.winfo_rootx()+20}+{self.widget.winfo_rooty()+self.widget.winfo_height()+8}')
        ttk.Label(self.window, text=self.text, justify='left', padding=(
            8, 5), relief='solid', borderwidth=1, wraplength=420).pack()

    def hide(self, _=None):
        if self.window:
            self.window.destroy()
            self.window = None