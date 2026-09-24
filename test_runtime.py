"""Run with `py -3.11 -m unittest test_runtime`; no real camera or input events."""
import ast
import ctypes
import io
import json
import math
import os
from pathlib import Path
import queue
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import cv2
import numpy as np
from mouthclick_runtime import (ActionAudio, FACE_POINTS, RANGES, SettingsSession,
                               atomic_save_profiles, point_pixels, validated, wave_bytes, gain_index, step_gain)

SOURCE = Path(__file__).with_name("mouthclick_mvp_opticalflow.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def isolated_app():
    mouse = Mock()
    mouse.size.return_value = (1920, 1080)
    mouse.position.return_value = (500, 500)
    env = dict(os=os, json=json, math=math, ctypes=ctypes, time=time, queue=queue, cv2=cv2, np=np,
               pyautogui=mouse, FACE_POINTS=FACE_POINTS, RANGES=RANGES, validated=validated,
               point_pixels=point_pixels, atomic_save_profiles=atomic_save_profiles, gain_index=gain_index, step_gain=step_gain,
               keyboard=SimpleNamespace(Key=SimpleNamespace(**{name: name for name in
                   ["esc"]+[f"f{i}" for i in range(1,13)]})))
    for node in TREE.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "cap" for t in node.targets):
            break
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in node.targets):
            env["CONFIG"] = {**env["normalize_profile"]({}), "_profile_name": "Test"}
        elif isinstance(node, (ast.Assign, ast.FunctionDef)):
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<isolated app>", "exec"), env)
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("report_status", "present_camera"):
            exec(compile(ast.Module(body=[node], type_ignores=[]), "<isolated app>", "exec"), env)
    return env


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.app = isolated_app()
        self.current = self.app["runtime_snapshot"]()

    def test_profile_migration_and_invalid_values(self):
        p = self.app["normalize_profile"]({"sensitivity":"media-alta", "gain_x":float("nan"), "face_point":"old"})
        self.assertEqual(p["sens_x"], "alta")
        self.assertEqual(p["gain_x"],74)
        self.assertEqual(p["face_point"],"Punta de nariz")
        self.assertEqual(self.app["normalize_profile"](None)["gain_y"],52)

    def test_invalid_preview_is_atomic(self):
        apply = Mock()
        session=SettingsSession(self.current,apply,Mock())
        for value in ("", "nan", "inf", -1, 999):
            with self.assertRaises(ValueError): session.preview({"gain_x":value})
        apply.assert_not_called()
        self.assertEqual(session.values,self.current)

    def test_preview_cancel_restores_all_values(self):
        session=SettingsSession(self.current,self.app["apply_runtime_settings"],Mock())
        session.preview(dict(gain_x=77.5,gain_y=83,face_point="Pera / mentón",wink_diff_sens="sensible",
                             mouth_threshold=.07,dwell_time=1.2,dwell_radius=12,deadzone=.4,
                             smoothing=.3,stabilize=True,dwell_enabled=True,sound_enabled=False))
        self.assertEqual(self.app["REL_GAIN_X"],77.5)
        self.assertTrue(self.app["SELECTING_POINT"])
        self.assertEqual(self.app["CLICK_ARM_RATIO"],.07)
        session.cancel()
        self.assertEqual(self.app["runtime_snapshot"](),self.current)
        session.save.assert_not_called()

    def test_save_reload_preserves_other_profiles_and_unknown_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"profiles.json"
            original={"Test":{"camera":2,"mouth":"Doble click","custom":"preserve"},"Other":{"custom":42}}
            atomic_save_profiles(p,original)
            self.app["PROFILES_FILE"]=str(p)
            session=SettingsSession(self.current,self.app["apply_runtime_settings"],self.app["save_runtime_settings"])
            session.preview({"gain_x":87.3,"face_point":"Entrecejo"})
            session.commit()
            saved=json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(saved["Other"],original["Other"])
            self.assertEqual(saved["Test"]["custom"],"preserve")
            self.assertEqual(saved["Test"]["camera"],2)
            self.assertEqual(saved["Test"]["mouth"],"Doble click")
            self.assertNotIn("_profile_name",saved["Test"])
            loaded=self.app["normalize_profile"](saved["Test"])
            self.assertEqual(loaded["gain_x"],87.3)
            self.assertEqual(loaded["face_point"],"Entrecejo")

    def test_failed_save_allows_cancel(self):
        save=Mock(side_effect=OSError("disk full"))
        session=SettingsSession(self.current,self.app["apply_runtime_settings"],save)
        session.preview({"gain_x":90})
        with self.assertRaises(OSError): session.commit()
        self.assertFalse(session.closed)
        session.cancel()
        self.assertEqual(self.app["REL_GAIN_X"],self.current["gain_x"])

    def test_atomic_write_failure_keeps_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"profiles.json"
            path.write_text('{"original":true}')
            with patch("mouthclick_runtime.os.replace",side_effect=OSError("denied")):
                with self.assertRaises(OSError): atomic_save_profiles(path,{"new":1})
            self.assertEqual(path.read_text(),'{"original":true}')
            self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_four_landmarks_and_frame_clamping(self):
        landmarks=[SimpleNamespace(x=i/500,y=i/500) for i in range(478)]
        for name,index in FACE_POINTS.items():
            self.assertEqual(point_pixels(landmarks,name,640,480),(index/500*640,index/500*480))
        landmarks[1]=SimpleNamespace(x=-1,y=2)
        self.assertEqual(point_pixels(landmarks,"Punta de nariz",640,480),(0,479))

    def test_point_acquisition_does_not_move_mouse(self):
        app=self.app
        app["current_gray_frame"]=np.zeros((480,640),np.uint8)
        app["last_face_anchor"]=(200.,150.)
        app["on_mouse"](cv2.EVENT_LBUTTONDOWN,200.,150.,None,None)
        np.testing.assert_array_equal(app["tracking_point"],[[[200,150]]])
        app["pyautogui"].moveTo.assert_not_called()
        self.assertFalse(app["SELECTING_POINT"])

    def test_hidden_preview_does_not_render_or_poll_opencv(self):
        self.app["cv2"]=Mock()
        self.app["present_camera"](np.zeros((3,3,3),np.uint8),"test")
        self.app["cv2"].imshow.assert_not_called()
        self.app["cv2"].waitKey.assert_not_called()

    def test_sound_all_click_paths_and_disabled_option(self):
        app=self.app
        app["action_audio"]=Mock()
        with patch.object(time,"sleep"):
            for name in ("do_click","do_right_click","do_double_click","start_drag","stop_drag"):
                app[name]()
        self.assertEqual(app["action_audio"].play.call_count,5)
        app["action_audio"].reset_mock()
        app["execute_action"]("Click izquierdo")
        app["action_audio"].play.assert_called_once_with("Click izquierdo")
        app["SOUND_ENABLED"]=False
        app["action_audio"].reset_mock()
        app["do_click"]()
        app["action_audio"].play.assert_not_called()

    def test_shortcuts_preview_can_be_discarded(self):
        app=self.app
        session=SettingsSession(self.current,app["apply_runtime_settings"],Mock())
        app["on_press"]("f4")
        self.assertNotEqual(app["REL_GAIN_X"],self.current["gain_x"])
        session.cancel()
        self.assertEqual(app["runtime_snapshot"](),self.current)

    def test_fine_gain_shortcuts_are_monotonic_and_bounded(self):
        levels=[42.,62.,74.,88.,104.]
        for value in (5,42,65,83.4,104,177.2,400):
            self.assertGreaterEqual(step_gain(value,levels,1,8),value)
            self.assertLessEqual(step_gain(value,levels,-1,8),value)
            self.assertLessEqual(step_gain(value,levels,1,8),400)
            self.assertGreaterEqual(step_gain(value,levels,-1,8),5)

    def test_sound_worker_does_not_block_caller(self):
        started, release=threading.Event(),threading.Event()
        backend=SimpleNamespace(SND_MEMORY=4,PlaySound=lambda *args:(started.set(),release.wait(2)))
        audio=ActionAudio(backend)
        try:
            audio.play("Click izquierdo")
            self.assertTrue(started.wait(1))
            audio.play("Doble click")
            audio.play("Click derecho")
            self.assertLessEqual(audio.pending.qsize(),1)
        finally:
            audio.close()
            release.set()
            audio.worker.join(2)

    def test_release_escape_does_not_feed_back(self):
        app = self.app
        app["pyautogui"].press.side_effect = lambda key: app["ui_commands"].put("esc")
        app["release_all_inputs"](close_context_menu=True)
        app["process_hotkeys"]()
        self.assertTrue(app["ui_commands"].empty())
        app["pyautogui"].press.assert_called_once_with("esc")
        self.assertTrue(app["RUNNING"])

    def test_hotkeys_leave_time_for_ui(self):
        for _ in range(200):
            self.app["ui_commands"].put("unused")
        self.app["process_hotkeys"](limit=5)
        self.assertEqual(self.app["ui_commands"].qsize(), 195)

    def test_pause_resume_and_exit(self):
        app = self.app
        app["floating_actions_root"] = Mock()
        app["toggle_pause"]()
        self.assertTrue(app["PAUSED"])
        app["floating_actions_root"].set_paused.assert_called_with(True)
        app["toggle_pause"]()
        self.assertFalse(app["PAUSED"])
        self.assertTrue(app["RUNNING"])
        app["request_exit"]()
        self.assertFalse(app["RUNNING"])
        app["pyautogui"].press.assert_not_called()

    def test_sound_is_valid_wav(self):
        with wave.open(io.BytesIO(wave_bytes([(880,90)]))) as wav:
            self.assertEqual(wav.getnchannels(),1)
            self.assertEqual(wav.getsampwidth(),2)
            self.assertGreater(wav.getnframes(),1900)

    def test_loop_face_loss_and_reacquisition_without_preview(self):
        app=self.app
        face=SimpleNamespace(landmark=[SimpleNamespace(x=.5,y=.5) for _ in range(478)])
        outcomes=[[],[face],[face],[],[face]]
        app["face_mesh"]=SimpleNamespace(process=Mock(side_effect=[SimpleNamespace(multi_face_landmarks=x) for x in outcomes]))
        app["cap"]=SimpleNamespace(read=Mock(return_value=(True,np.zeros((480,640,3),np.uint8))))
        app["detect_gesture"]=Mock(return_value=None)
        app["update_optical_tracking"]=Mock()
        app["report_status"]=Mock()
        app["DWELL_ENABLED"]=True
        app["last_move_time"]=0
        ticks=[]
        def tick():
            ticks.append(1)
            if len(ticks)>len(outcomes): app["RUNNING"]=False
        app["update_floating_keyboard"]=tick
        loop=next(n.body[0] for n in TREE.body if isinstance(n,ast.Try) and isinstance(n.body[0],ast.While))
        exec(compile(ast.Module(body=[loop],type_ignores=[]),"<simulated frames>","exec"),app)
        # Only one continuous tracking step; the first/reacquired frames initialize without moving.
        self.assertEqual(app["update_optical_tracking"].call_count,1)
        app["pyautogui"].moveTo.assert_not_called()
        app["pyautogui"].click.assert_not_called()
        self.assertEqual(app["face_mesh"].process.call_count,5)
        self.assertFalse(app["SELECTING_POINT"])

    def test_optical_tracking_moves_within_screen(self):
        app=self.app
        app["current_gray_frame"]=np.zeros((480,640),np.uint8)
        app["last_face_anchor"]=(200.,150.)
        app["on_mouse"](cv2.EVENT_LBUTTONDOWN,200.,150.,None,None)
        fake=Mock(wraps=cv2)
        fake.calcOpticalFlowPyrLK.return_value=(np.array([[[201.,151.]]],np.float32),np.array([[1]]),None)
        app["cv2"]=fake
        app["update_optical_tracking"](app["current_gray_frame"],time.time())
        app["pyautogui"].moveTo.assert_called_once()
        x,y=app["pyautogui"].moveTo.call_args.args
        self.assertTrue(500<x<640 and 500<y<640)


if __name__ == "__main__":
    unittest.main()
