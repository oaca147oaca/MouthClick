"""Explicit GUI checks with mock input/audio/persistence. No camera or cursor control."""
import ctypes
from pathlib import Path
import tkinter as tk
from unittest.mock import Mock
from PIL import ImageGrab
from mouthclick_live_ui import LiveSettings, ConfirmAction
from mouthclick_ui import ActionsBubble, toggle
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
        check_window=tk.Toplevel(root)
        check_window.geometry('600x120')
        value=tk.BooleanVar(root,value=False)
        check=toggle(check_window,'Texto completo que activa la opción',value)
        root.update()
        for x in (80,check.winfo_width()-12):
            check.event_generate('<ButtonPress-1>',x=x,y=20)
            check.event_generate('<ButtonRelease-1>',x=x,y=20)
            root.update()
            assert value.get()
            check.invoke()
        check_window.destroy()
        panel=LiveSettings(root,"Test",before,app["apply_runtime_settings"],saved.append,Mock(),lambda:"")
        root.update()
        assert panel.overrideredirect()
        assert panel.winfo_width()==panel.winfo_screenwidth()
        panel.chrome.toggle()
        root.update()
        assert not panel.chrome.maximized
        panel.chrome.toggle()
        root.update()
        panel.chrome.minimize()
        root.update()
        assert panel.state()=='iconic'
        panel.deiconify()
        root.update()
        assert panel.overrideredirect()
        panel.geometry("760x680")
        root.update()
        for index, page in enumerate(panel.pages):
            panel.show_page(index)
            root.update()
            assert page.winfo_viewable()
            assert sum(p.winfo_viewable() for p in panel.pages)==1
            for control in [w for card in page.cards for w in card.body.winfo_children()]:
                assert control.winfo_rooty()+control.winfo_height()<=panel.content.winfo_rooty()+panel.content.winfo_height(), (scale,index,control)
        panel.show_page(0)
        panel.vars["gain_x"].set("88.5")
        assert app["REL_GAIN_X"]==88.5
        assert panel.level_vars['gain_x'].get()=='Personalizada'
        panel.show_page(2)
        panel.show_page(0)
        assert app['REL_GAIN_X']==88.5
        panel.level_vars['gain_x'].set('alta')
        panel.select_level('gain_x')
        assert app['REL_GAIN_X']==74.0
        panel.vars['gain_x'].set('88.5')
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
        items=[(name,Mock()) for name in ["Drag","Oficina","Teclado","Sensibilidades","Menú principal","Posición cámara","Calib","Centro","Pausa","Salir"]]
        bubble=ActionsBubble(root,items,None,Mock(),Mock(),Mock())
        bubble.expand()
        bubble.set_status("ACTIVO · Punta de nariz")
        root.update()
        assert bubble.winfo_viewable()
        app["tk"] = tk
        app["floating_keyboard_root"] = root
        app["floating_actions_root"] = bubble
        app["remember_keyboard_target"] = Mock()
        app["update_keyboard_move_mode"] = Mock()
        app["last_bubble_check"] = 0
        bubble.withdraw()
        app["update_floating_keyboard"]()
        root.update()
        assert bubble.winfo_viewable()
        assert bubble.attributes('-topmost')
        bubble.set_paused(True)
        assert bubble.pause_button.cget('text')=='Continuar'
        bubble.set_paused(False)
        assert bubble.pause_button.cget('text')=='Pausar'
        bubble.set_modes(True,False)
        assert 'ON' in bubble.mode_buttons['Drag'].cget('text')
        bubble.set_modes(False,True)
        assert 'ON' in bubble.mode_buttons['Oficina'].cget('text')
        from mouthclick_ui import COLORS
        from types import SimpleNamespace
        active = bubble.mode_buttons['Oficina']
        active.event_generate('<Enter>')
        active.event_generate('<Leave>')
        root.update()
        assert active.cget('bg') == COLORS['red']
        event = SimpleNamespace(x_root=bubble.winfo_x()+25,y_root=bubble.winfo_y()+25)
        bubble._drag_start(event)
        bubble._drag_end(event)
        assert bubble.moving
        bubble.collapse_now()
        assert bubble.expanded
        bubble.stop_moving()
        assert not bubble.moving
        bubble._drag_start(event)
        bubble._drag(SimpleNamespace(x_root=250,y_root=250))
        bubble._drag_end(event)
        assert not bubble.moving
        for b in bubble.action_buttons:
            assert b.winfo_height()>=40,(scale,b.cget('text'),b.winfo_height())
            assert b.winfo_rooty()+b.winfo_height()<=bubble.winfo_rooty()+bubble.winfo_height()
            b.invoke()
        assert all(callback.call_count==1 for _,callback in items)
        bubble.destroy()
        accepted=Mock()
        dialog=ConfirmAction(root,'¿Cerrar MouthClick?', 'Para volver a usar el control facial necesitarás abrir la app con ayuda o un dispositivo físico. Guardá tus ajustes antes de salir.',accepted)
        root.update()
        assert not accepted.called
        assert dialog.accept_button.winfo_height()>=40
        assert dialog.accept_button.winfo_rooty()>dialog.winfo_rooty()+100
        dialog.cancel_button.invoke()
        assert not accepted.called
        dialog=ConfirmAction(root,'¿Pausar?', 'El control facial sigue activo hasta confirmar.',accepted)
        root.update()
        dialog.accept_button.invoke()
        accepted.assert_called_once()
    from tkinter import ttk, messagebox
    from mouthclick_ui import PagedMenu, Menu, field, hint
    from mouthclick_live_ui import WindowChrome, numeric
    app.update(tk=tk,ttk=ttk,messagebox=messagebox,PagedMenu=PagedMenu,Menu=Menu,field=field,hint=hint,toggle=toggle,WindowChrome=WindowChrome,numeric=numeric)
    app['load_profiles']=lambda:{'Test':app['normalize_profile']({})}
    app['get_camera_options']=lambda:(['Camera test', 'Camera second'],{'Camera test':0, 'Camera second':1})
    app['save_profiles']=Mock()
    done=Mock()
    menu=app['show_gui_menu'](root,done)
    root.update()
    assert menu.winfo_viewable() and root.winfo_exists()
    def descendants(w):
        for child in w.winfo_children():
            yield child
            yield from descendants(child)
    camera = next(w for w in descendants(menu) if isinstance(w,ttk.Combobox) and tuple(w.cget('values')) == ('Camera test', 'Camera second'))
    assert str(camera.cget('state')) == 'readonly'
    camera.current(1)
    save=next(w for w in descendants(menu) if isinstance(w,tk.Button) and 'Guardar y aplicar' in w.cget('text'))
    save.invoke()
    done.assert_called_once()
    assert done.call_args.args[0]['camera'] == 1
    assert app['save_profiles'].call_args.args[0]['Test']['camera'] == 1
    assert root.winfo_exists() and not menu.winfo_exists()
    menu=app['show_gui_menu'](root,done)
    root.update()
    menu.destroy()
    done.assert_called_once()
    assert not errors,errors
    print('PASS: settings, named levels, fine values, save/cancel and ten bubble actions at 100/125/150%')
finally:
    root.destroy()
