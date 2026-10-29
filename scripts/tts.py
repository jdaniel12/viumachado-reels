"""Narracao do Reel v2. Camada fina: trocar de provedor de voz mexe so aqui.

Hoje usa o edge-tts (voz pt-BR-FranciscaNeural, escolhida em 23/10/2026).
Devolve o audio em WAV e os tempos de cada palavra (em segundos).
"""
import asyncio, os, subprocess, wave

VOZ_PADRAO = "pt-BR-FranciscaNeural"
TICKS_POR_SEGUNDO = 10_000_000  # o edge-tts mede o tempo em unidades de 100 ns
TENTATIVAS = 3


async def _sintetizar(texto, voz, mp3_path):
    import edge_tts
    palavras = []
    com = edge_tts.Communicate(texto, voz, rate="+8%", boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for parte in com.stream():
            if parte["type"] == "audio":
                f.write(parte["data"])
            elif parte["type"] == "WordBoundary":
                ini = parte["offset"] / TICKS_POR_SEGUNDO
                palavras.append({"texto": parte["text"], "ini": ini,
                                 "fim": ini + parte["duration"] / TICKS_POR_SEGUNDO})
    return palavras


def narrar(texto, wav_path, voz=VOZ_PADRAO):
    """Gera a fala em `wav_path` (48 kHz mono). Retorna (duracao_s, palavras)."""
    mp3_path = wav_path + ".mp3"
    erro = None
    for _ in range(TENTATIVAS):
        try:
            palavras = asyncio.run(_sintetizar(texto, voz, mp3_path))
            if palavras and os.path.getsize(mp3_path) > 0:
                break
        except Exception as e:  # rede instavel no runner: tenta de novo
            erro = e
    else:
        raise RuntimeError(f"Falha na narracao (TTS): {erro}")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3_path,
                           "-ar", "48000", "-ac", "1", wav_path])
    with wave.open(wav_path) as w:
        dur = w.getnframes() / w.getframerate()
    return dur, palavras
