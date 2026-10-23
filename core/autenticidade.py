"""
MÓDULO 2: SISTEMA DE AUTENTICIDADE DE DUPLA CAMADA (core/autenticidade.py)
-------------------------------------------------------------------------
Arquitetura Sênior Definitiva (3 Camadas de Persistência e Validação):
1. Camada Cloud (Vercel KV / Upstash Redis REST API):
   Se as variáveis KV_REST_API_URL / UPSTASH_REDIS_REST_URL estiverem ativas na Vercel,
   salva e consulta as chaves permanentemente na nuvem (vitalício, via HTTP nativo).
2. Camada Local / Cache (/tmp na Vercel ou data/ no computador local):
   Funciona instantaneamente sem configuração extra.
3. Camada Criptográfica Stateless (Verificação Matemática SHA-256 + SECRET_KEY):
   Recalcula o Hash SHA-256 a partir dos dados impressos no certificado + SECRET_KEY do servidor.
   Funciona para sempre mesmo se nenhum banco de dados estiver configurado!
"""

import base64
import hashlib
import hmac
import json
import os
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import qrcode
from PIL import Image

SECRET_KEY = os.getenv(
    "CERT_SECRET_KEY",
    "chave-secreta-academica-super-segura-trocar-na-vercel-2026"
)

# Suporte nativo ao banco gratuito da própria Vercel (Vercel KV / Upstash Redis via HTTP REST)
KV_URL = (
    os.getenv("KV_REST_API_URL")
    or os.getenv("UPSTASH_REDIS_REST_URL")
    or ""
).rstrip("/")
KV_TOKEN = (
    os.getenv("KV_REST_API_TOKEN")
    or os.getenv("UPSTASH_REDIS_REST_TOKEN")
    or ""
)

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_REGISTRO = BASE_DIR / "data" / "certificados_registro.json"


def _nfc(texto: str) -> str:
    """
    Converte caracteres Unicode decompostos (NFD, comum no macOS) para compostos (NFC).
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
    """
    return {
        "nome": _nfc(nome).title(),
        "documento": _nfc(documento) or "Isento",
        "evento": _nfc(evento),
        "carga_horaria": _nfc(str(carga_horaria)),
        "data_emissao": _nfc(data_emissao),
    }


def gerar_assinatura_e_codigo(dados_normalizados: Dict[str, str]) -> Tuple[str, str]:
    """
    Gera a assinatura SHA-256 e a Chave Única ('CERT-XXXXXXXXXXXX') usando os 4 campos
    visíveis no certificado + a SECRET_KEY exclusiva do servidor.
    """
    carga_dados = (
        f"{dados_normalizados['nome']}|"
        f"{dados_normalizados['evento'].lower()}|"
        f"{dados_normalizados['carga_horaria']}|"
        f"{dados_normalizados['data_emissao']}|"
        f"{SECRET_KEY}"
    )

    hash_completo = hashlib.sha256(carga_dados.encode("utf-8")).hexdigest()
    codigo_curto = f"CERT-{hash_completo[:12].upper()}"
    return hash_completo, codigo_curto


