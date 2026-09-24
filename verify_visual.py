"""UI regression check: uses mock cameras/persistence, never starts cursor control."""
import ast
import copy
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mouthclick_ui import PagedMenu, Menu, field, hint, toggle, style_floating
from mouthclick_live_ui import numeric, WindowChrome
from mouthclick_runtime import FACE_POINTS, RANGES, validated, profile_save_name
from tkinter import messagebox
import math

ctypes.windll.user32.SetProcessDPIAware()

FILES = ('mouthclick_mvp_opticalflow.py', 'mouthclick.py', 'cameramause.py')
PROFILES = json.loads(Path('profiles.json').read_text(encoding='utf-8'))


def widgets(root):
    for child in root.winfo_children():
        yield child
        yield from widgets(child)


def namespace(source):
    tree = ast.parse(source)
    keep = []
    constants = {'DEFAULT_PROFILE', 'AVAILABLE_ACTIONS', 'SENS_LEVELS', 'LEGACY_SENS_MAP', 'WINK_DIFF_LEVELS', 'GAIN_X_BY_LEVEL', 'GAIN_Y_BY_LEVEL'}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in ('show_gui_menu', 'normalize_profile'):
            keep.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets):
            keep.append(n)
    saved = []
    env = dict(numeric=numeric, FACE_POINTS=FACE_POINTS, RANGES=RANGES, validated=validated, math=math, messagebox=messagebox, tk=tk, ttk=ttk, Menu=Menu, field=field, hint=hint, toggle=toggle,
               style_floating=style_floating, PagedMenu=PagedMenu, WindowChrome=WindowChrome, profile_save_name=profile_save_name,
               load_profiles=lambda: copy.deepcopy(PROFILES),
               save_profiles=lambda p: saved.append(copy.deepcopy(p)),
               get_camera_options=lambda: (['Camera A', 'Camera B'], {'Camera A': 0, 'Camera B': 1}))
    exec(compile(ast.Module(body=keep, type_ignores=[]), '<isolated UI>', 'exec'), env)
    return env, saved


def run(source, name, select=False, size=None, scale=None, capture=False):
    env, saved = namespace(source)
    errors = []
    def loop(root, *args):
        root.report_callback_exception = lambda *e: errors.append(e)
        if scale:
            root.tk.call('tk', 'scaling', scale)
        if size:
            root.state("normal")
            root.geometry(size)
        root.update_idletasks()
        root.update()
        controls = list(widgets(root))
        if select and name != 'cameramause.py':
            combo = next(w for w in controls if isinstance(w, ttk.Combobox) and 'Por Defecto' in w.cget('values'))
            combo.set('Por Defecto')
            combo.event_generate('<<ComboboxSelected>>')
            root.update()
        if size:
            buttons = [w for w in controls if isinstance(w, tk.Button)]
            begin = next(w for w in buttons if 'Comenzar' in w.cget('text'))
            assert begin.winfo_rooty() + begin.winfo_height() <= root.winfo_rooty()+root.winfo_height(), 'Start clipped'
            assert begin.winfo_height() >= 40, 'Start target too small'
            if hasattr(root, 'paged_menu'):
                menu=root.paged_menu
                assert not any(isinstance(w,ttk.Scrollbar) for w in controls)
                for index in range(len(menu.pages)):
                    menu.show_page(index)
                    root.update()
                    for card in menu.cards[index*2:index*2+2]:
                        for control in card.body.winfo_children():
                            assert control.winfo_rooty()+control.winfo_height()<=menu.content.winfo_rooty()+menu.content.winfo_height(), (size,scale,index,control)
                menu.show_page(0)
                root.update()
            if capture:
                from PIL import ImageGrab
                x, y = root.winfo_rootx(), root.winfo_rooty()
                ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height())).save('.visual-build/preview.png')
        start = next(w for w in widgets(root) if isinstance(w, tk.Button) and ('COMENZAR' in w.cget('text') or 'Comenzar' in w.cget('text')))
        start.invoke()
    original_init = tk.Tk.__init__
    def init(root, *args, **kwargs):
        original_init(root, *args, **kwargs)
        if scale:
            root.tk.call('tk', 'scaling', scale)
    with patch.object(tk.Tk, '__init__', init), patch.object(tk.Tk, 'mainloop', loop):
        result = env['show_gui_menu']()
    assert not errors, errors
    return result, saved


for name in FILES:
    if name == "mouthclick_mvp_opticalflow.py":
        continue  # Intentional runtime changes are covered by test_runtime.py.
    before = subprocess.check_output(['git', 'show', 'HEAD:'+name]).decode('utf-8-sig')
    after = Path(name).read_text(encoding='utf-8-sig')
    for select in (False, True):
        expected = run(before, name, select)
        actual = run(after, name, select)
        assert actual == expected, (name, select, actual, expected)
    # Every nonvisual function must remain byte-for-byte equivalent as an AST.
    old = {n.name: ast.dump(n) for n in ast.parse(before).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new = {n.name: ast.dump(n) for n in ast.parse(after).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    allowed = {'show_gui_menu', 'create_floating_keyboard', 'create_quick_actions_bubble'}
    assert all(new[k] == v for k,v in old.items() if k not in allowed), name
    print(name, 'profiles, return contract and nonvisual functions OK')

source = Path(FILES[0]).read_text(encoding='utf-8')
for scale in (1.3333, 1.6667, 2.0):
    for size in ('1080x740', '860x600', '620x480'):
        run(source, FILES[0], size=size, scale=scale, capture=(scale == 1.3333 and size == '1080x740'))
        print('Layout', size, 'Tk scaling', scale, 'OK')
print('All UI checks passed')
