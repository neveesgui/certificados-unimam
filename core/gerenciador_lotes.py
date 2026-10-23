"""
MÓDULO 3: GERENCIADOR DE LOTES (core/gerenciador_lotes.py)
-------------------------------------------------------------------------
Objetivo: Ler planilhas de alunos em múltiplos formatos:
- Planilha CSV (.csv), TSV (.tsv) ou Texto (.txt)
- Planilha Microsoft Excel / Google Planilhas (.xlsx)
Processar todos os alunos com um laço `for`, gerar os certificados individualmente
e empacotar tudo em um arquivo `.zip` (junto com a planilha de auditoria das Chaves Únicas).
"""

import csv
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from core.motor_desenho import gerar_certificado_individual
from core.template_config import carregar_config_template


def _limpar_nome_arquivo(texto: str) -> str:
    """
    Remove caracteres especiais e espaços para criar um nome de arquivo seguro.
    Exemplo: "Maria José (BCC)" -> "Maria_Jose_BCC"
    """
    texto_limpo = re.sub(r"[^\w\s-]", "", texto.strip())
    return re.sub(r"[-\s]+", "_", texto_limpo)


def _decodificar_csv_inteligente(conteudo_bytes: bytes) -> str:
    """
    Decodifica os bytes do arquivo CSV tratando diferenças entre Google Forms e Excel BR.
    """
    try:
        return conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return conteudo_bytes.decode("latin-1")


def _indice_coluna_excel(referencia_celula: str) -> int:
    """
    Converte a referência de célula do Excel (ex: 'A1', 'C5', 'AA2') no índice numérico da coluna (0, 2, 26...).
    POR QUE: Se uma célula do meio estiver vazia no Excel (ex: pulou de A1 para C1), precisamos
    saber exatamente a qual coluna cada valor pertence!
    """
    letras = "".join(ch for ch in referencia_celula if ch.isalpha()).upper()
    indice = 0
    for letra in letras:
        indice = indice * 26 + (ord(letra) - ord("A") + 1)
    return max(indice - 1, 0)


def _extrair_linhas_xlsx(conteudo_bytes: bytes) -> List[Dict[str, str]]:
    """
    Lê um arquivo Microsoft Excel (.xlsx) nativamente usando `zipfile` e `xml.etree.ElementTree`.
    POR QUE FAZER ASSIM:
    O formato .xlsx (OpenXML) é um arquivo ZIP contendo arquivos XML padronizados.
    Ao lê-lo com a biblioteca nativa do Python, o sistema suporta planilhas do Excel e Google Sheets
    sem depender de bibliotecas pesadas de terceiros!
    """
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with zipfile.ZipFile(io.BytesIO(conteudo_bytes), mode="r") as zf:
        # 1. Carrega a tabela de textos compartilhados (sharedStrings.xml), se existir no Excel
        textos_compartilhados: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            raiz_ss = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item_si in raiz_ss.findall("main:si", ns):
                pedacos = [n.text or "" for n in item_si.findall(".//main:t", ns)]
                textos_compartilhados.append("".join(pedacos))

        # 2. Localiza a primeira aba da planilha (sheet1.xml)
        planilhas = sorted(
            nome for nome in zf.namelist()
            if nome.startswith("xl/worksheets/sheet") and nome.endswith(".xml")
        )
        if not planilhas:
            raise ValueError("A planilha Excel (.xlsx) não contém abas de dados válidas.")

        raiz_sheet = ET.fromstring(zf.read(planilhas[0]))
        linhas_matriz: List[List[str]] = []

        for elem_linha in raiz_sheet.findall(".//main:sheetData/main:row", ns):
            valores_linha: Dict[int, str] = {}
            maior_col = -1

            for celula in elem_linha.findall("main:c", ns):
                ref = celula.attrib.get("r", "A1")
                idx_col = _indice_coluna_excel(ref)
                maior_col = max(maior_col, idx_col)

                tipo_celula = celula.attrib.get("t", "")
                valor_texto = ""

                if tipo_celula == "s":
                    # Texto vindo da tabela sharedStrings
                    elem_v = celula.find("main:v", ns)
                    if elem_v is not None and elem_v.text is not None:
                        idx_str = int(elem_v.text)
                        if 0 <= idx_str < len(textos_compartilhados):
                            valor_texto = textos_compartilhados[idx_str]
                elif tipo_celula == "inlineStr":
                    # Texto embutido diretamente na célula
                    pedacos = [n.text or "" for n in celula.findall(".//main:t", ns)]
                    valor_texto = "".join(pedacos)
                else:
                    # Número ou valor direto
                    elem_v = celula.find("main:v", ns)
                    if elem_v is not None and elem_v.text is not None:
                        valor_texto = elem_v.text

                valores_linha[idx_col] = valor_texto.strip()

            if maior_col >= 0:
                linha_completa = [valores_linha.get(i, "") for i in range(maior_col + 1)]
                if any(linha_completa):
                    linhas_matriz.append(linha_completa)

    if len(linhas_matriz) < 2:
        return []

    cabecalhos = [col.strip().lower() for col in linhas_matriz[0]]
    registros: List[Dict[str, str]] = []
    for linha_valores in linhas_matriz[1:]:
        dicionario_linha: Dict[str, str] = {}
        for idx, nome_coluna in enumerate(cabecalhos):
            if nome_coluna:
                dicionario_linha[nome_coluna] = linha_valores[idx] if idx < len(linha_valores) else ""
        registros.append(dicionario_linha)

    return registros


