#!/usr/bin/env python3
"""Reel v2 do @viumachado: 1080x1920, 15-25 s, tela cheia, gancho, narracao e legenda.

Le tudo do ambiente (nunca da linha de comando, por seguranca no Actions):
  REEL_ID      id do arquivo (reels/<id>.mp4)
  PAYLOAD_B64  JSON em base64 com imagens, gancho, roteiro, cta, precos, voz, trilha, layout
Saidas: reels/<id>.mp4, reels/<id>.jpg (capa) e reels/<id>.json (dados do render).
Para testar no PC: python scripts/reel_v2.py --payload-file teste.json --id teste --local
"""
import argparse, base64, io, json, math, os, re, subprocess, sys, tempfile, time, urllib.request, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music as trilhas
import tts
from layouts import layout, NAVY, WHITE, YELLOW
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DUR_MIN, DUR_MAX, FALA_MAX = 15.0, 25.0, 24.0
GANCHO_MIN_S, CTA_MIN_S, PRECO_S, CENA_S = 2.5, 3.0, 3.0, 2.5
PAUSA_APOS_GANCHO, PAUSA_ANTES_CTA, FOLGA_FINAL = 0.25, 0.35, 1.0
TEXTO_LARG = 860            # largura maxima dos textos (deixa livre a lateral dos botoes)
FOTO_LARG = 1000
PALAVRAS_POR_LEGENDA = 3
ID_OK = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, "..", "assets", "fonts", "Fredoka.ttf")
LOGO = os.path.join(AQUI, "..", "assets", "logo.png")
LOGO_ALT, LOGO_POS = 170, (36, 64)  # canto de cima a esquerda, fora dos botoes do Instagram


def falhar(msg):
    print(f"ERRO: {msg}", file=sys.stderr); sys.exit(1)


# ---------- entrada ----------
def validar(p, reel_id, local=False):
    if not ID_OK.match(reel_id or ""): falhar("reel_id invalido (use letras, numeros, _ ou -, ate 64)")
    imgs = p.get("imagens") or []
    if not 1 <= len(imgs) <= 5: falhar("envie de 1 a 5 imagens")
    for u in imgs:
        if not (u.startswith("https://") or (local and os.path.exists(u))): falhar(f"imagem precisa ser https: {u[:80]}")
    regras = {"gancho": (5, 45), "roteiro": (20, 280), "cta": (5, 60)}
    for campo, (lo, hi) in regras.items():
        v = str(p.get(campo, "")).strip()
        if not lo <= len(v) <= hi: falhar(f"'{campo}' precisa ter de {lo} a {hi} caracteres (tem {len(v)})")
    for campo in ("preco", "preco_de"):
        if p.get(campo) and not re.match(r"^\d{1,5}(,\d{2})?$", str(p[campo])): falhar(f"'{campo}' no formato 29,90")
    return {
        "imagens": imgs, "gancho": p["gancho"].strip(), "roteiro": p["roteiro"].strip(), "cta": p["cta"].strip(),
        "preco": str(p.get("preco", "")), "preco_de": str(p.get("preco_de", "")),
        "desconto": int(p.get("desconto") or 0), "voz": p.get("voz") or tts.VOZ_PADRAO,
        "trilha": p.get("trilha", "on") != "off", "layout": int(p.get("layout") or 1),
    }


def baixar(url):
    if not url.startswith("https://"): return Image.open(url).convert("RGB")
    erro = None
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=15).read())).convert("RGB")
        except Exception as e:
            erro = e; time.sleep(1 + tentativa)
    raise RuntimeError(f"nao baixou a imagem {url[:80]}: {erro}")


def baixar_todas(urls):
    imgs = []
    for u in urls:
        try: imgs.append(baixar(u))
        except RuntimeError as e: print(f"aviso: {e}", file=sys.stderr)
    if not imgs: falhar("nenhuma imagem baixou; nao vou publicar outra coisa")
    return imgs


# ---------- voz ----------
def narrar_partes(partes, voz, tmp):
    """Narra cada parte separada (tempos exatos de cada uma) e junta num WAV so."""
    amostras, palavras, trechos, t = [], [], [], 0.0
    taxa = 48000
    for i, (nome, texto, pausa) in enumerate(partes):
        wav = os.path.join(tmp, f"voz{i}.wav")
        dur, pals = tts.narrar(texto, wav, voz)
        with wave.open(wav) as w: amostras.append(np.frombuffer(w.readframes(w.getnframes()), dtype="<i2"))
        trechos.append({"nome": nome, "ini": t, "fim": t + dur})
        palavras += [{**p, "ini": p["ini"] + t, "fim": p["fim"] + t, "parte": nome} for p in pals]
        amostras.append(np.zeros(int(pausa * taxa), dtype="<i2"))
        t += dur + pausa
    saida = os.path.join(tmp, "voz.wav")
    with wave.open(saida, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa); w.writeframes(np.concatenate(amostras).tobytes())
    return saida, t, palavras, {tr["nome"]: tr for tr in trechos}


