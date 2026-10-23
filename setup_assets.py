"""
SCRIPT DE PREPARAÇÃO DE ASSETS (setup_assets.py)
-------------------------------------------------------------------------
Objetivo: Criar automaticamente:
1. Três opções de molduras institucionais em alta resolução (1920x1080) usando Pillow:
   - Moldura 1 (Clássica UNIMAM): Verde Institucional e Dourado sobre fundo marfim suave.
   - Moldura 2 (Executiva Minimalista): Linhas modernas em Verde UNIMAM e Grafite sobre branco puro.
   - Moldura 3 (Solene Acadêmica): Moldura dupla Dourada e Verde Escuro para simpósios e honrarias.
   (Todas com a Chave de Autenticidade apenas digitada, sem fundo colorido).
2. Planilhas fictícias de teste (.csv e .xlsx) no Modelo Completo (múltiplos eventos)
   e no Modelo Simplificado (apenas Nome e Matrícula/CPF).
"""

from pathlib import Path
from typing import List
import zipfile
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw

from core.motor_desenho import _carregar_fonte
from core.template_config import BASE_DIR


def _colar_cabecalho_unimam(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    cor_titulo: str,
    cor_linha: str,
) -> None:
    """
    Desenha a logo oficial da UNIMAM, o título CERTIFICADO DE PARTICIPAÇÃO,
    o subtítulo institucional e a assinatura da coordenação (elementos comuns às 3 molduras).
    """
    largura = img.width
    fonte_instituicao = _carregar_fonte(tamanho=25, negrito=True)
    fonte_titulo = _carregar_fonte(tamanho=60, negrito=True)
    fonte_subtitulo = _carregar_fonte(tamanho=27, negrito=False)
    fonte_rodape = _carregar_fonte(tamanho=22, negrito=False)

    caminho_logo = BASE_DIR / "static" / "logo_unimam.png"
    if caminho_logo.exists():
        logo_unimam = Image.open(caminho_logo).convert("RGBA")
        altura_logo = 76
        largura_logo = int(logo_unimam.width * (altura_logo / logo_unimam.height))
        logo_unimam = logo_unimam.resize((largura_logo, altura_logo), Image.Resampling.LANCZOS)
        pos_x_logo = (largura - largura_logo) // 2
        img.paste(logo_unimam, (pos_x_logo, 108), mask=logo_unimam.split()[-1])
    else:
        draw.text(
            (960, 150),
            "UNIMAM · CENTRO UNIVERSITÁRIO MARIA MILZA",
            fill="#008542",
            font=fonte_instituicao,
            anchor="mm",
        )

    draw.text(
        (960, 248),
        "CERTIFICADO DE PARTICIPAÇÃO",
        fill=cor_titulo,
        font=fonte_titulo,
        anchor="mm",
    )

    # Linha divisória abaixo do título
    draw.line([(560, 298), (1360, 298)], fill=cor_linha, width=3)

    draw.text(
        (960, 375),
        "Certificamos, para os devidos fins de comprovação de carga horária acadêmica, que:",
        fill="#4A5568",
        font=fonte_subtitulo,
        anchor="mm",
    )

    # Linha sutil sob o nome do aluno
    draw.line([(360, 512), (1560, 512)], fill="#CBD5E0", width=2)

    # Linha de assinatura da Professora / Coordenação no rodapé central
    draw.line([(660, 845), (1260, 845)], fill=cor_titulo, width=2)
    draw.text(
        (960, 880),
        "Coordenação de Extensão e Eventos Acadêmicos",
        fill=cor_titulo,
        font=fonte_rodape,
        anchor="mm",
    )


def criar_template_fundo_padrao() -> Path:
    """
    MOLDURA 1 (Padrão): Clássica Institucional (Verde Escuro e Dourado sobre fundo marfim).
    """
    caminho_destino = BASE_DIR / "assets" / "templates" / "fundo_padrao.png"
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    largura, altura = 1920, 1080
    img = Image.new("RGB", (largura, altura), color="#FAF9F5")
    draw = ImageDraw.Draw(img)

    # Moldura externa Verde Institucional Escuro (#0F3D24) e interna Dourada (#C59B27)
    draw.rectangle([48, 48, largura - 48, altura - 48], outline="#0F3D24", width=12)
    draw.rectangle([70, 70, largura - 70, altura - 70], outline="#C59B27", width=4)

    for cx, cy in [(48, 48), (largura - 128, 48), (48, altura - 128), (largura - 128, altura - 128)]:
        draw.rectangle([cx, cy, cx + 80, cy + 80], outline="#C59B27", width=3)

    _colar_cabecalho_unimam(img, draw, cor_titulo="#0F3D24", cor_linha="#C59B27")
    img.save(caminho_destino, format="PNG")
    return caminho_destino


