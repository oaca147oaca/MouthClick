"""Two-minute bounded-memory smoke check; synthetic frames, no camera or mouse."""
import ctypes
from ctypes import wintypes
import time
import json
from pathlib import Path
import tkinter as tk
import numpy as np
import mediapipe as mp
from mouthclick_runtime import LatestFrameCapture
from mouthclick_alignment import AlignmentGuide


class Memory(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak','working','peakpaged','paged','peaknonpaged','nonpaged','pagefile','peakpagefile','private')]


def memory_mb():
    data=Memory()
    data.cb=ctypes.sizeof(data)
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi')
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(data),data.cb):
        raise ctypes.WinError()
    return round(data.working/1048576,2),round(data.private/1048576,2)


class Camera:
    def read(self):
        time.sleep(1/30)
        return True,np.zeros((480,640,3),np.uint8)
    def release(self):
        pass


root=tk.Tk()
root.withdraw()
guide=AlignmentGuide(root,lambda:None)
guide.withdraw()
capture=LatestFrameCapture(Camera())
mesh=mp.solutions.face_mesh.FaceMesh(max_num_faces=1,refine_landmarks=True)
start=time.monotonic()
samples=[]
count=0
next_sample=20
try:
    while time.monotonic()-start<120:
        ok,frame=capture.read()
        if not ok:
            continue
        mesh.process(frame)
        guide.update_frame(frame,None)
        root.update()
        count+=1
        # Deliberately slower consumer: old camera frames must not queue up.
        time.sleep(.02)
        elapsed=time.monotonic()-start
        if elapsed>=next_sample:
            working,private=memory_mb()
            sample=dict(seconds=round(elapsed,1),working_mb=working,private_mb=private,
                        frames=count,tk_images=len(root.tk.call('image','names')))
            samples.append(sample)
            print(sample,flush=True)
            next_sample+=20
finally:
    capture.release()
    mesh.close()
    guide.destroy()
    root.destroy()
assert not capture.worker.is_alive()
assert max(s['tk_images'] for s in samples)-min(s['tk_images'] for s in samples)<=1
growth=samples[-1]['private_mb']-samples[0]['private_mb']
assert growth<25, samples
Path('.visual-build').mkdir(exist_ok=True)
Path('.visual-build/soak-result.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
print('PASS: bounded frames/images; private growth after warmup:',round(growth,2),'MB',flush=True)
