// Nó "Montar roteiro do Reel v2" (n8n, Code, uma vez para todos os itens).
// Monta gancho, roteiro e chamada a partir da oferta escolhida e entrega o
// payload em base64 que o workflow "Gerar Reel" (versao=v2) espera.
// Sem IA paga: frases-modelo que variam pelo produto.
const o = $('Escolher oferta e legenda').first().json;

const num = t => Number(String(t).replace(/[^\d,]/g, '').replace(',', '.'));
const fmt = v => v.toFixed(2).replace('.', ',');
const atual = num(o.precoTxt);
const desc = Math.round(num(o.descTxt));
const original = atual / (1 - desc / 100);

// nome do produto: primeira linha da legenda, sem o emoji, encurtado
const titulo = String(o.caption || '').split(String.fromCharCode(10))[0].replace(/^🔥\s*/, '');
const limpo = titulo.replace(/[\[\(【].*?[\]\)】]/g, ' ').replace(/[|/+*#_]/g, ' ').replace(/\s+/g, ' ').trim();
let nome = '';
for (const p of limpo.split(' ')) {
  if ((nome + ' ' + p).trim().length > 40 || nome.split(' ').length >= 6) break;
  nome = (nome + ' ' + p).trim();
}
if (nome.length < 3) nome = 'Esse achado';

// varia as frases pelo id do produto (o mesmo produto sempre gera o mesmo texto)
const semente = [...String(o.itemId)].reduce((s, c) => s + c.charCodeAt(0), 0);
const escolher = lista => lista[semente % lista.length];

const ganchos = [
  'Isso por menos de R$ ' + Math.ceil(atual) + '?',
  desc + '% OFF na Shopee? Olha isso!',
  'Achei esse achado e fiquei chocada',
  'Corre que esse preço não dura',
  'Para tudo e olha esse preço',
].filter(g => g.length >= 5 && g.length <= 45);

const roteiro = (nome + '. De R$ ' + fmt(original) + ' por apenas R$ ' + fmt(atual)
  + '. São ' + desc + '% de desconto na Shopee.').slice(0, 280);

const cta = escolher(['O link tá no grupo, entra pela bio!', 'Entra no grupo da bio e pega o link!']);

const payload = {
  imagens: [o.imageUrl],
  gancho: escolher(ganchos),
  roteiro,
  cta,
  preco: fmt(atual),
  preco_de: fmt(original),
  desconto: desc,
  layout: (new Date().getDate() % 3) + 1,
};

return [{ json: {
  reel_id: o.artId,
  payload: Buffer.from(JSON.stringify(payload), 'utf8').toString('base64'),
  roteiro: payload,
} }];