def empacotar_token_validacao(dados_normalizados: Dict[str, str], hash_completo: str) -> str:
    """Empacota os dados do certificado + assinatura em um token Base64 URL-Safe."""
    pacote = {
        "d": dados_normalizados,
        "sig": hash_completo[:24],
    }
    json_bytes = json.dumps(pacote, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8")


def _salvar_no_vercel_kv(chave: str, registro: Dict[str, Any]) -> None:
    """
    Salva o registro permanentemente no Vercel KV / Upstash Redis (se configurado no painel da Vercel).
    Usa `urllib.request` nativo do Python para não exigir pacotes extras.
    """
    if not KV_URL or not KV_TOKEN:
        return
    try:
        payload = json.dumps(["SET", f"cert:{chave}", json.dumps(registro, ensure_ascii=False)]).encode("utf-8")
        req = urllib.request.Request(
            KV_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {KV_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.5) as _:
            pass
    except Exception:
        pass


def _buscar_no_vercel_kv(chave: str) -> Optional[Dict[str, Any]]:
    """
    Consulta uma Chave Única no Vercel KV / Upstash Redis (se configurado).
    """
    if not KV_URL or not KV_TOKEN:
        return None
    try:
        payload = json.dumps(["GET", f"cert:{chave}"]).encode("utf-8")
        req = urllib.request.Request(
            KV_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {KV_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            resposta_json = json.loads(resp.read().decode("utf-8"))
            valor_str = resposta_json.get("result")
            if valor_str:
                return json.loads(valor_str)
    except Exception:
        return None
    return None


def salvar_no_registro_local(codigo_curto: str, dados_normalizados: Dict[str, str], token: str) -> None:
    """
    Salva a Chave Única:
    1. Na nuvem permanente (Vercel KV / Upstash), se configurada.
    2. Em arquivo JSON local (`data/` no computador ou `/tmp/` na Vercel).
    """
    chave_upper = codigo_curto.upper()
    novo_registro = {
        "codigo": chave_upper,
        "dados": dados_normalizados,
        "token": token,
    }

    # 1. Salva na nuvem permanente (se KV_REST_API_URL estiver ativo na Vercel)
    _salvar_no_vercel_kv(chave_upper, novo_registro)

    # 2. Salva no disco local ou /tmp
    try:
        ARQUIVO_REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        registros: Dict[str, Any] = {}
        if ARQUIVO_REGISTRO.exists():
            with open(ARQUIVO_REGISTRO, mode="r", encoding="utf-8") as f:
                registros = json.load(f)
        registros[chave_upper] = novo_registro
        with open(ARQUIVO_REGISTRO, mode="w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
    except OSError:
        caminho_tmp = Path("/tmp/certificados_registro.json")
        registros_tmp: Dict[str, Any] = {}
        if caminho_tmp.exists():
            with open(caminho_tmp, mode="r", encoding="utf-8") as f:
                registros_tmp = json.load(f)
        registros_tmp[chave_upper] = novo_registro
        with open(caminho_tmp, mode="w", encoding="utf-8") as f:
            json.dump(registros_tmp, f, ensure_ascii=False, indent=2)


def gerar_qrcode_imagem(url_validacao: str, tamanho_px: int = 220) -> Image.Image:
    """Mantido por compatibilidade caso algum template futuro utilize QR Code."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url_validacao)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#1A365D", back_color="white").convert("RGB")
    return img_qr.resize((tamanho_px, tamanho_px), Image.Resampling.NEAREST)


def validar_certificado(
    codigo: Optional[str] = None,
    token: Optional[str] = None,
    nome: Optional[str] = None,
    evento: Optional[str] = None,
    carga_horaria: Optional[str] = None,
    data_emissao: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifica se um certificado é AUTÊNTICO em 3 camadas:
    1. Busca no banco em nuvem (Vercel KV / Upstash) ou registro local/tmp pelo código curto.
    2. Se os dados do certificado (nome, evento, carga_horaria, data_emissao) forem informados,
       recalcula o Hash SHA-256 matematicamente (100% Stateless, não precisa de banco!).
    3. Valida o token assinado com hmac.compare_digest.
    """
    codigo_limpo = (codigo or "").strip().upper()
    if codigo_limpo and not codigo_limpo.startswith("CERT-"):
        codigo_limpo = f"CERT-{codigo_limpo}"

    # CAMADA 1 e 2: Busca pelo código curto no registro local/tmp ou no Vercel KV
    if codigo_limpo and not token:
        for caminho in [ARQUIVO_REGISTRO, Path("/tmp/certificados_registro.json")]:
            if caminho.exists():
                try:
                    with open(caminho, mode="r", encoding="utf-8") as f:
                        registros = json.load(f)
                    if codigo_limpo in registros:
                        token = registros[codigo_limpo]["token"]
                        break
                except Exception:
                    continue

        if not token:
            registro_kv = _buscar_no_vercel_kv(codigo_limpo)
            if registro_kv and "token" in registro_kv:
                token = registro_kv["token"]

    # CAMADA 3: Verificação Matemática Stateless (quando o validador informa os dados impressos no certificado)
    if codigo_limpo and not token and nome and evento and carga_horaria and data_emissao:
        dados_teste = normalizar_dados_aluno(
            nome=nome,
            documento="Isento",
            evento=evento,
            carga_horaria=carga_horaria,
            data_emissao=data_emissao,
        )
        hash_calc, codigo_calc = gerar_assinatura_e_codigo(dados_teste)
        if hmac.compare_digest(codigo_limpo, codigo_calc.upper()):
            token = empacotar_token_validacao(dados_teste, hash_calc)
            # Re-hidrata o cache automaticamente!
            salvar_no_registro_local(codigo_calc, dados_teste, token)
        else:
            return {
                "valido": False,
                "requer_dados_stateless": False,
                "mensagem": (
                    "ALERTA: A Chave de Autenticidade NÃO corresponde aos dados informados! "
                    "Confira se digitou exatamente como está no certificado."
                ),
                "dados": None,
            }

    # Se a chave não estava no cache temporário e os dados ainda não foram preenchidos,
    # pede a confirmação dos dados impressos para validação matemática Stateless!
    if not token:
        return {
            "valido": False,
            "requer_dados_stateless": True,
            "codigo_consultado": codigo_limpo,
            "mensagem": (
                "Para validar esta chave criptograficamente, confirme abaixo os dados impressos no certificado:"
            ),
            "dados": None,
        }

    # Validação final do token e assinatura SHA-256
    try:
        json_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
        pacote = json.loads(json_bytes.decode("utf-8"))
        dados_recebidos = pacote["d"]
        assinatura_recebida = pacote["sig"]

        hash_recalculado, codigo_recalculado = gerar_assinatura_e_codigo(dados_recebidos)
        assinatura_esperada = hash_recalculado[:24]

        assinatura_integra = hmac.compare_digest(assinatura_recebida, assinatura_esperada)
        if codigo_limpo and codigo_limpo != codigo_recalculado.upper():
            assinatura_integra = False

        if assinatura_integra:
            return {
                "valido": True,
                "codigo_autenticidade": codigo_recalculado,
                "hash_sha256": hash_recalculado,
                "mensagem": "Certificado Autêntico! Emitido oficialmente e verificado por assinatura SHA-256.",
                "dados": dados_recebidos,
            }
        else:
            return {
                "valido": False,
                "requer_dados_stateless": False,
                "mensagem": "ALERTA DE FRAUDE: A assinatura criptográfica não confere! Os dados foram adulterados.",
                "dados": None,
            }

    except Exception:
        return {
            "valido": False,
            "requer_dados_stateless": False,
            "mensagem": "Formato de chave ou token inválido.",
            "dados": None,
        }
