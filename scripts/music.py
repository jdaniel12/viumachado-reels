"""Trilhas originais (sem direitos autorais) geradas por sintese: estilos 'pop', 'lofi' e 'eletro'."""
import subprocess, wave
import numpy as np

SR = 44100

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def saw(f, t): return 2 * ((f * t) % 1.0) - 1
def tri(f, t): return 2 * np.abs(saw(f, t)) - 1
def env(n, a=0.005, d=6.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)

def add(buf, start, sig):
    i = int(start * SR)
    if i >= len(buf): return
    seg = sig[: len(buf) - i]; buf[i:i + len(seg)] += seg

def kick(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (48 + 110 * np.exp(-t * 28)) * t) * np.exp(-t * 8)
def clap(n=int(0.22 * SR), seed=1):
    t = np.arange(n) / SR; r = np.random.default_rng(seed).standard_normal(n)
    return r * (np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) * 70) ** 2))
def hat(n=int(0.06 * SR), seed=2, d=70):
    t = np.arange(n) / SR; r = np.random.default_rng(seed).standard_normal(n)
    return np.diff(r, prepend=0) * np.exp(-t * d)
def snare(n=int(0.25 * SR), seed=3):
    t = np.arange(n) / SR; r = np.random.default_rng(seed).standard_normal(n)
    return (r * 0.7 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 18)

def pad(chord, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for m in chord:
        for det in (-0.12, 0.0, 0.12):
            s += saw(hz(m) * 2 ** (det / 12), t)
    a = np.minimum(1, t / 0.15) * np.minimum(1, (dur - t) / 0.2)
    return s / (3 * len(chord)) * a

def rhodes(m, dur):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5) + 0.15 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 9)
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 2.6)

def song(style, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    drums = np.zeros(n); bass = np.zeros(n); keys = np.zeros(n); arp = np.zeros(n); kick_t = []
    if style == "pop":
        bpm = 120; chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]; roots = [48, 43, 45, 41]
    elif style == "lofi":
        bpm = 84; chords = [[62, 65, 69, 72], [55, 59, 62, 65], [60, 64, 67, 71], [57, 60, 64, 67]]; roots = [38, 43, 36, 45]
    else:
        bpm = 128; chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]; roots = [45, 41, 36, 43]
    beat = 60 / bpm; nb = int(dur / beat) + 2
    for b in range(nb):
        ts = b * beat; bar = int(b // 4) % 4; ch = chords[bar]; root = roots[bar]
        if style in ("pop", "eletro"):
            add(drums, ts, kick() * 0.9); kick_t.append(ts)
            if b % 2 == 1: add(drums, ts, clap(seed=b) * 0.35)
            add(drums, ts + beat / 2, hat(seed=b) * 0.22)
            if style == "eletro" and b % 4 == 3: add(drums, ts + beat / 2, hat(seed=b + 50, d=25) * 0.25)
            add(bass, ts + beat / 2, np.sin(2 * np.pi * hz(root) * np.arange(int(beat * 0.45 * SR)) / SR) * env(int(beat * 0.45 * SR), 0.004, 5) * 0.55)
            if b % 4 == 0: add(keys, ts, pad(ch, beat * 4) * 0.55)
            for k in range(2):
                m = ch[(b * 2 + k) % len(ch)] + 12 + (12 if (b + k) % 4 == 3 else 0)
                tt = np.arange(int(beat * 0.8 * SR)) / SR
                add(arp, ts + k * beat / 2, tri(hz(m), tt) * env(len(tt), 0.003, 9) * 0.35)
        else:
            sw = beat * 0.08
            if b % 4 in (0, 2): add(drums, ts, kick() * 0.75); kick_t.append(ts)
            if b % 4 in (1, 3): add(drums, ts, snare(seed=b) * 0.35)
            add(drums, ts, hat(seed=b, d=90) * 0.14); add(drums, ts + beat / 2 + sw, hat(seed=b + 9, d=90) * 0.11)
            if b % 4 == 0:
                for j, m in enumerate(ch): add(keys, ts + j * 0.02, rhodes(m, beat * 4) * 0.3)
            add(bass, ts, np.sin(2 * np.pi * hz(root) * np.arange(int(beat * 1.5 * SR)) / SR) * env(int(beat * 1.5 * SR), 0.01, 2.5) * 0.7)
            if b % 2 == 0:
                m = ch[(b // 2) % len(ch)] + 12; tt = np.arange(int(beat * SR)) / SR
                add(arp, ts + beat * 0.75 + sw, rhodes(m, beat) * 0.22)
    # sidechain: o pad/teclado "respira" no bumbo
    duck = np.ones(n)
    if style != "lofi":
        for kt in kick_t:
            i = int(kt * SR); L = int(0.28 * SR); seg = np.arange(min(L, n - i)) / SR
            duck[i:i + len(seg)] *= 1 - 0.6 * np.exp(-seg * 14)
    mix = drums + bass + (keys + arp * 0.9) * duck
    if style == "lofi":
        mix += 0.012 * np.random.default_rng(7).standard_normal(n)
    mix = mix[:n]
    fade = np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.9)); mix *= fade
    mix = np.tanh(mix * 1.3); mix = mix / max(1e-6, np.abs(mix).max()) * 0.85
    return mix

def make(style, dur, path):
    x = song(style, dur); raw = path + ".raw.wav"
    st = np.stack([x, x], 1); data = (st * 32767).astype("<i2").tobytes()
    with wave.open(raw, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data)
    chain = {"pop": "lowpass=f=9000,aecho=0.8:0.6:60|120:0.25|0.15,acompressor=threshold=-18dB:ratio=3",
             "lofi": "lowpass=f=4200,highpass=f=60,aecho=0.8:0.7:90|180:0.3|0.2,acompressor=threshold=-20dB:ratio=3",
             "eletro": "lowpass=f=11000,aecho=0.8:0.6:117|234:0.22|0.12,acompressor=threshold=-16dB:ratio=4"}[style]
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", chain + ",volume=-1.5dB", path])

if __name__ == "__main__":
    import sys; make(sys.argv[1], float(sys.argv[2]), sys.argv[3])
