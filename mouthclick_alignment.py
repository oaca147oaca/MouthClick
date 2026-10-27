"""On-demand, low-rate alignment preview. Images are never written to disk."""
import time
import math
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk
from mouthclick_ui import apply_theme, label, button, COLORS
from mouthclick_live_ui import WindowChrome


def alignment_state(points):
    if not points:
        return False, "Colocá la cara dentro del óvalo"
    top, chin, left, right = (points[i] for i in (10,152,234,454))
    cx, cy = (left.x+right.x)/2, (top.y+chin.y)/2
    height = abs(chin.y-top.y)
    width = abs(right.x-left.x)
    if abs(cx-.5) > .10 or abs(cy-.5) > .12:
        return False, "Centrate en el óvalo"
    if height < .26:
        return False, "Acercate un poco a la cámara"
    if height > .65 or width > .55:
        return False, "Alejate un poco de la cámara"
    def eye(indices):
        p=[points[i] for i in indices]
        dist=lambda a,b:math.hypot(a.x-b.x,a.y-b.y)
        return (dist(p[1],p[5])+dist(p[2],p[4]))/max(2*dist(p[0],p[3]),1e-6)
    l=eye((33,160,158,133,153,144))
    r=eye((362,385,387,263,373,380))
    if min(l,r)<.16 or abs(l-r)/max(l,r,1e-6)>.35:
        return False, "Ojos poco visibles: mirá de frente y revisá la altura de la cámara"
    if abs(points[33].y-points[263].y) > .06:
        return False, "Enderezá la cabeza y mirá hacia la cámara"
    return True, "Cara centrada y ojos visibles"


def lighting_state(frame, points):
    """Estimate facial exposure from a small face-only sample, not ambient lux."""
    if frame is None or not points:
        return False, "Luz: esperando detectar el rostro"
    small = cv2.resize(frame, (160, 120), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    contour = np.array([(round(points[i].x*159), round(points[i].y*119))
                        for i in (10, 338, 454, 397, 152, 172, 234, 109)], dtype=np.int32)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(contour), 255)
    mask = cv2.erode(mask, np.ones((3, 3), dtype=np.uint8))
    face = gray[mask > 0]
    if face.size < 100:
        return False, "Luz: acercate para evaluar el rostro"
    median = float(np.median(face))
    if median < 60 or float(np.mean(face < 35)) > .45:
        return False, "Luz baja: agregá una luz suave frente a la cara"
    if median > 220 or float(np.mean(face > 245)) > .20:
        return False, "Demasiada luz: evitá el sol o una lámpara directa en la cara"
    center = int(np.median(np.where(mask > 0)[1]))
    left = gray[:, :center][mask[:, :center] > 0]
    right = gray[:, center:][mask[:, center:] > 0]
    if left.size and right.size and abs(float(np.median(left))-float(np.median(right))) > 55:
        return False, "Luz desigual: iluminá ambos lados de la cara de forma pareja"
    return True, "Luz adecuada en el rostro"


class AlignmentGuide(tk.Toplevel):
    def __init__(self,master,recalibrate):
        super().__init__(master)
        apply_theme(self)
        self.title("MouthClick · Posición de la cámara")
        width=min(900,self.winfo_screenwidth())
        self.geometry(f"{width}x{min(820,self.winfo_screenheight())}")
        self.chrome=WindowChrome(self,self.destroy,"MouthClick · Posición de la cámara")
        footer=tk.Frame(self,bg=COLORS['bg'])
        footer.pack(side='bottom',fill='x')
        self.last_update=0.0
        self.photo=None
        label(self,"Posición frente a la cámara",size=20,bold=True).pack(pady=10)
        self.preview=tk.Label(self,bg=COLORS['bg'])
        self.preview.pack(fill='both',expand=True)
        self.message=label(footer,"Buscando cara…",wraplength=width-40,size=12)
        self.message.pack(fill='x',padx=15,pady=8)
        self.lighting=label(footer,"Luz: esperando detectar el rostro",wraplength=width-40,size=12)
        self.lighting.pack(fill='x',padx=15,pady=4)
        label(footer,"Estimación de la imagen; no mide la luz ambiente ni garantiza detectar todos los gestos.",secondary=True,wraplength=width-40).pack(fill='x',padx=15)
        label(footer,"Elevá la cámara hasta la altura de los ojos. Si queda por debajo de la cara, los guiños pueden fallar aunque estés centrado. El verde indica encuadre, no una calibración validada.",secondary=True,wraplength=width-40,justify='left').pack(padx=15,pady=8)
        self.recalibrate_button=button(footer,"Estoy cómodo · recalibrar ojos y cejas",recalibrate)
        self.recalibrate_button.pack(fill='x',padx=15,pady=5)
        self.close_button=button(footer,"Cerrar guía",self.destroy,primary=True)
        self.close_button.pack(fill='x',padx=15,pady=10)

    def update_frame(self,frame,points):
        if time.monotonic()-self.last_update < .1:
            return
        self.last_update=time.monotonic()
        ok,message=alignment_state(points)
        light_ok,light_message=lighting_state(frame,points)
        self.lighting.configure(text=light_message,fg=COLORS['green'] if light_ok else COLORS['amber'])
        width=min(480,max(160,int(self.preview.winfo_height()*frame.shape[1]/frame.shape[0])))
        height=round(frame.shape[0]*width/frame.shape[1])
        preview=cv2.resize(frame,(width,height))
        color=(80,210,100) if ok else (20,180,255)
        cv2.ellipse(preview,(width//2,height//2),(int(width*.16),int(height*.25)),0,0,360,color,3)
        if points:
            for index in (33,133,362,263):
                point=points[index]
                cv2.circle(preview,(int(point.x*width),int(point.y*height)),3,color,-1)
        photo=ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(preview,cv2.COLOR_BGR2RGB)),master=self)
        self.preview.configure(image=photo)
        self.photo=photo
        self.message.configure(text=message,fg=COLORS['green'] if ok else COLORS['amber'])

    def unavailable(self):
        self.lighting.configure(text="Luz: sin imagen para evaluar",fg=COLORS['amber'])
        if self.photo is not None:
            self.preview.configure(image="")
            self.photo=None
        self.message.configure(text="Sin imagen actual de la cámara",fg=COLORS['amber'])

    def destroy(self):
        self.photo=None
        super().destroy()
