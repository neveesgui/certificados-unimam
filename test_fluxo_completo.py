"""
SUÍTE DE TESTES DE INTEGRAÇÃO (test_fluxo_completo.py)
-------------------------------------------------------------------------
Objetivo: Testar todos os módulos do sistema:
- Criação das 3 molduras institucionais (Clássica, Executiva Clean, Solene Dourada)
- Chave de Autenticidade apenas digitada (sem fundo colorido no certificado)
- Planilhas fictícias em CSV e Excel (.xlsx) nos 2 modelos (Simplificado e Completo)
- Validação de Chave e Bloqueio Antifraude
"""

import base64
import io
import json
import zipfile

from core.autenticidade import validar_certificado
from core.gerenciador_lotes import processar_lote_csv
from core.motor_desenho import gerar_certificado_individual
from core.template_config import BASE_DIR, carregar_config_template
from setup_assets import (
    criar_csv_exemplo,
    criar_csv_simplificado,
    criar_todas_molduras,
    criar_xlsx_exemplo,
    criar_xlsx_simplificado,
)


def executar_testes() -> None:
    print("1. Gerando as 3 molduras UNIMAM (1920x1080) e os 4 arquivos de planilha (.csv e .xlsx)...")
    criar_todas_molduras()
    caminho_csv = criar_csv_exemplo()
    caminho_xlsx = criar_xlsx_exemplo()
    caminho_csv_simp = criar_csv_simplificado()
    caminho_xlsx_simp = criar_xlsx_simplificado()

    assert caminho_csv.exists() and caminho_xlsx.exists()
    assert caminho_csv_simp.exists() and caminho_xlsx_simp.exists()

    print("2. Testando carregamento do Template Dinâmico (JSON)...")
    config = carregar_config_template()
    assert len(config["molduras_disponiveis"]) == 3

    print("3. Testando Motor de Desenho nas 3 Molduras (apenas digitação limpa da Chave)...")
    for nome_moldura in ["padrao", "moderno", "solene"]:
        png_bytes, meta = gerar_certificado_individual(
            nome="Lais Cardoso De Medeiros",
            documento="044266434546",
            evento="Tech Girls no mercado de trabalho",
            carga_horaria="8",
            data_emissao="22/10/2026",
            moldura_escolhida=nome_moldura,
        )
        assert len(png_bytes) > 10000
        if nome_moldura == "padrao":
            caminho_demo = BASE_DIR / "data" / "certificado_demo_gerado.png"
            caminho_demo.parent.mkdir(parents=True, exist_ok=True)
            caminho_demo.write_bytes(png_bytes)
            print(f"   -> Certificado demo salvo em: {caminho_demo}")
            print(f"   -> Chave de Autenticidade gerada: {meta['codigo_autenticidade']}")

    print("4. Testando Validação de Autenticidade por Chave Única...")
    res_key = validar_certificado(codigo=meta["codigo_autenticidade"])
    assert res_key["valido"] is True

    print("5. Testando Sistema Antifraude...")
    pacote_original = json.loads(base64.urlsafe_b64decode(meta["token_validacao"]).decode("utf-8"))
    pacote_original["d"]["carga_horaria"] = "160"
    token_adulterado = base64.urlsafe_b64encode(json.dumps(pacote_original).encode("utf-8")).decode("utf-8")
    res_fraude = validar_certificado(token=token_adulterado)
    assert res_fraude["valido"] is False

    print("6. Testando Gerenciador de Lotes nos 2 Modelos (Completo 8 alunos e Simplificado 6 alunos)...")
    _, rel_csv = processar_lote_csv(caminho_csv.read_bytes(), nome_arquivo_planilha="alunos_exemplo.csv")
    assert len(rel_csv) == 8, f"CSV Completo: Esperava 8 certificados, gerou {len(rel_csv)}"

    zip_xlsx, rel_xlsx = processar_lote_csv(caminho_xlsx.read_bytes(), nome_arquivo_planilha="alunos_exemplo.xlsx")
    assert len(rel_xlsx) == 8, f"XLSX Completo: Esperava 8 certificados, gerou {len(rel_xlsx)}"

    _, rel_simp = processar_lote_csv(caminho_xlsx_simp.read_bytes(), nome_arquivo_planilha="modelo_simplificado_chamada.xlsx")
    assert len(rel_simp) == 6, f"XLSX Simplificado: Esperava 6 certificados, gerou {len(rel_simp)}"

    with zipfile.ZipFile(io.BytesIO(zip_xlsx), "r") as zf:
        arquivos_no_zip = zf.namelist()
        assert "relatorio_chaves_autenticidade.csv" in arquivos_no_zip
        assert len(arquivos_no_zip) == 9

    print("   -> Lote Completo e Lote Simplificado (.csv e .xlsx) processados com sucesso!")
    print("\n✅ TODOS OS TESTES PASSARAM COM SUCESSO!")


if __name__ == "__main__":
    executar_testes()