def _extrair_linhas_planilha(conteudo_bytes: bytes, nome_arquivo: str = "") -> List[Dict[str, str]]:
    """
    Detecta automaticamente se o arquivo enviado é uma planilha Excel (.xlsx)
    ou um arquivo de texto separado por delimitadores (.csv, .tsv, .txt).
    """
    # O QUE FAZ: Verifica se o arquivo começa com a assinatura binária 'PK\x03\x04' (formato ZIP/XLSX)
    # ou se possui extensão .xlsx.
    eh_xlsx = conteudo_bytes[:4] == b"PK\x03\x04" or nome_arquivo.lower().endswith(".xlsx")
    if eh_xlsx:
        return _extrair_linhas_xlsx(conteudo_bytes)

    texto_csv = _decodificar_csv_inteligente(conteudo_bytes)
    primeira_linha = texto_csv.splitlines()[0] if texto_csv.splitlines() else ""

    # Suporta separação por TAB (.tsv), ponto-e-vírgula (Excel BR) ou vírgula (Padrão CSV)
    if "\t" in primeira_linha:
        delimitador = "\t"
    elif ";" in primeira_linha and "," not in primeira_linha:
        delimitador = ";"
    else:
        delimitador = ","

    leitor_csv = csv.DictReader(io.StringIO(texto_csv), delimiter=delimitador)
    return [
        {(k.strip().lower() if k else ""): (v.strip() if v else "") for k, v in linha.items()}
        for linha in leitor_csv
    ]


