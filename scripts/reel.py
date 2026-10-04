#!/usr/bin/env python3
"""Gera o Reel animado do @viumachado (1080x1920, 10s, 30fps) com Pillow + numpy + ffmpeg."""
import argparse, io, math, os, subprocess, sys, tempfile, urllib.request, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music as trilhas
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 10.0
NAVY=(26,26,75); GREEN=(126,217,87); ORANGE=(250,110,30); BLUE=(50,200,240); WHITE=(255,255,255)
FONT_B = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"] if os.path.exists(p)), None)

def font(sz): return ImageFont.truetype(FONT_B, sz) if FONT_B else ImageFont.load_default()
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "viumachado-reels"})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")

def clamp(x): return max(0.0, min(1.0, x))
def prog(t, a, b): return clamp((t-a)/(b-a))
def out_back(x, s=1.9): x -= 1; return 1 + (s+1)*x**3 + s*x**2
def out_cubic(x): return 1-(1-x)**3

def rrect(size, r, fill):
    im = Image.new("RGBA", size, (0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle((0,0,size[0]-1,size[1]-1), r, fill=fill); return im

def pill(size, color, text, sz):
    im = rrect(size, 44, color+(255,)); d = ImageDraw.Draw(im); f = font(sz)
    while d.textlength(text, font=f) > size[0]-40 and sz > 20: sz -= 4; f = font(sz)
    tw = d.textlength(text, font=f); bb = f.getbbox("A0")
    d.text(((size[0]-tw)/2, (size[1]-(bb[3]-bb[1]))/2 - bb[1]), text, font=f, fill=WHITE if color != GREEN else NAVY if False else WHITE)
    return im

def paste_center(base, im, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1,int(im.width*scale)), max(1,int(im.height*scale))), Image.BILINEAR)
    if alpha < 1.0:
        a = im.getchannel("A").point(lambda v: int(v*alpha)); im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(cx-im.width/2), int(cy-im.height/2)))

