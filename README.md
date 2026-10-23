# 🎓 UNIMAM · Sistema Integrado de Certificados Acadêmicos

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10%2B-008542?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-006837?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Pillow-Imaging-C59B27?style=for-the-badge" alt="Pillow" />
  <img src="https://img.shields.io/badge/Seguran%C3%A7a-SHA--256-1D1D1F?style=for-the-badge" alt="SHA-256" />
  <img src="https://img.shields.io/badge/Deploy-Vercel_Serverless-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel" />
</p>

Plataforma web de emissão em lote e validação criptográfica de certificados acadêmicos, desenhada com a identidade institucional do **Centro Universitário Maria Milza (UNIMAM)** e experiência de uso inspirada em interfaces translúcidas modernas (**Apple UI/UX**).

> **Autoria:** Projeto arquitetado e desenvolvido por [**Guilherme Neves (@neveesgui)**](https://github.com/neveesgui).

---

## ✨ Principais Funcionalidades

* **4 Modos Operacionais Intuitivos (`Individual · Turma · Eventos · Validar`):**
  1. **Individual:** Emissão instantânea para 1 aluno com prévia ao vivo no navegador e cópia rápida da Chave de Autenticidade.
  2. **Turma (1 Único Evento):** A coordenação/professora preenche o nome da palestra, carga horária e data na tela e sobe apenas a lista de chamada simples (`nome` e `documento`), baixando um pacote `.ZIP` com todos os certificados.
  3. **Eventos (Múltiplos Eventos e Molduras na mesma Planilha):** Ideal para Semanas Acadêmicas e Congressos. Cada linha da planilha define o aluno, seu respectivo evento, carga horária, data e até a **moldura específica** (`classica`, `executiva` ou `solene`).
  4. **Validar:** Portal público para conferência imediata da **Chave de Autenticidade (`CERT-XXXXXXXXXXXX`)**.
* **Motor Gráfico Inteligente (`Pillow`):**
  * Enquadramento automático em pixels (`textlength` + `multiline_text`): títulos longos quebram linha automaticamente e nomes extensos ajustam a tipografia para nunca vazarem da moldura.
  * Normalização automática de temas enviados (`PNG`, `JPG`, `WEBP`) para `1920×1080 px` (Full HD) sem distorcer proporções.
* **3 Molduras Institucionais Nativas + Upload Customizado:**
  * **1. Clássica UNIMAM:** Moldura tradicional em verde-escuro institucional e dourado sobre fundo marfim.
  * **2. Executiva Clean:** Design minimalista sobre fundo branco puro com faixas laterais no verde UNIMAM.
  * **3. Solene Dourada:** Borda tripla diplomática para simpósios, congressos e honrarias.
  * **+ Sua Moldura:** Suporte para envio de qualquer arte própria do evento.
* **Leitura Nativa de Excel (`.xlsx`) e CSV (`.csv` / `.tsv`):**
  * Suporta arquivos exportados tanto do **Microsoft Excel** (separados por `;` ou nativos `.xlsx`) quanto do **Google Planilhas / Forms** (separados por `,`).

---

## 📊 Estrutura das Planilhas Aceitas

O sistema oferece exemplos prontos para download diretamente nas abas **Turma** e **Eventos**:

### 1. Aba `Turma` (Lista de Chamada Simples — Mesmo Evento)
| `nome` | `documento` *(opcional)* |
| :--- | :--- |
| Lais Cardoso de Medeiros | 20261045 |
| Ana Beatriz Oliveira | 20261089 |

### 2. Aba `Eventos` (Múltiplos Eventos e Molduras)
| `nome` | `documento` | `evento` | `carga_horaria` | `data` | `moldura` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Lais Cardoso de Medeiros | 20261045 | Tech Girls no Mercado de Trabalho | 8 | 22/10/2026 | `classica` |
| Ana Beatriz Oliveira | 20261089 | Semana Acadêmica de Eng. de Software | 20 | 22/10/2026 | `executiva` |
| Fernanda Costa Lima | 20261150 | Simpósio de Inovação UNIMAM | 16 | 22/10/2026 | `solene` |

---

## 🏗️ Arquitetura de Pastas

```text
gerador-certificados/
├── api/
│   └── index.py                     # Ponto de entrada Serverless (Vercel ASGI)
├── assets/
│   ├── exemplos/                    # Planilhas exemplo editáveis (.xlsx e .csv)
│   └── templates/
│       ├── config_padrao.json       # Coordenadas X/Y, fontes e cores desacopladas do código
│       ├── fundo_padrao.png         # Moldura 1: Clássica UNIMAM (1920x1080)
│       ├── fundo_moderno.png        # Moldura 2: Executiva Clean (1920x1080)
│       └── fundo_solene.png         # Moldura 3: Solene Dourada (1920x1080)
├── core/
│   ├── autenticidade.py             # Assinatura SHA-256 + HMAC antifraude
│   ├── motor_desenho.py             # Motor Pillow com quebra de linha automática em pixels
│   ├── gerenciador_lotes.py         # Processador de lotes CSV/XLSX em memória (io.BytesIO)
│   └── template_config.py           # Leitor e validador do JSON de coordenadas
├── static/
│   ├── logo_unimam.png              # Logo institucional em alta definição
│   └── styles.css                   # Design System responsivo (Desktop, Tablet e Mobile)
├── templates_html/
│   ├── index.html                   # Painel principal (Individual, Turma, Eventos, Validar)
│   └── validar.html                 # Página pública de verificação de autenticidade
├── app.py                           # Aplicação web FastAPI
├── setup_assets.py                  # Gerador das molduras e planilhas de exemplo
├── test_fluxo_completo.py           # Suíte de testes de integração
├── requirements.txt                 # Dependências do projeto
└── vercel.json                      # Configuração de rotas para deploy na Vercel
```

---

## 🚀 Como Executar Localmente

1. **Clone o repositório e acesse a pasta:**
   ```bash
   git clone https://github.com/neveesgui/gerador-certificados-unimam.git
   cd gerador-certificados-unimam
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute a suíte de testes (opcional — valida todos os módulos):**
   ```bash
   python test_fluxo_completo.py
   ```

5. **Inicie o servidor web:**
   ```bash
   uvicorn app:app --reload --port 8000
   ```
   Acesse **`http://localhost:8000`** no seu navegador.

---

## ☁️ Como Fazer o Deploy na Vercel

O projeto já está 100% configurado para execução **Serverless** na Vercel (processamento em memória RAM via `io.BytesIO`, sem escrita bloqueante em disco):

1. Suba o projeto para um repositório no seu **GitHub**.
2. Acesse [vercel.com](https://vercel.com) → **Add New Project** → selecione o repositório.
3. Em **Environment Variables**, adicione a chave secreta usada na assinatura dos certificados:
   * **Name:** `CERT_SECRET_KEY`
   * **Value:** *(defina uma frase secreta forte exclusiva da instituição)*
4. Clique em **Deploy**!

---

## 👨‍💻 Autor

Desenvolvido por **Guilherme Neves**  
🔗 GitHub: [@neveesgui](https://github.com/neveesgui)