def processar_lote_csv(
    conteudo_csv_bytes: bytes,
    url_base_validacao: str = "http://localhost:8000/validar",
    evento_padrao: str = "Evento Acadêmico",
    carga_horaria_padrao: str = "4",
    data_emissao_padrao: str = "22/10/2026",
    imagem_fundo_customizada: Optional[bytes] = None,
    nome_arquivo_planilha: str = "",
    moldura_escolhida: str = "padrao",
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Lê os bytes de uma planilha (.csv, .xlsx ou .tsv), percorre cada aluno com um laço `for`,
    gera os certificados e retorna os bytes de um arquivo `.zip` pronto para download + relatório.
    """
    linhas_planilha = _extrair_linhas_planilha(conteudo_csv_bytes, nome_arquivo=nome_arquivo_planilha)

    # Carrega a configuração do template apenas 1 vez antes do laço 'for' (Otimização de I/O)
    config_template = carregar_config_template()

    buffer_zip = io.BytesIO()
    relatorio_emissoes: List[Dict[str, Any]] = []

    with zipfile.ZipFile(buffer_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as arquivo_zip:
        # O QUE FAZ: Laço 'for' principal que percorre cada aluno da planilha (.csv ou .xlsx).
        for indice, linha_limpa in enumerate(linhas_planilha, start=1):
            nome_aluno = (
                linha_limpa.get("nome")
                or linha_limpa.get("aluno")
                or linha_limpa.get("participante")
                or linha_limpa.get("nome completo")
                or ""
            )

            if not nome_aluno:
                continue

            documento = (
                linha_limpa.get("documento")
                or linha_limpa.get("cpf")
                or linha_limpa.get("ra")
                or linha_limpa.get("matricula")
                or linha_limpa.get("matrícula")
                or "Isento"
            )
            evento = linha_limpa.get("evento") or evento_padrao
            carga_horaria = (
                linha_limpa.get("carga_horaria")
                or linha_limpa.get("carga horária")
                or linha_limpa.get("horas")
                or carga_horaria_padrao
            )
            data_emissao = (
                linha_limpa.get("data")
                or linha_limpa.get("data_emissao")
                or linha_limpa.get("data de emissão")
                or data_emissao_padrao
            )

            # Permite que cada linha da planilha Multi-Eventos defina sua própria moldura!
            moldura_bruta = (
                linha_limpa.get("moldura")
                or linha_limpa.get("tema")
                or ""
            ).strip().lower()
            mapa_alias_moldura = {
                "1": "padrao",
                "padrao": "padrao",
                "padrão": "padrao",
                "classica": "padrao",
                "clássica": "padrao",
                "2": "moderno",
                "moderno": "moderno",
                "moderna": "moderno",
                "executiva": "moderno",
                "clean": "moderno",
                "3": "solene",
                "solene": "solene",
                "dourada": "solene",
            }
            moldura_da_linha = mapa_alias_moldura.get(moldura_bruta, moldura_escolhida)

            png_bytes, metadados = gerar_certificado_individual(
                nome=nome_aluno,
                documento=documento,
                evento=evento,
                carga_horaria=carga_horaria,
                data_emissao=data_emissao,
                url_base_validacao=url_base_validacao,
                config_template=config_template,
                imagem_fundo_customizada=imagem_fundo_customizada,
                moldura_escolhida=moldura_da_linha,
            )

            nome_seguro = _limpar_nome_arquivo(nome_aluno)
            codigo_curto = metadados["codigo_autenticidade"]
            nome_arquivo_png = f"certificados/{indice:03d}_{nome_seguro}_{codigo_curto}.png"

            arquivo_zip.writestr(nome_arquivo_png, png_bytes)

            relatorio_emissoes.append({
                "ordem": indice,
                "nome": metadados["dados"]["nome"],
                "documento": metadados["dados"]["documento"],
                "evento": metadados["dados"]["evento"],
                "carga_horaria": metadados["dados"]["carga_horaria"],
                "data_emissao": metadados["dados"]["data_emissao"],
                "codigo_autenticidade": codigo_curto,
                "url_validacao": metadados["url_validacao"],
            })

        # Gera a planilha de auditoria dentro do próprio ZIP para a secretaria/professora
        buffer_relatorio = io.StringIO()
        colunas_relatorio = [
            "ordem",
            "nome",
            "documento",
            "evento",
            "carga_horaria",
            "data_emissao",
            "codigo_autenticidade",
            "url_validacao",
        ]
        escritor_relatorio = csv.DictWriter(buffer_relatorio, fieldnames=colunas_relatorio)
        escritor_relatorio.writeheader()
        escritor_relatorio.writerows(relatorio_emissoes)

        arquivo_zip.writestr(
            "relatorio_chaves_autenticidade.csv",
            buffer_relatorio.getvalue().encode("utf-8-sig"),
        )

    buffer_zip.seek(0)
    return buffer_zip.getvalue(), relatorio_emissoes
