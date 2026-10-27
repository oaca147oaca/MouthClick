"""Alignment layout/lifecycle checks with synthetic pixels and no real devices."""
import ctypes
import tkinter as tk
from unittest.mock import Mock
import numpy as np
from mouthclick_alignment import AlignmentGuide

ctypes.windll.user32.SetProcessDPIAware()
root=tk.Tk()
root.withdraw()
errors=[]
root.report_callback_exception=lambda *args:errors.append(args)
try:
    for scale in (1.3333,1.6667,2.0):
        root.tk.call('tk','scaling',scale)
        calibrate=Mock()
        guide=AlignmentGuide(root,calibrate)
        root.update()
        for i in range(20):
            guide.last_update=0
            guide.update_frame(np.zeros((480,640,3),np.uint8),None)
            root.update()
        assert len(root.tk.call('image','names'))==5
        buttons=[guide.recalibrate_button,guide.close_button]
        for b in buttons:
            assert b.winfo_height()>=40
            assert b.winfo_rooty()+b.winfo_height()<=guide.winfo_rooty()+guide.winfo_height()
        buttons[0].invoke()
        calibrate.assert_called_once()
        guide.unavailable()
        assert guide.photo is None
        guide.destroy()
        root.update()
        assert len(root.tk.call('image','names'))==4
    assert not errors,errors
    print('PASS: guide preview, recalibrate, bounded images, close and layout at three scales')
finally:
    root.destroy()