def music(path):
    sr = 44100; n = int(sr*DUR); t = np.arange(n)/sr; out = np.zeros(n)
    bpm = 124; beat = 60/bpm
    # acordes (Am - F - C - G) em arpejo + baixo + bumbo + chimbal
    prog_ = [[57,60,64],[53,57,60],[48,52,55],[55,59,62]]
    def hz(m): return 440*2**((m-69)/12)
    step = beat/2; i = 0
    while i*step < DUR:
        ts = i*step; ch = prog_[int(ts/(beat*4)) % 4]; note = ch[i % 3] + (12 if (i//3) % 2 else 0)
        idx = int(ts*sr); L = int(step*sr*1.6); tt = np.arange(min(L, n-idx))/sr
        env = np.exp(-tt*7)
        out[idx:idx+len(tt)] += 0.20*env*(np.sign(np.sin(2*np.pi*hz(note+12)*tt))*0.5 + np.sin(2*np.pi*hz(note+12)*tt)*0.5)
        i += 1
    for b in range(int(DUR/beat)+1):
        ts = b*beat; idx = int(ts*sr); tt = np.arange(min(int(0.3*sr), n-idx))/sr
        if len(tt)==0: break
        out[idx:idx+len(tt)] += 0.55*np.sin(2*np.pi*(55+90*np.exp(-tt*30))*tt)*np.exp(-tt*9)           # bumbo
        root = prog_[int(ts/(beat*4)) % 4][0]-24
        tb = np.arange(min(int(beat*sr*0.9), n-idx))/sr
        out[idx:idx+len(tb)] += 0.22*np.sin(2*np.pi*hz(root)*tb)*np.exp(-tb*3)                          # baixo
        idx2 = int((ts+beat/2)*sr); th = np.arange(min(int(0.05*sr), n-idx2))/sr
        if len(th) > 0:
            rng = np.random.default_rng(b); out[idx2:idx2+len(th)] += 0.10*rng.standard_normal(len(th))*np.exp(-th*60)  # chimbal
    fade = np.minimum(1, np.minimum(t/0.4, (DUR-t)/0.8)); out *= fade
    out = np.clip(out/ max(1e-6, np.abs(out).max()) * 0.8, -1, 1)
    st = np.stack([out, out], 1); data = (st*32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True); ap.add_argument("--logo", required=True)
    ap.add_argument("--desc", required=True); ap.add_argument("--preco", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--frames-only", default="")
    a = ap.parse_args()
    foto = (fetch(a.foto) if a.foto.startswith("http") else Image.open(a.foto).convert("RGB"))
    side = min(foto.size); foto = foto.crop(((foto.width-side)//2,(foto.height-side)//2,(foto.width-side)//2+side,(foto.height-side)//2+side)).resize((816,816), Image.LANCZOS)
    logo = (fetch(a.logo) if a.logo.startswith("http") else Image.open(a.logo).convert("RGB"))
    logo = logo.crop((140,30,660,690)).resize((300,381), Image.LANCZOS).convert("RGBA")
    # fundo
    bg = Image.new("RGBA", (W,H), WHITE+(255,)); d = ImageDraw.Draw(bg)
    for y0,y1 in ((0,18),(H-18,H)):
        d.rectangle((0,y0,360,y1),fill=GREEN); d.rectangle((360,y0,720,y1),fill=ORANGE); d.rectangle((720,y0,W,y1),fill=BLUE)
    frame = rrect((832,832), 36, NAVY+(255,))
    desc_p = pill((480,150), ORANGE, a.desc, 84); preco_p = pill((480,150), GREEN, a.preco, 84)
    cta1 = pill((960,110), NAVY, "Siga @viumachado e receba achados todo dia", 40)
    cta2 = pill((960,110), NAVY, "Link na bio: entre no grupo grátis!", 44)
    tag = pill((560,84), BLUE, "OFERTA DO DIA", 44)
    nfr = int(DUR*FPS); tmp = tempfile.mkdtemp()
    for i in range(nfr):
        t = i/FPS; f = bg.copy()
        # logo desce
        p = out_back(prog(t,0.0,0.7)); paste_center(f, logo, W/2, 60+190 - (1-p)*420, 1.0, clamp(t/0.3))
        # selo "oferta do dia" logo abaixo da logo
        paste_center(f, tag, W/2, 600-40, out_back(prog(t,0.9,1.4)) , 1.0)
        # moldura + foto (pop) + zoom suave
        pf = out_back(prog(t,0.5,1.2), 1.4)
        zoom = 1.0 + 0.07*prog(t,1.4,9.5)
        z = foto.resize((int(816*zoom),int(816*zoom)), Image.BILINEAR); ox=(z.width-816)//2; z = z.crop((ox,ox,ox+816,ox+816)).convert("RGBA")
        comp = frame.copy(); comp.alpha_composite(z, (8,8))
        paste_center(f, comp, W/2, 1036+40, 0.6+0.4*pf, clamp(prog(t,0.5,0.9)))
        # selos de desconto e preco
        pulse = 1+0.035*math.sin(max(0,t-3)*2*math.pi*1.1)*prog(t,2.8,3.2)
        paste_center(f, desc_p, 280, 1580, out_back(prog(t,1.6,2.2),2.4)*pulse)
        paste_center(f, preco_p, 800, 1580, out_back(prog(t,2.0,2.6),2.4)*pulse)
        # CTA com troca de texto
        slide = (1-out_cubic(prog(t,2.7,3.3)))*260
        c1 = clamp(1-prog(t,6.0,6.4)); c2 = clamp(prog(t,6.0,6.4))
        sc = 1+0.03*math.sin(max(0,t-6.4)*2*math.pi*1.6)*prog(t,6.4,6.8)
        paste_center(f, cta1, W/2, 1790+slide, 1.0, c1*clamp(prog(t,2.7,3.0)))
        paste_center(f, cta2, W/2, 1790+slide, sc, c2)
        # fade final
        if t > DUR-0.5:
            ov = Image.new("RGBA",(W,H),WHITE+(int(255*prog(t,DUR-0.5,DUR)),)); f.alpha_composite(ov)
        f.convert("RGB").save(f"{tmp}/f{i:04d}.jpg", quality=92)
        if a.frames_only and i in (int(x) for x in a.frames_only.split(",")): f.convert("RGB").save(f"/tmp/prev_{i}.png")
    wav = f"{tmp}/m.wav"; trilhas.make("lofi", DUR, wav)
    subprocess.check_call(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",f"{tmp}/f%04d.jpg","-i",wav,
        "-c:v","libx264","-preset","medium","-crf","21","-pix_fmt","yuv420p","-af","loudnorm=I=-15:TP=-1.5:LRA=7","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",a.out])

if __name__ == "__main__": main()
