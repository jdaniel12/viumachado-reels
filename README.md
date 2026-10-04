# viumachado-reels

Gera os Reels do @viumachado. O fluxo do n8n dispara o workflow **Gerar Reel**
(`workflow_dispatch`) com a URL da arte 9:16 e um id; o vídeo fica em
`reels/<id>.mp4` e é servido em
`https://raw.githubusercontent.com/jdaniel12/viumachado-reels/main/reels/<id>.mp4`.
Só os 10 mais recentes são mantidos.
