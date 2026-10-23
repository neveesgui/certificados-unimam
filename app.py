"""
MÓDULOS 5 E 6: INTERFACE WEB E ROTA DE VALIDAÇÃO (app.py)
-------------------------------------------------------------------------
Objetivo: Expor as funcionalidades do gerador de certificados na Web usando
o framework FastAPI, compatível com hospedagem Serverless na Vercel.
"""

import io
import zipfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Path as FastAPIPath, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError

from core.autenticidade import validar_certificado
from core.gerenciador_lotes import _limpar_nome_arquivo, processar_lote_csv
from core.motor_desenho import gerar_certificado_individual
from core.template_config import BASE_DIR
from setup_assets import (
    criar_csv_exemplo,
    criar_csv_simplificado,
    criar_todas_molduras,
    criar_xlsx_exemplo,
    criar_xlsx_simplificado,
)

TAMANHO_MAX_TEMA = 8 * 1024 * 1024
TIPOS_TEMA_ACEITOS = {"image/png", "image/jpeg", "image/webp"}

MAPA_ARQUIVOS_MOLDURA = {
    "padrao": BASE_DIR / "assets" / "templates" / "fundo_padrao.png",
    "moderno": BASE_DIR / "assets" / "templates" / "fundo_moderno.png",
    "solene": BASE_DIR / "assets" / "templates" / "fundo_solene.png",
}
PASTA_HTML = BASE_DIR / "templates_html"

