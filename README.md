# viumachado-reels

Gera os Reels do @viumachado. O fluxo do n8n dispara o workflow **Gerar Reel**
(`workflow_dispatch`) com a URL da arte 9:16 e um id; o vídeo fica em
`reels/<id>.mp4` e é servido em
`https://raw.githubusercontent.com/jdaniel12/viumachado-reels/main/reels/<id>.mp4`.
Só os 10 mais recentes são mantidos.

## Reel v2 (tela cheia com narração)

Dispare o mesmo workflow com `versao=v2`, `reel_id` e `payload` (JSON em base64):

```json
{
  "imagens": ["https://...jpg"],
  "gancho": "Achei isso por R$ 29",
  "roteiro": "2 a 3 frases, até 280 caracteres.",
  "cta": "Comenta EU QUERO que eu te mando o link",
  "preco": "29,90", "preco_de": "59,90", "desconto": 50,
  "voz": "pt-BR-FranciscaNeural", "trilha": "on", "layout": 1
}
```

Gera `reels/<id>.mp4` (15–25 s, 1080x1920, H.264/AAC), `reels/<id>.jpg` (capa) e
`reels/<id>.json` (dados do render). Sem `versao`, o workflow segue gerando o v1.
Teste local: `python scripts/reel_v2.py --payload-file teste.json --id teste --local`.
Fonte: Fredoka (SIL OFL, `assets/fonts/OFL.txt`). Voz: edge-tts.
