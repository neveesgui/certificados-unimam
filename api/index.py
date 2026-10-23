"""
PONTO DE ENTRADA SERVERLESS PARA A VERCEL (api/index.py)
-------------------------------------------------------------------------
O QUE FAZ: Importa e expõe a instância 'app' do FastAPI.
POR QUE: O runtime '@vercel/python' procura automaticamente uma variável chamada
'app' (ASGI/WSGI) dentro de 'api/index.py' para transformar cada requisição HTTP
em uma execução Serverless.
"""

from app import app

# Exporta explicitamente para o analisador da Vercel
__all__ = ["app"]