app = FastAPI(
    title="UNIMAM · Sistema Integrado de Certificados Acadêmicos",
    description="Emissão e validação criptográfica de certificados universitários com suporte a CSV e Excel (.xlsx).",
    version="3.1.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def _garantir_assets_iniciais() -> None:
    """
    Cria as 3 molduras PNG e as planilhas de exemplo (.csv e .xlsx) caso não existam.
    """
    if not all(caminho.exists() for caminho in MAPA_ARQUIVOS_MOLDURA.values()):
        criar_todas_molduras()
    if not (BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.csv").exists():
        criar_csv_exemplo()
    if not (BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.xlsx").exists():
        criar_xlsx_exemplo()
    if not (BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.csv").exists():
        criar_csv_simplificado()
    if not (BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.xlsx").exists():
        criar_xlsx_simplificado()


async def _ler_tema_enviado(arquivo: Optional[UploadFile]) -> Optional[bytes]:
    """
    Lê e valida o tema (imagem de fundo) enviado pela professora.
    Retorna None quando nenhum tema customizado foi enviado.
    """
    if not arquivo or not arquivo.filename:
        return None

    if arquivo.content_type not in TIPOS_TEMA_ACEITOS:
        raise HTTPException(status_code=400, detail="Tema deve ser PNG, JPG ou WEBP.")

    conteudo = await arquivo.read()
    if len(conteudo) > TAMANHO_MAX_TEMA:
        raise HTTPException(status_code=400, detail="Tema acima de 8 MB.")
    return conteudo


def _url_validacao(request: Request) -> str:
    """Descobre o domínio atual (ex: https://meu-app.vercel.app/validar)."""
    return f"{str(request.base_url).rstrip('/')}/validar"


# ===================== PÁGINAS =====================

@app.get("/", response_class=HTMLResponse)
async def pagina_inicial() -> HTMLResponse:
    """Entrega a interface principal."""
    _garantir_assets_iniciais()
    return HTMLResponse((PASTA_HTML / "index.html").read_text(encoding="utf-8"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    """Entrega o ícone do pássaro da UNIMAM na aba do navegador."""
    return FileResponse(BASE_DIR / "static" / "favicon.png", media_type="image/png")


@app.get("/validar", response_class=HTMLResponse)
async def pagina_validacao() -> HTMLResponse:
    """Página pública de verificação da Chave de Autenticidade."""
    return HTMLResponse((PASTA_HTML / "validar.html").read_text(encoding="utf-8"))


# ===================== API DE MOLDURAS =====================

@app.get("/api/tema-padrao")
async def tema_padrao() -> FileResponse:
    """Devolve a Moldura 1 (Clássica UNIMAM)."""
    _garantir_assets_iniciais()
    return FileResponse(MAPA_ARQUIVOS_MOLDURA["padrao"], media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.get("/api/tema/{nome_moldura}")
async def obter_moldura(nome_moldura: str = FastAPIPath(...)) -> FileResponse:
    """Devolve a miniatura de qualquer uma das 3 molduras oficiais (padrao, moderno, solene)."""
    _garantir_assets_iniciais()
    caminho = MAPA_ARQUIVOS_MOLDURA.get(nome_moldura, MAPA_ARQUIVOS_MOLDURA["padrao"])
    return FileResponse(caminho, media_type="image/png", headers={"Cache-Control": "no-cache"})


# ===================== API DE EMISSÃO E VALIDAÇÃO =====================

@app.post("/api/emitir-individual")
async def rota_emitir_individual(
    request: Request,
    nome: str = Form(...),
    evento: str = Form(...),
    carga_horaria: str = Form(...),
    data_emissao: str = Form(...),
    documento: str = Form("Isento"),
    moldura_escolhida: str = Form("padrao"),
    fundo_customizado: Optional[UploadFile] = File(None),
) -> StreamingResponse:
    """Gera um certificado e devolve o PNG."""
    _garantir_assets_iniciais()
    tema = await _ler_tema_enviado(fundo_customizado)

    try:
        png_bytes, metadados = gerar_certificado_individual(
            nome=nome,
            documento=documento or "Isento",
            evento=evento,
            carga_horaria=carga_horaria,
            data_emissao=data_emissao,
            url_base_validacao=_url_validacao(request),
            imagem_fundo_customizada=tema,
            moldura_escolhida=moldura_escolhida,
        )
    except (ValueError, UnidentifiedImageError) as erro:
        raise HTTPException(status_code=400, detail=str(erro) or "Imagem de tema inválida.")

    codigo = metadados["codigo_autenticidade"]
    nome_arquivo = f"Certificado_{_limpar_nome_arquivo(nome)}_{codigo}.png"

    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
            "X-Certificado-Codigo": codigo,
        },
    )


@app.post("/api/emitir-lote")
async def rota_emitir_lote(
    request: Request,
    arquivo_csv: UploadFile = File(...),
    evento_padrao: str = Form("Evento Acadêmico"),
    carga_horaria_padrao: str = Form("8"),
    data_emissao_padrao: str = Form("22/10/2026"),
    moldura_escolhida: str = Form("padrao"),
    fundo_customizado: Optional[UploadFile] = File(None),
) -> StreamingResponse:
    """Processa a planilha da turma (.CSV, .XLSX ou .TSV) e devolve um .ZIP com todos os certificados."""
    _garantir_assets_iniciais()
    tema = await _ler_tema_enviado(fundo_customizado)

    try:
        zip_bytes, relatorio = processar_lote_csv(
            conteudo_csv_bytes=await arquivo_csv.read(),
            url_base_validacao=_url_validacao(request),
            evento_padrao=evento_padrao,
            carga_horaria_padrao=carga_horaria_padrao,
            data_emissao_padrao=data_emissao_padrao,
            imagem_fundo_customizada=tema,
            nome_arquivo_planilha=arquivo_csv.filename or "",
            moldura_escolhida=moldura_escolhida,
        )
    except (ValueError, UnidentifiedImageError, zipfile.BadZipFile) as erro:
        raise HTTPException(status_code=400, detail=str(erro) or "Planilha inválida. Envie .xlsx ou .csv.")

    if not relatorio:
        raise HTTPException(status_code=400, detail="Nenhum aluno encontrado. Confira a coluna 'nome'.")

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="Certificados_Turma_UNIMAM.zip"',
            "X-Total-Emitidos": str(len(relatorio)),
        },
    )


@app.get("/api/validar", response_class=JSONResponse)
async def rota_api_validar(
    codigo: Optional[str] = Query(None, description="Chave curta impressa no certificado (ex: CERT-...)"),
    token: Optional[str] = Query(None, description="Token assinado opcional"),
    nome: Optional[str] = Query(None, description="Nome impresso no certificado (para validação Stateless)"),
    evento: Optional[str] = Query(None, description="Evento impresso no certificado"),
    carga_horaria: Optional[str] = Query(None, description="Horas impressas no certificado"),
    data_emissao: Optional[str] = Query(None, description="Data impressa no certificado (DD/MM/AAAA)"),
) -> JSONResponse:
    """Verifica a autenticidade via Chave de Autenticidade (Banco KV, Cache ou Cálculo Stateless SHA-256)."""
    resultado = validar_certificado(
        codigo=codigo,
        token=token,
        nome=nome,
        evento=evento,
        carga_horaria=carga_horaria,
        data_emissao=data_emissao,
    )
    return JSONResponse(content=resultado, status_code=200 if resultado["valido"] else 404)


# ===================== PLANILHAS MODELO EDITÁVEIS (2 TIPOS) =====================

@app.get("/api/exemplo-csv")
async def baixar_csv_exemplo() -> Response:
    """Modelo 1 (Completo - Múltiplos Eventos) em formato CSV."""
    caminho = BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.csv"
    if not caminho.exists():
        caminho = criar_csv_exemplo()
    return Response(
        content=caminho.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="planilha_teste_completa_unimam.csv"'},
    )


@app.get("/api/exemplo-xlsx")
async def baixar_xlsx_exemplo() -> Response:
    """Modelo 1 (Completo - Múltiplos Eventos) em formato Excel (.xlsx)."""
    caminho = BASE_DIR / "assets" / "exemplos" / "alunos_exemplo.xlsx"
    if not caminho.exists():
        caminho = criar_xlsx_exemplo()
    return Response(
        content=caminho.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="planilha_teste_completa_unimam.xlsx"'},
    )


@app.get("/api/exemplo-simplificado-csv")
async def baixar_csv_simplificado() -> Response:
    """Modelo 2 (Simplificado - Lista de Presença Rápida: Nome e Documento) em CSV."""
    caminho = BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.csv"
    if not caminho.exists():
        caminho = criar_csv_simplificado()
    return Response(
        content=caminho.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="modelo_simplificado_chamada.csv"'},
    )


@app.get("/api/exemplo-simplificado-xlsx")
async def baixar_xlsx_simplificado() -> Response:
    """Modelo 2 (Simplificado - Lista de Presença Rápida: Nome e Documento) em Excel (.xlsx)."""
    caminho = BASE_DIR / "assets" / "exemplos" / "modelo_simplificado_chamada.xlsx"
    if not caminho.exists():
        caminho = criar_xlsx_simplificado()
    return Response(
        content=caminho.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="modelo_simplificado_chamada.xlsx"'},
    )
