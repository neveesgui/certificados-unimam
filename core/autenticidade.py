"""
MÓDULO 2: SISTEMA DE AUTENTICIDADE (core/autenticidade.py)
-------------------------------------------------------------------------
Objetivo: Gerar uma Key Única (Hash SHA-256) e um QR Code antifraude a partir
dos dados do aluno, impedindo plágio, edição no Photoshop ou adulteração de carga horária.

Visão de Engenharia Sênior (Por que usar Chave Secreta + Hash?):
Se gerássemos um hash apenas com `sha256(nome + evento)`, um aluno com conhecimento
básico de programação poderia calcular o próprio hash para um nome falso.
Ao concatenar uma `SECRET_KEY` (Chave Secreta exclusiva do servidor da faculdade/professora)
dentro do `hashlib.sha256`, criamos uma Assinatura Digital. E ao embutir os dados assinados
na URL do QR Code, a validação funciona até em servidores Serverless (como a Vercel) sem
precisar pagar por um banco de dados externo!
"""

import base64
import hashlib
import hmac
import json
import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import qrcode
from PIL import Image

# O QUE FAZ: Busca a chave secreta nas variáveis de ambiente da Vercel/Sistema.
# Se não existir (ambiente de desenvolvimento local), usa uma chave padrão de fallback.
# POR QUE: Nunca devemos deixar senhas de produção fixas no código (Boas práticas 12-Factor App).
SECRET_KEY = os.getenv(
    "CERT_SECRET_KEY",
    "chave-secreta-academica-super-segura-trocar-na-vercel-2026"
)

# Caminho para o arquivo JSON que guarda o histórico local de certificados emitidos
BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_REGISTRO = BASE_DIR / "data" / "certificados_registro.json"


def _nfc(texto: str) -> str:
    """
    Converte caracteres Unicode decompostos (NFD, comum no macOS) para compostos (NFC).
    POR QUE: No NFD, 'é' vira 'e' + acento separado, o que pode gerar o símbolo '⍰' ao desenhar.
    No NFC, 'é' é um caractere único perfeito para fontes TrueType!
    """
    return unicodedata.normalize("NFC", texto.strip())


def normalizar_dados_aluno(
    nome: str,
    documento: str,
    evento: str,
    carga_horaria: str,
    data_emissao: str
) -> Dict[str, str]:
    """
    Limpa espaços extras, normaliza acentos em NFC e padroniza os dados antes de gerar o Hash.
    POR QUE: No SHA-256, "João Silva" e "João Silva " (com espaço no final) geram
    hashes completamente diferentes (Efeito Avalanche). Normalizar evita erros de validação!
    """
    return {
        "nome": _nfc(nome).title(),
        "documento": _nfc(documento),
        "evento": _nfc(evento),
        "carga_horaria": _nfc(str(carga_horaria)),
        "data_emissao": _nfc(data_emissao),
    }


def gerar_assinatura_e_codigo(dados_normalizados: Dict[str, str]) -> Tuple[str, str]:
    """
    Recebe o dicionário com os dados do aluno e gera:
    1. A assinatura completa (SHA-256 hexadecimal de 64 caracteres).
    2. A Key Única amigável para impressão no certificado (ex: 'CERT-A1B2C3D4E5F6').
    """
    # O QUE FAZ: Monta uma string única e determinística unindo os campos e a chave secreta.
    # POR QUE: Ordenar os campos garante que os mesmos dados sempre gerem exatamente o mesmo hash.
    carga_dados = (
        f"{dados_normalizados['nome']}|"
        f"{dados_normalizados['documento']}|"
        f"{dados_normalizados['evento']}|"
        f"{dados_normalizados['carga_horaria']}|"
        f"{dados_normalizados['data_emissao']}|"
        f"{SECRET_KEY}"
    )

    # O QUE FAZ: Converte a string para bytes UTF-8 (.encode) e aplica o algoritmo SHA-256.
    # POR QUE: O hashlib do Python opera exclusivamente sobre bytes, retornando um hash irreversível.
    hash_completo = hashlib.sha256(carga_dados.encode("utf-8")).hexdigest()

    # O QUE FAZ: Pega os primeiros 12 caracteres do hash em maiúsculas e adiciona o prefixo 'CERT-'.
    # POR QUE: Um hash de 64 caracteres é difícil de digitar manualmente caso alguém queira validar
    # sem câmera; 12 caracteres hexadecimais oferecem 281 trilhões de combinações (zero colisão em eventos).
    codigo_curto = f"CERT-{hash_completo[:12].upper()}"

    return hash_completo, codigo_curto


