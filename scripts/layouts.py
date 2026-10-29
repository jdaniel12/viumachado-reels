"""Os 3 layouts do Reel v2: onde fica cada texto e com quais cores (paleta da marca).

Posicoes em pixels no quadro 1080x1920. A faixa de baixo (~250 px) e a lateral
direita (~120 px) ficam livres por causa dos botoes do Instagram; o canto de cima
a esquerda (~230 x 210 px) e da logo.
"""
NAVY = (26, 26, 75); GREEN = (126, 217, 87); ORANGE = (250, 110, 30)
BLUE = (50, 200, 240); YELLOW = (250, 170, 20); RED = (230, 57, 80); WHITE = (255, 255, 255)

LAYOUTS = {
    1: {  # gancho no alto, legenda embaixo da foto
        "gancho_y": 380, "gancho_fundo": YELLOW, "gancho_cor": NAVY,
        "foto_y": 1040, "legenda_y": 1610, "destaque": YELLOW,
        "preco_y": 330, "preco_fundo": GREEN, "off_fundo": RED,
        "cta_y": 1610, "cta_fundo": ORANGE,
    },
    2: {  # gancho no centro sobre a foto, preco no alto, legenda embaixo
        "gancho_y": 960, "gancho_fundo": NAVY, "gancho_cor": WHITE,
        "foto_y": 960, "legenda_y": 1560, "destaque": GREEN,
        "preco_y": 310, "preco_fundo": ORANGE, "off_fundo": NAVY,
        "cta_y": 960, "cta_fundo": GREEN,
    },
    3: {  # gancho embaixo da foto, preco no alto
        "gancho_y": 1580, "gancho_fundo": ORANGE, "gancho_cor": WHITE,
        "foto_y": 940, "legenda_y": 1560, "destaque": BLUE,
        "preco_y": 310, "preco_fundo": BLUE, "off_fundo": ORANGE,
        "cta_y": 1580, "cta_fundo": NAVY,
    },
}


def layout(n):
    return LAYOUTS.get(int(n), LAYOUTS[1])
