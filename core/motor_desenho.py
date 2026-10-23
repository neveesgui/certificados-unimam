"""
MÓDULO 1: MOTOR DE DESENHO (core/motor_desenho.py)
-------------------------------------------------------------------------
Objetivo: Abrir a imagem base do certificado, enquadrar automaticamente os textos
dentro das margens (quebrando linhas ou ajustando a fonte para nunca vazar da moldura)
e estampar a Chave Única de Autenticidade (sem necessidade de QR Code).
"""

import io
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from core.autenticidade import (
    empacotar_token_validacao,
    gerar_assinatura_e_codigo,
    normalizar_dados_aluno,
    salvar_no_registro_local,
)
from core.template_config import BASE_DIR, carregar_config_template


def _carregar_fonte(tamanho: int, negrito: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Carrega uma fonte TrueType (.ttf) de forma resiliente em qualquer Sistema Operacional
    (Windows, macOS ou Linux Serverless da Vercel).

    POR QUE FAZER ASSIM:
    Servidores Linux na nuvem (como a Vercel) não possuem "arial.ttf" instalada por padrão.
    Testamos uma lista de fontes comuns e, se nenhuma existir, usamos a fonte vetorial
    embutida do Pillow 10+ (`load_default(size=tamanho)`), garantindo que o sistema NUNCA trave!
    """
    candidatas_negrito = [
        str(BASE_DIR / "assets" / "fonts" / "fonte_negrito.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux / Vercel
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",     # macOS
        "C:/Windows/Fonts/arialbd.ttf",                          # Windows
    ]
    candidatas_regular = [
        str(BASE_DIR / "assets" / "fonts" / "fonte_regular.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux / Vercel
        "/System/Library/Fonts/Supplemental/Arial.ttf",          # macOS
        "C:/Windows/Fonts/arial.ttf",                            # Windows
    ]

    lista_busca = candidatas_negrito if negrito else candidatas_regular

    for caminho_fonte in lista_busca:
        try:
            return ImageFont.truetype(caminho_fonte, size=tamanho)
        except OSError:
            continue

    # Fallback seguro do Pillow 10+ que aceita tamanho customizado sem depender de arquivos externos
    return ImageFont.load_default(size=tamanho)


# Formatos aceitos como tema. POR QUE: são os formatos que o Pillow abre nativamente
# e que qualquer professora consegue exportar do Canva, PowerPoint ou Photoshop.
FORMATOS_TEMA_ACEITOS = {"PNG", "JPEG", "WEBP"}


def preparar_imagem_fundo(imagem: Image.Image, config_template: Dict[str, Any]) -> Image.Image:
    """
    Normaliza QUALQUER imagem de tema para as dimensões definidas no JSON.

    POR QUE: As coordenadas X/Y do JSON foram pensadas para 1920x1080. Se a professora
    enviar uma arte A4 (3508x2480) ou um print de celular, o nome do aluno sairia no
    lugar errado. Redimensionando o fundo, as coordenadas continuam válidas sempre.
    """
    if imagem.format and imagem.format not in FORMATOS_TEMA_ACEITOS:
        raise ValueError(f"Formato '{imagem.format}' não suportado. Use PNG, JPG ou WEBP.")

    largura = config_template.get("dimensoes", {}).get("largura", 1920)
    altura = config_template.get("dimensoes", {}).get("altura", 1080)

    # Se o PNG tiver transparência, cola sobre um fundo branco para não ficar preto ao converter para RGB.
    if imagem.mode in ("RGBA", "LA", "P"):
        imagem = imagem.convert("RGBA")
        fundo_branco = Image.new("RGB", imagem.size, "#FFFFFF")
        fundo_branco.paste(imagem, mask=imagem.split()[-1])
        imagem = fundo_branco
    else:
        imagem = imagem.convert("RGB")

    return ImageOps.fit(imagem, (largura, altura), method=Image.Resampling.LANCZOS)


def _quebrar_linhas_por_pixel(
    desenhador: ImageDraw.ImageDraw,
    texto: str,
    fonte: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    largura_maxima_px: int,
) -> List[str]:
    """
    Divide um texto longo em várias linhas medindo a largura real em pixels de cada palavra.

    POR QUE FAZER ASSIM:
    Se desenharmos o texto do evento em uma linha só, títulos grandes vazam para fora da
    moldura do certificado. Medindo com `desenhador.textlength`, garantimos que nenhuma
    linha ultrapasse a margem segura (ex: 1440px em um certificado de 1920px).
    """
    palavras = texto.split()
    if not palavras:
        return [""]

    linhas: List[str] = []
    linha_atual = palavras[0]

    for palavra in palavras[1:]:
        teste_linha = f"{linha_atual} {palavra}"
        # O QUE FAZ: Mede quantos pixels a frase ocuparia se adicionássemos a próxima palavra.
        if desenhador.textlength(teste_linha, font=fonte) <= largura_maxima_px:
            linha_atual = teste_linha
        else:
            linhas.append(linha_atual)
            linha_atual = palavra

    linhas.append(linha_atual)
    return linhas


def _enquadrar_texto_inteligente(
    desenhador: ImageDraw.ImageDraw,
    texto: str,
    tamanho_inicial: int,
    negrito: bool,
    largura_maxima_px: int,
    max_linhas: int = 1,
) -> Tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    """
    Ajusta automaticamente a quebra de linha e o tamanho da fonte para que o texto
    fique sempre perfeitamente enquadrado dentro da moldura do certificado.
    """
    tamanho_atual = tamanho_inicial
    tamanho_minimo = 16

    while tamanho_atual >= tamanho_minimo:
        fonte = _carregar_fonte(tamanho=tamanho_atual, negrito=negrito)
        linhas = _quebrar_linhas_por_pixel(desenhador, texto, fonte, largura_maxima_px)

        # Verifica se a quantidade de linhas cabe no limite permitido para aquele campo
        # e se nenhuma palavra isolada ficou maior que a largura máxima
        maior_largura = max(desenhador.textlength(l, font=fonte) for l in linhas)
        if len(linhas) <= max_linhas and maior_largura <= largura_maxima_px:
            return "\n".join(linhas), fonte

        # Se ainda não coube, reduz 2 pontos na fonte e tenta novamente
        tamanho_atual -= 2

    fonte_final = _carregar_fonte(tamanho=tamanho_minimo, negrito=negrito)
    linhas_finais = _quebrar_linhas_por_pixel(desenhador, texto, fonte_final, largura_maxima_px)
    return "\n".join(linhas_finais), fonte_final


def gerar_certificado_individual(
    nome: str,
    documento: str,
    evento: str,
    carga_horaria: str,
    data_emissao: str,
    url_base_validacao: str = "http://localhost:8000/validar",
    config_template: Optional[Dict[str, Any]] = None,
    imagem_fundo_customizada: Optional[bytes] = None,
    moldura_escolhida: str = "padrao",
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Gera o certificado completo em memória (bytes PNG) e retorna também os metadados de autenticidade.
    """
    # 1. Carrega as coordenadas X e Y do Template Dinâmico (JSON)
    if config_template is None:
        config_template = carregar_config_template()

    # 2. Normaliza os dados e gera o Hash SHA-256 + Key Única + Token Assinado
    dados_norm = normalizar_dados_aluno(nome, documento, evento, carga_horaria, data_emissao)
    hash_completo, codigo_curto = gerar_assinatura_e_codigo(dados_norm)
    token_validacao = empacotar_token_validacao(dados_norm, hash_completo)

    # Salva no registro local para permitir consulta rápida digitando apenas a Chave Única
    salvar_no_registro_local(codigo_curto, dados_norm, token_validacao)

    url_completa_validacao = f"{url_base_validacao}?codigo={codigo_curto}"

    # 3. Abre e normaliza a imagem base do certificado (Moldura Customizada ou uma das 3 Molduras Oficiais)
    if imagem_fundo_customizada:
        imagem_certificado = preparar_imagem_fundo(
            Image.open(io.BytesIO(imagem_fundo_customizada)), config_template
        )
    else:
        mapa_molduras = config_template.get("molduras_disponiveis", {})
        caminho_relativo = mapa_molduras.get(moldura_escolhida, config_template["imagem_fundo"])
        caminho_fundo = BASE_DIR / caminho_relativo
        imagem_certificado = preparar_imagem_fundo(Image.open(caminho_fundo), config_template)

    # 4. Inicializa o pincel de desenho (ImageDraw) sobre a imagem do certificado
    desenhador = ImageDraw.Draw(imagem_certificado)

    # 5. Prepara os textos exatos que serão escritos em cada campo (SEM o número do documento no meio do texto!)
    textos_para_desenhar = {
        "nome_aluno": dados_norm["nome"],
        "texto_evento": (
            f"Participou com êxito do evento acadêmico \"{dados_norm['evento']}\", "
            f"perfazendo carga horária total de {dados_norm['carga_horaria']} horas."
        ),
        "data_emissao": f"Emitido em: {dados_norm['data_emissao']}",
        "codigo_autenticidade": f"Chave de Autenticidade: {codigo_curto}",
    }

    # Largura máxima segura para o texto nunca encostar nas bordas laterais (padrão: 1440px de 1920px)
    largura_maxima_padrao = config_template.get("largura_maxima_texto", 1440)

    # 6. Laço de desenho: percorre cada campo, calcula o enquadramento e desenha centralizado
    campos_config = config_template["campos"]
    for nome_campo, texto in textos_para_desenhar.items():
        if nome_campo not in campos_config:
            continue

        cfg = campos_config[nome_campo]
        coordenada_xy = (cfg["x"], cfg["y"])
        cor_texto = cfg.get("cor_hex", "#000000")
        ancora = cfg.get("alinhamento_ancora", "mm")
        max_linhas = cfg.get("max_linhas", 2 if nome_campo == "texto_evento" else 1)
        largura_campo = cfg.get("largura_maxima", largura_maxima_padrao)

        texto_enquadrado, fonte_ajustada = _enquadrar_texto_inteligente(
            desenhador=desenhador,
            texto=texto,
            tamanho_inicial=cfg.get("tamanho_fonte", 30),
            negrito=cfg.get("negrito", False),
            largura_maxima_px=largura_campo,
            max_linhas=max_linhas,
        )

        # O QUE FAZ: Usa multiline_text com align="center" e anchor="mm".
        # POR QUE: Garante que textos de 1, 2 ou 3 linhas fiquem perfeitamente centralizados
        # tanto horizontalmente quanto verticalmente dentro do certificado!
        desenhador.multiline_text(
            xy=coordenada_xy,
            text=texto_enquadrado,
            fill=cor_texto,
            font=fonte_ajustada,
            anchor=ancora,
            align="center",
            spacing=12,
        )

    # 7. Salva a imagem finalizada em um buffer de memória RAM (io.BytesIO)
    buffer_memoria = io.BytesIO()
    imagem_certificado.save(buffer_memoria, format="PNG", optimize=True)
    buffer_memoria.seek(0)

    metadados = {
        "codigo_autenticidade": codigo_curto,
        "hash_sha256": hash_completo,
        "token_validacao": token_validacao,
        "url_validacao": url_completa_validacao,
        "dados": dados_norm,
    }

    return buffer_memoria.getvalue(), metadados