def empacotar_token_validacao(dados_normalizados: Dict[str, str], hash_completo: str) -> str:
    """
    Empacota os dados do certificado + assinatura em um token Base64 seguro para URLs.
    POR QUE: Permite que o próprio QR Code carregue os dados assinados criptograficamente.
    Assim, quando a Vercel (Serverless) receber a leitura do QR Code, ela consegue validar
    a autenticidade instantaneamente mesmo sem consultar um banco de dados!
    """
    # O QUE FAZ: Cria um pacote com os dados do certificado e um trecho verificador da assinatura.
    pacote = {
        "d": dados_normalizados,
        "sig": hash_completo[:24],  # 24 caracteres hexadecimais (96 bits de segurança criptográfica)
    }

    # O QUE FAZ: Converte o dicionário para JSON compacto (sem espaços extras) e depois para bytes.
    json_bytes = json.dumps(pacote, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # O QUE FAZ: Codifica em Base64 URL-Safe (troca '+' e '/' por '-' e '_') para não quebrar links HTTP.
    token_b64 = base64.urlsafe_b64encode(json_bytes).decode("utf-8")
    return token_b64


def salvar_no_registro_local(codigo_curto: str, dados_normalizados: Dict[str, str], token: str) -> None:
    """
    Salva a Key Única em um arquivo JSON local (ou /tmp na Vercel) para permitir
    consulta digitando apenas o código curto (ex: CERT-A1B2C3D4E5F6).
    """
    try:
        # Garante que a pasta 'data/' exista
        ARQUIVO_REGISTRO.parent.mkdir(parents=True, exist_ok=True)

        registros: Dict[str, Any] = {}
        if ARQUIVO_REGISTRO.exists():
            with open(ARQUIVO_REGISTRO, mode="r", encoding="utf-8") as f:
                registros = json.load(f)

        registros[codigo_curto.upper()] = {
            "codigo": codigo_curto.upper(),
            "dados": dados_normalizados,
            "token": token,
        }

        with open(ARQUIVO_REGISTRO, mode="w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
    except OSError:
        # POR QUE CAPTURAR OSError: Na Vercel, o diretório raiz é somente leitura (Read-Only File System).
        # Se a escrita em 'data/' falhar na nuvem, usamos '/tmp/certificados_registro.json' sem quebrar a execução!
        caminho_tmp = Path("/tmp/certificados_registro.json")
        registros_tmp: Dict[str, Any] = {}
        if caminho_tmp.exists():
            with open(caminho_tmp, mode="r", encoding="utf-8") as f:
                registros_tmp = json.load(f)
        registros_tmp[codigo_curto.upper()] = {
            "codigo": codigo_curto.upper(),
            "dados": dados_normalizados,
            "token": token,
        }
        with open(caminho_tmp, mode="w", encoding="utf-8") as f:
            json.dump(registros_tmp, f, ensure_ascii=False, indent=2)


def gerar_qrcode_imagem(url_validacao: str, tamanho_px: int = 220) -> Image.Image:
    """
    Transforma a URL de validação do certificado em uma imagem QR Code do Pillow (PIL).
    """
    # O QUE FAZ: Configura o objeto QRCode com nível de correção de erro 'M' (Médio - recupera até 15% de dano).
    # POR QUE: Se o certificado impresso amassar ou sujar levemente, a câmera do celular ainda conseguirá ler!
    qr = qrcode.QRCode(
        version=None,  # Ajusta o tamanho da matriz automaticamente conforme o tamanho da URL
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,      # Borda branca mínima (Quiet Zone) exigida pelos leitores ópticos de QR Code
    )

    # O QUE FAZ: Insere a URL de validação dentro da matriz do QR Code e compila os blocos.
    qr.add_data(url_validacao)
    qr.make(fit=True)

    # O QUE FAZ: Renderiza o QR Code como uma imagem Pillow em formato RGB (azul-marinho escuro sobre fundo branco).
    # POR QUE: Converter para '.convert("RGB")' garante compatibilidade total ao colar sobre o fundo PNG do certificado.
    img_qr = qr.make_image(fill_color="#1A365D", back_color="white").convert("RGB")

    # O QUE FAZ: Redimensiona exatamente para o tamanho definido no JSON de configuração (ex: 220x220 pixels).
    # POR QUE: Usa o filtro LANCZOS/NEAREST para manter as bordas do QR Code nítidas sem borrar os quadradinhos.
    img_qr = img_qr.resize((tamanho_px, tamanho_px), Image.Resampling.NEAREST)

    return img_qr


def validar_certificado(
    codigo: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifica se um certificado é AUTÊNTICO ou FALSO/ADULTERADO.
    Aceita validação tanto via Token do QR Code (Stateless) quanto via Key Única digitada.
    """
    # 1. Se a pessoa digitou apenas a Key Única (ex: CERT-1A2B3C4D5E6F), buscamos no registro
    if codigo and not token:
        codigo_limpo = codigo.strip().upper()
        for caminho in [ARQUIVO_REGISTRO, Path("/tmp/certificados_registro.json")]:
            if caminho.exists():
                with open(caminho, mode="r", encoding="utf-8") as f:
                    registros = json.load(f)
                if codigo_limpo in registros:
                    token = registros[codigo_limpo]["token"]
                    break

    # Se mesmo assim não houver token, o código não foi encontrado
    if not token:
        return {
            "valido": False,
            "mensagem": (
                "Certificado não localizado. Verifique se o código foi digitado "
                "corretamente ou escaneie o QR Code original do certificado."
            ),
            "dados": None,
        }

    # 2. Decodifica o token e recalcula o Hash SHA-256 com a SECRET_KEY do servidor
    try:
        json_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
        pacote = json.loads(json_bytes.decode("utf-8"))
        dados_recebidos = pacote["d"]
        assinatura_recebida = pacote["sig"]

        # O QUE FAZ: Recalcula o hash exatamente com a mesma função usada na emissão.
        hash_recalculado, codigo_recalculado = gerar_assinatura_e_codigo(dados_recebidos)
        assinatura_esperada = hash_recalculado[:24]

        # O QUE FAZ: Compara a assinatura recebida com a esperada usando hmac.compare_digest.
        # POR QUE: Evita ataques de tempo (Timing Attacks) e garante que nem 1 único bit dos dados
        # (nome, horas, evento) tenha sido alterado pelo aluno!
        assinatura_integra = hmac.compare_digest(assinatura_recebida, assinatura_esperada)

        # Se o usuário também informou um código manual, confere se bate com o código do token
        if codigo and codigo.strip().upper() != codigo_recalculado.upper():
            assinatura_integra = False

        if assinatura_integra:
            return {
                "valido": True,
                "codigo_autenticidade": codigo_recalculado,
                "hash_sha256": hash_recalculado,
                "mensagem": "Certificado Autêntico! Emitido oficialmente e verificado criptograficamente.",
                "dados": dados_recebidos,
            }
        else:
            return {
                "valido": False,
                "mensagem": "ALERTA DE FRAUDE: A assinatura criptográfica não confere! Os dados deste certificado foram adulterados.",
                "dados": None,
            }

    except Exception:
        return {
            "valido": False,
            "mensagem": "Token de validação corrompido ou formato inválido.",
            "dados": None,
        }