def criar_template_fundo_moderno() -> Path:
    """
    MOLDURA 2 (Executiva Minimalista): Branco puro, faixas laterais em Verde UNIMAM (#008542)
    e moldura fina em grafite prateado.
    """
    caminho_destino = BASE_DIR / "assets" / "templates" / "fundo_moderno.png"
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    largura, altura = 1920, 1080
    img = Image.new("RGB", (largura, altura), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Faixas verticais modernas nas extremidades esquerda e direita
    draw.rectangle([0, 0, 28, altura], fill="#008542")
    draw.rectangle([largura - 28, 0, largura, altura], fill="#008542")

    # Moldura interna minimalista dupla em cinza-grafite e verde
    draw.rectangle([64, 54, largura - 64, altura - 54], outline="#D2D8D5", width=2)
    draw.rectangle([76, 66, largura - 76, altura - 66], outline="#008542", width=4)

    # Cantoneiras minimalistas verdes
    for x1, y1, x2, y2 in [
        (64, 54, 140, 54), (64, 54, 64, 130),
        (largura - 140, 54, largura - 64, 54), (largura - 64, 54, largura - 64, 130),
        (64, altura - 54, 140, altura - 54), (64, altura - 130, 64, altura - 54),
        (largura - 140, altura - 54, largura - 64, altura - 54), (largura - 64, altura - 130, largura - 64, altura - 54),
    ]:
        draw.line([(x1, y1), (x2, y2)], fill="#0F3D24", width=8)

    _colar_cabecalho_unimam(img, draw, cor_titulo="#1D1D1F", cor_linha="#008542")
    img.save(caminho_destino, format="PNG")
    return caminho_destino


def criar_template_fundo_solene() -> Path:
    """
    MOLDURA 3 (Solene Diplomática): Moldura dupla imperial em Dourado e Verde Musgo
    com ornamentos internos sobre fundo marfim clássico.
    """
    caminho_destino = BASE_DIR / "assets" / "templates" / "fundo_solene.png"
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    largura, altura = 1920, 1080
    img = Image.new("RGB", (largura, altura), color="#FCFBF7")
    draw = ImageDraw.Draw(img)

    # Borda tripla diplomática
    draw.rectangle([40, 40, largura - 40, altura - 40], outline="#C59B27", width=10)
    draw.rectangle([58, 58, largura - 58, altura - 58], outline="#0F3D24", width=6)
    draw.rectangle([72, 72, largura - 72, altura - 72], outline="#C59B27", width=2)

    # Ornamentos de canto duplos
    for cx, cy in [(58, 58), (largura - 158, 58), (58, altura - 158), (largura - 158, altura - 158)]:
        draw.rectangle([cx, cy, cx + 100, cy + 100], outline="#C59B27", width=3)
        draw.rectangle([cx + 14, cy + 14, cx + 86, cy + 86], outline="#0F3D24", width=2)

    _colar_cabecalho_unimam(img, draw, cor_titulo="#0F3D24", cor_linha="#C59B27")
    img.save(caminho_destino, format="PNG")
    return caminho_destino


def criar_todas_molduras() -> None:
    """Garante a criação das 3 molduras institucionais."""
    criar_template_fundo_padrao()
    criar_template_fundo_moderno()
    criar_template_fundo_solene()


def _salvar_matriz_em_xlsx(caminho_xlsx: Path, linhas: List[List[str]], nome_aba: str = "Turma") -> Path:
    """
    Salva uma matriz de linhas e colunas em um arquivo Excel (.xlsx) nativo e editável.
    """
    caminho_xlsx.parent.mkdir(parents=True, exist_ok=True)
    colunas_letras = ["A", "B", "C", "D", "E", "F", "G"]
    xml_linhas = []

    for num_linha, valores in enumerate(linhas, start=1):
        celulas = []
        for idx_col, valor in enumerate(valores):
            ref = f"{colunas_letras[idx_col]}{num_linha}"
            texto_escapado = escape(str(valor))
            celulas.append(f'<c r="{ref}" t="inlineStr"><is><t>{texto_escapado}</t></is></c>')
        xml_linhas.append(f'<row r="{num_linha}">{"".join(celulas)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_linhas)}</sheetData>'
        '</worksheet>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{nome_aba}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )

    with zipfile.ZipFile(caminho_xlsx, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    return caminho_xlsx


# Dados fictícios realistas para a aba Multi-Eventos (cada linha com seu próprio evento e moldura!)
DADOS_FICTICIOS_COMPLETOS = [
    ["nome", "documento", "evento", "carga_horaria", "data", "moldura"],
    ["Lais Cardoso de Medeiros", "20261045", "Tech Girls no Mercado de Trabalho", "8", "22/10/2026", "classica"],
    ["Ana Beatriz Oliveira", "20261089", "Semana Acadêmica de Engenharia de Software", "20", "22/10/2026", "executiva"],
    ["Carlos Eduardo Santos", "20261102", "Workshop de Python e Inteligência Artificial", "12", "22/10/2026", "executiva"],
    ["Fernanda Costa Lima", "20261150", "Simpósio de Inovação e Empreendedorismo UNIMAM", "16", "22/10/2026", "solene"],
    ["Gabriel Henrique Souza", "20261198", "Congresso Regional de Saúde e Biotecnologia", "24", "22/10/2026", "solene"],
    ["Juliana Mendes Rocha", "20261234", "Oficina Prática de UX/UI Design Moderno", "6", "22/10/2026", "classica"],
    ["Lucas Martins Almeida", "20261277", "Jornada de Iniciação Científica da UNIMAM", "30", "22/10/2026", "solene"],
    ["Mariana Ribeiro Alves", "20261310", "Palestra Ética e Inteligência Artificial na Educação", "4", "22/10/2026", "executiva"],
]

# Modelo 2: Planilha Simplificada (Lista de Presença Rápida — usa o Evento e Horas digitados na tela)
DADOS_FICTICIOS_SIMPLIFICADOS = [
    ["nome", "documento"],
    ["Lais Cardoso de Medeiros", "20261045"],
    ["Ana Beatriz Oliveira", "20261089"],
    ["Carlos Eduardo Santos", "20261102"],
    ["Fernanda Costa Lima", "20261150"],
    ["Gabriel Henrique Souza", "20261198"],
    ["Juliana Mendes Rocha", "20261234"],
]


def criar_csv_exemplo() -> Path:
    """Cria a planilha CSV de teste no Modelo Completo (5 colunas)."""
    caminho_csv = BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.csv"
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    linhas_str = [",".join(linha) for linha in DADOS_FICTICIOS_COMPLETOS]
    caminho_csv.write_text("\n".join(linhas_str) + "\n", encoding="utf-8-sig")
    return caminho_csv


def criar_xlsx_exemplo() -> Path:
    """Cria a planilha Excel (.xlsx) de teste no Modelo Completo (5 colunas)."""
    caminho_xlsx = BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.xlsx"
    return _salvar_matriz_em_xlsx(caminho_xlsx, DADOS_FICTICIOS_COMPLETOS, nome_aba="Modelo_Completo")


def criar_csv_simplificado() -> Path:
    """Cria a planilha CSV editável no Modelo Simplificado (apenas nome e documento)."""
    caminho_csv = BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.csv"
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    linhas_str = [",".join(linha) for linha in DADOS_FICTICIOS_SIMPLIFICADOS]
    caminho_csv.write_text("\n".join(linhas_str) + "\n", encoding="utf-8-sig")
    return caminho_csv


def criar_xlsx_simplificado() -> Path:
    """Cria a planilha Excel (.xlsx) editável no Modelo Simplificado (apenas nome e documento)."""
    caminho_xlsx = BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.xlsx"
    return _salvar_matriz_em_xlsx(caminho_xlsx, DADOS_FICTICIOS_SIMPLIFICADOS, nome_aba="Lista_Presenca")


if __name__ == "__main__":
    criar_todas_molduras()
    criar_csv_exemplo()
    criar_xlsx_exemplo()
    criar_csv_simplificado()
    criar_xlsx_simplificado()
    print("[OK] 3 Molduras institucionais e 4 planilhas modelo (.csv e .xlsx) criadas com sucesso!")
