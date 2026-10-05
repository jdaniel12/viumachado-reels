#!/usr/bin/env python3
"""Gera painel/painel.html a partir de um JSON de métricas.
Uso: python3 painel/build.py dados.json  (grava painel/painel.html)"""
import json, sys, pathlib
base = pathlib.Path(__file__).parent
dados = json.load(open(sys.argv[1], encoding="utf-8"))
html = (base / "template.html").read_text(encoding="utf-8").replace("__DADOS__", json.dumps(dados, ensure_ascii=False))
(base / "painel.html").write_text(html, encoding="utf-8")
print("ok", len(html))
