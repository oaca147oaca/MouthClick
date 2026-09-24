"""Explicit GUI checks with mock input/audio/persistence. No camera or cursor control."""
import ctypes
from pathlib import Path
import tkinter as tk
from unittest.mock import Mock
from PIL import ImageGrab
from mouthclick_live_ui import LiveSettings
from mouthclick_ui import ActionsBubble
from test_runtime import isolated_app

ctypes.windll.user32.SetProcessDPIAware()
root=tk.Tk()
root.withdraw()
app=isolated_app()
before=app["runtime_snapshot"]()
errors=[]
root.report_callback_exception=lambda *args: errors.append(args)
saved=[]
try:
    for scale in (1.3333,1.6667,2.0):
        root.tk.call("tk","scaling",scale)
        panel=LiveSettings(root,"Test",before,app["apply_runtime_settings"],saved.append,Mock(),lambda:"")
        panel.geometry("760x680")
        root.update()
        for index, page in enumerate(panel.pages):
            panel.show_page(index)
            root.update()
            assert page.winfo_viewable()
            assert sum(p.winfo_viewable() for p in panel.pages)==1
            for control in page.body.winfo_children():
                assert control.winfo_rooty()+control.winfo_height()<=panel.content.winfo_rooty()+panel.content.winfo_height(), (scale,index,control)
        panel.show_page(0)
        panel.vars["gain_x"].set("88.5")
        assert app["REL_GAIN_X"]==88.5
        panel.vars["face_point"].set("Pera / mentón")
        assert app["FACE_POINT"]=="Pera / mentón"
        panel.vars["gain_y"].set("not a number")
        panel.commit()
        assert panel.winfo_exists() and not saved
        panel.discard()
        assert app["runtime_snapshot"]()==before
        panel=LiveSettings(root,"Test",before,app["apply_runtime_settings"],saved.append,Mock(),lambda:"")
        panel.vars["gain_x"].set("81.25")
        panel.vars["face_point"].set("Entrecejo")
        root.update()
        if scale==1.3333:
            Path('.visual-build').mkdir(exist_ok=True)
            x,y=panel.winfo_rootx(),panel.winfo_rooty()
            ImageGrab.grab(bbox=(x,y,x+panel.winfo_width(),y+panel.winfo_height())).save('.visual-build/live-settings.png')
        panel.commit()
        assert saved[-1]["gain_x"]==81.25 and saved[-1]["face_point"]=="Entrecejo"
        app["apply_runtime_settings"](before)
        saved.clear()
        items=[(name,Mock()) for name in ["Esc","Click","Derecho","Drag","Teclado","Sensibilidades","Calib","Centro","Pausa","Salir"]]
        bubble=ActionsBubble(root,items,None,Mock(),Mock(),Mock())
        bubble.expand()
        bubble.set_status("ACTIVO · Punta de nariz")
        root.update()
        assert bubble.winfo_viewable()
        bubble.set_paused(True)
        assert bubble.pause_button.cget('text')=='Continuar'
        bubble.set_paused(False)
        assert bubble.pause_button.cget('text')=='Pausar'
        for b in bubble.action_buttons:
            assert b.winfo_height()>=40,(scale,b.cget('text'),b.winfo_height())
            assert b.winfo_rooty()+b.winfo_height()<=bubble.winfo_rooty()+bubble.winfo_height()
            b.invoke()
        assert all(callback.call_count==1 for _,callback in items)
        bubble.destroy()
    assert not errors,errors
    print('PASS: eight pages, preview, validation, cancel, save and ten bubble actions at 100/125/150%')
finally:
    root.destroy()