# ---------- desenho ----------
def fonte(sz):
    if os.path.exists(FONTE):
        f = ImageFont.truetype(FONTE, sz); f.set_variation_by_name("Bold"); return f
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def quebrar(texto, f, larg, d):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if d.textlength(teste, font=f) <= larg or not atual: atual = teste
        else: linhas.append(atual); atual = p
    return linhas + ([atual] if atual else [])


def caixa(texto, sz, fundo, cor, max_linhas=2, larg=TEXTO_LARG):
    """Texto em caixa arredondada; diminui a fonte ate caber em `max_linhas`."""
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    while True:
        f = fonte(sz); linhas = quebrar(texto, f, larg - 70, d)
        if len(linhas) <= max_linhas or sz <= 36: break
        sz -= 4
    alt_l = int(sz * 1.18); lw = max(d.textlength(l, font=f) for l in linhas)
    im = Image.new("RGBA", (int(lw) + 70, alt_l * len(linhas) + 50), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im); dd.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 34, fill=fundo + (255,))
    for i, l in enumerate(linhas):
        dd.text((im.width / 2, 25 + i * alt_l + alt_l / 2), l, font=f, fill=cor, anchor="mm")
    return im


def legenda(palavras, atual, destaque, sz=84):
    """Legenda branca com contorno navy; a palavra falada agora fica colorida."""
    f = fonte(sz); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    textos = [p.upper() for p in palavras]; esp = d.textlength(" ", font=f) * 1.4
    larg = sum(d.textlength(t, font=f) for t in textos) + esp * (len(textos) - 1)
    if larg > TEXTO_LARG: return legenda(palavras, atual, destaque, sz - 6)
    im = Image.new("RGBA", (int(larg) + 40, int(sz * 1.6)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 20
    for i, t in enumerate(textos):
        dd.text((x, im.height / 2), t, font=f, anchor="lm", fill=destaque if i == atual else WHITE,
                stroke_width=6, stroke_fill=NAVY)
        x += d.textlength(t, font=f) + esp
    return im


def colar(base, im, cx, cy, escala=1.0):
    if escala <= 0.02: return
    if abs(escala - 1) > 0.005:
        im = im.resize((max(1, int(im.width * escala)), max(1, int(im.height * escala))), Image.BILINEAR)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def entrar(t, ini, dur=0.25):  # escala com leve "salto" quando o texto aparece
    x = min(1.0, max(0.0, (t - ini) / dur)) - 1; s = 1.9
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def selo_logo():
    """Logo do @viumachado num cartao branco arredondado, presente o video inteiro."""
    if not os.path.exists(LOGO): return None
    lg = Image.open(LOGO).convert("RGB"); lw = int(lg.width * LOGO_ALT / lg.height)
    lg = lg.resize((lw, LOGO_ALT), Image.LANCZOS); pad = 12
    im = Image.new("RGBA", (lw + 2 * pad, LOGO_ALT + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 28, fill=WHITE + (240,))
    im.paste(lg, (pad, pad)); return im


# ---------- cenas ----------
RECORTES = [(0, 0, 1, 1), (0.1, 0, 0.9, 0.62), (0.1, 0.38, 0.9, 1), (0.18, 0.18, 0.82, 0.82)]


def preparar_cenas(imgs, dur):
    """Uma cena a cada ~2,5 s. Com 1 foto, alterna recortes (inteiro, cima, baixo, centro)."""
    n = max(1, math.ceil(dur / CENA_S)); cenas = []
    for i in range(n):
        img = imgs[i % len(imgs)]
        r = RECORTES[0] if len(imgs) > 1 and i < len(imgs) else RECORTES[(i // len(imgs)) % len(RECORTES)]
        frente = img.crop((int(r[0] * img.width), int(r[1] * img.height), int(r[2] * img.width), int(r[3] * img.height)))
        esc = max(W / img.width, H / img.height)
        fundo = img.resize((int(img.width * esc) + 1, int(img.height * esc) + 1), Image.BILINEAR)
        fundo = fundo.crop(((fundo.width - W) // 2, (fundo.height - H) // 2, (fundo.width - W) // 2 + W, (fundo.height - H) // 2 + H))
        fundo = Image.blend(fundo.filter(ImageFilter.GaussianBlur(45)), Image.new("RGB", (W, H), NAVY), 0.35).convert("RGBA")
        alt = min(int(FOTO_LARG * frente.height / frente.width), 1150)
        cenas.append({"fundo": fundo, "frente": frente, "caixa": (FOTO_LARG, alt), "ini": i * dur / n, "fim": (i + 1) * dur / n})
    return cenas


def foto_quadro(cena, t):
    """Foto da cena com zoom lento (Ken Burns) e cantos arredondados."""
    bw, bh = cena["caixa"]; p = (t - cena["ini"]) / max(0.01, cena["fim"] - cena["ini"])
    z = 1.0 + 0.08 * p + 0.05 * max(0.0, 1 - (t - cena["ini"]) / 0.15)  # leve "soco" no corte
    fr = cena["frente"]; esc = max(bw / fr.width, bh / fr.height) * z
    im = fr.resize((int(fr.width * esc) + 1, int(fr.height * esc) + 1), Image.BILINEAR)
    im = im.crop(((im.width - bw) // 2, (im.height - bh) // 2, (im.width - bw) // 2 + bw, (im.height - bh) // 2 + bh)).convert("RGBA")
    mask = Image.new("L", (bw, bh), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), 40, fill=255)
    im.putalpha(mask); return im


# ---------- linha do tempo ----------
def blocos_legenda(palavras):
    roteiro = [p for p in palavras if p["parte"] == "roteiro"]; blocos = []
    for i in range(0, len(roteiro), PALAVRAS_POR_LEGENDA):
        grupo = roteiro[i:i + PALAVRAS_POR_LEGENDA]
        fim = roteiro[i + PALAVRAS_POR_LEGENDA]["ini"] if i + PALAVRAS_POR_LEGENDA < len(roteiro) else grupo[-1]["fim"] + 0.3
        blocos.append({"palavras": grupo, "ini": grupo[0]["ini"], "fim": fim})
    return blocos


def montar_tempos(trechos, dur):
    gancho_fim = max(GANCHO_MIN_S, trechos["gancho"]["fim"])
    cta_ini = min(trechos["cta"]["ini"], dur - CTA_MIN_S)
    preco_ini = max(gancho_fim + 0.3, 0.4 * dur)
    preco_fim = min(preco_ini + PRECO_S, cta_ini - 0.2)
    return {"gancho_fim": gancho_fim, "cta_ini": cta_ini, "preco_ini": preco_ini, "preco_fim": preco_fim}


def textos_fixos(d, lay):
    preco = f"De R$ {d['preco_de']} por R$ {d['preco']}" if d["preco_de"] else (f"Por R$ {d['preco']}" if d["preco"] else "")
    return {
        "gancho": caixa(d["gancho"], 92, lay["gancho_fundo"], lay["gancho_cor"]),
        "preco": caixa(preco, 66, lay["preco_fundo"], NAVY if lay["preco_fundo"] == YELLOW else WHITE, 1) if preco else None,
        "off": caixa(f"{d['desconto']}% OFF", 84, lay["off_fundo"], WHITE, 1) if d["desconto"] > 0 else None,
        "cta": caixa(d["cta"], 74, lay["cta_fundo"], WHITE, 3),
        "logo": selo_logo(),
    }


def desenhar(t, cena, tx, tempos, blocos, lay, cache):
    f = cena["fundo"].copy()
    colar(f, foto_quadro(cena, t), W / 2, lay["foto_y"])
    if t < tempos["gancho_fim"]:
        colar(f, tx["gancho"], W / 2, lay["gancho_y"], entrar(t, 0.05))
    if tx["preco"] and tempos["preco_ini"] <= t < tempos["preco_fim"]:
        colar(f, tx["preco"], W / 2, lay["preco_y"], entrar(t, tempos["preco_ini"]))
        if tx["off"]: colar(f, tx["off"], W / 2, lay["preco_y"] + 140, entrar(t, tempos["preco_ini"] + 0.15))
    if t >= tempos["cta_ini"]:
        pulso = 1 + 0.03 * math.sin((t - tempos["cta_ini"]) * 2 * math.pi * 1.4)
        colar(f, tx["cta"], W / 2, lay["cta_y"], entrar(t, tempos["cta_ini"]) * pulso)
    elif t >= tempos["gancho_fim"]:
        for bi, b in enumerate(blocos):
            if b["ini"] <= t < b["fim"]:
                atual = max([i for i, p in enumerate(b["palavras"]) if p["ini"] <= t] or [0])
                chave = (bi, atual)
                if chave not in cache: cache[chave] = legenda([p["texto"] for p in b["palavras"]], atual, lay["destaque"])
                colar(f, cache[chave], W / 2, lay["legenda_y"]); break
    if tx["logo"]: f.alpha_composite(tx["logo"], LOGO_POS)
    return f.convert("RGB")


# ---------- render ----------
def mixar_audio(voz_wav, dur, trilha, tmp):
    saida = os.path.join(tmp, "audio.wav")
    filtro_voz = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=7,apad[v]"
    if trilha:
        mus = os.path.join(tmp, "musica.wav"); trilhas.make("lofi", dur, mus)
        filtro = f"{filtro_voz};[1:a]volume=0.10[m];[v][m]amix=inputs=2:duration=longest:normalize=0[a]"
        entradas = ["-i", voz_wav, "-i", mus]
    else:
        filtro = filtro_voz.replace("[v]", "[a]"); entradas = ["-i", voz_wav]
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", *entradas, "-filter_complex", filtro,
                           "-map", "[a]", "-t", f"{dur:.2f}", "-ar", "48000", "-ac", "2", saida])
    return saida


def renderizar(d, cenas, tx, tempos, blocos, lay, dur, audio, saida_mp4, saida_jpg):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "4M", "-bufsize", "8M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-shortest",
           "-movflags", "+faststart", saida_mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE); cache = {}; capa_frame = int(1.2 * FPS)
    for i in range(int(round(dur * FPS))):
        t = i / FPS; cena = next(c for c in cenas if t < c["fim"] or c is cenas[-1])
        quadro = desenhar(t, cena, tx, tempos, blocos, lay, cache)
        if i == capa_frame: quadro.save(saida_jpg, quality=90)
        proc.stdin.write(quadro.tobytes())
    proc.stdin.close()
    if proc.wait() != 0: falhar("ffmpeg falhou no render")


def conferir(mp4):
    info = subprocess.run(["ffmpeg", "-i", mp4], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    if not (DUR_MIN - 0.3 <= dur <= DUR_MAX + 0.3): falhar(f"duracao fora do limite: {dur:.1f}s")
    if f"{W}x{H}" not in info: falhar("resolucao diferente de 1080x1920")
    if "Audio:" not in info: falhar("video sem audio")
    return dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-file"); ap.add_argument("--id"); ap.add_argument("--out-dir", default="reels")
    ap.add_argument("--local", action="store_true", help="aceita caminhos de arquivo nas imagens (so para teste)")
    a = ap.parse_args()
    reel_id = a.id or os.environ.get("REEL_ID", "")
    try:
        bruto = open(a.payload_file, encoding="utf-8").read() if a.payload_file else base64.b64decode(os.environ.get("PAYLOAD_B64", "")).decode("utf-8")
        payload = json.loads(bruto)
    except Exception as e:
        falhar(f"payload invalido: {e}")
    d = validar(payload, reel_id, a.local); lay = layout(d["layout"])
    os.makedirs(a.out_dir, exist_ok=True); tmp = tempfile.mkdtemp(); inicio = time.time()

    imgs = baixar_todas(d["imagens"])
    partes = [("gancho", d["gancho"], PAUSA_APOS_GANCHO), ("roteiro", d["roteiro"], PAUSA_ANTES_CTA), ("cta", d["cta"], 0)]
    voz_wav, fala, palavras, trechos = narrar_partes(partes, d["voz"], tmp)
    if fala > FALA_MAX: falhar(f"roteiro longo demais: a fala deu {fala:.1f}s (maximo {FALA_MAX:.0f}s)")
    dur = min(DUR_MAX, max(DUR_MIN, fala + FOLGA_FINAL))

    cenas = preparar_cenas(imgs, dur); tx = textos_fixos(d, lay)
    tempos = montar_tempos(trechos, dur); blocos = blocos_legenda(palavras)
    audio = mixar_audio(voz_wav, dur, d["trilha"], tmp)
    mp4 = os.path.join(a.out_dir, f"{reel_id}.mp4"); jpg = os.path.join(a.out_dir, f"{reel_id}.jpg")
    renderizar(d, cenas, tx, tempos, blocos, lay, dur, audio, mp4, jpg)
    dur_real = conferir(mp4)
    meta = {"reel_id": reel_id, "versao": "v2", "duracao": round(dur_real, 2), "fala": round(fala, 2),
            "layout": d["layout"], "voz": d["voz"], "trilha": d["trilha"], "imagens": len(imgs),
            "tamanho_mb": round(os.path.getsize(mp4) / 1e6, 2), "render_s": round(time.time() - inicio, 1)}
    with open(os.path.join(a.out_dir, f"{reel_id}.json"), "w", encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__": main()
