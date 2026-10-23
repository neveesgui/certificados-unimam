"""
MÓDULO 4: TEMPLATE DINÂMICO (core/template_config.py)
-------------------------------------------------------------------------
Objetivo: Isolar as coordenadas (X, Y), tamanhos de fonte, cores e posição
do QR Code em um dicionário/JSON externo.
Por que fazer assim?
Se a professora quiser mudar a arte de fundo no próximo semestre, não será
necessário alterar nenhuma linha de código Python (evita "Hardcoding" /
números mágicos espalhados pelo motor de desenho).
"""

import json
from pathlib import Path
from typing import Any, Dict

# Define a raiz do projeto usando pathlib.
# O QUE FAZ: Pega o caminho deste arquivo (__file__), sobe dois níveis (.parent.parent).
# POR QUE: Garante que o sistema encontre os arquivos JSON e imagens mesmo se
# for executado de diretórios diferentes ou dentro da função Serverless da Vercel.
BASE_DIR = Path(__file__).resolve().parent.parent

# Caminho padrão para o arquivo JSON de configuração do template
CAMINHO_CONFIG_PADRAO = BASE_DIR / "assets" / "templates" / "config_padrao.json"


def carregar_config_template(caminho_json: Path = CAMINHO_CONFIG_PADRAO) -> Dict[str, Any]:
    """
    Lê o arquivo JSON de configuração do template e retorna um dicionário Python validado.
    """
    # O QUE FAZ: Verifica se o arquivo JSON realmente existe no disco antes de tentar abrir.
    # POR QUE: Fornece um erro claro e amigável caso o arquivo tenha sido movido ou deletado.
    if not caminho_json.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração do template não encontrado em: {caminho_json}"
        )

    # O QUE FAZ: Abre o arquivo com codificação UTF-8 no gerenciador de contexto (with).
    # POR QUE: O 'encoding="utf-8"' evita problemas com acentos em português, e o 'with'
    # garante que o arquivo seja fechado automaticamente da memória após a leitura.
    with open(caminho_json, mode="r", encoding="utf-8") as arquivo:
        config = json.load(arquivo)

    # O QUE FAZ: Valida se a seção essencial ('campos') existe no JSON.
    # POR QUE: Princípio "Fail-Fast" (Falhe Rápido) — se a professora editar o JSON e
    # esquecer a estrutura de campos, avisamos imediatamente antes de processar a turma.
    if "campos" not in config:
        raise ValueError("O JSON de template é inválido: falta a seção 'campos'.")

    return config
