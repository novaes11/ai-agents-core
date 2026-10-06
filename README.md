# AI Agents Core 🤖

Infraestrutura de orquestração autônoma de múltiplos agentes de Inteligência Artificial estruturada via **Grafos Acíclicos Direcionados (DAG)**. Em vez de atuar como um mero revisor de código em *Pull Requests*, este projeto converte o fluxo numa **Fábrica de Desenvolvimento Autônoma**, processando tarefas, gerando arquitetura, escrevendo o código final, garantindo a segurança estática e entregando o pacote com testes em um novo Pull Request.

## 🎯 Arquitetura do Pipeline

O fluxo descarta o formato de "Chat Livre" em favor de rotinas de entrada e saída (I/O) validadas e encadeadas. A saída determinística de um agente torna-se o *input* exato do LLM seguinte:

1. **Ingestão de Requisitos:** Conexão nativa com o Notion API. O sistema extrai blocos de texto, descrição e critérios de aceite da tarefa demandada.
2. **Planner (Project Manager):** Recebe o contexto completo da especificação e lê a atual árvore de diretórios do repositório. Retorna o plano arquitetural de implementação limitando os arquivos impactados.
3. **Developer:** Com base no planejamento restrito, projeta todo o código fonte e as modificações nos arquivos apontados.
4. **Security:** Analisa estritamente a saída do *Developer* visando vulnerabilidades conhecidas (padrões OWASP). Se falhas críticas não puderem ser corrigidas em sua camada, bloqueia a esteira.
5. **Tester:** Analisa a entrega funcional aprovada pelo time de segurança e desenvolve a bateria de testes unitários (PyTest/Unittest).
6. **Entrega (PyGithub):** Uma nova *branch* secundária é aberta remotamente, contendo as alterações. O sistema cria os arquivos e submete um detalhado Pull Request assinado pelo Esquadrão.

Motor Lógico: **Gemini 1.5 Pro** via `google-generativeai`.

---

## 👥 O Catálogo de Especialistas (Squad Builder)

A seleção dos agentes que atuarão nos projetos clientes ocorre por meio da ferramenta `squad-builder`. A ferramenta baixa perfis do repositório open source [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) e gera a configuração local necessária.

Para provisionar o Esquadrão em um novo projeto cliente, execute o script base no diretório alvo:

```bash
# Listar os grupos de especialistas disponíveis:
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py list

# Extrair as definições do agente alvo (exemplo: engineering-code-reviewer):
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py show engineering-code-reviewer

# Instalar os perfis de interesse apontando os códigos listados:
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py install --agents 3.09,14.02 --ref <SHA-DA-LISTAGEM>

# Provisionar a esteira para o GitHub Actions automaticamente:
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py init
```

---

## 🛠️ Guia de Configuração e Uso

O orquestrador pode ser executado tanto localmente quanto hospedado em Actions na nuvem. Em ambos os cenários, ele depende de chaves de autorização de integração lidas como **Variáveis de Ambiente**.

### 1. Preparação das Variáveis (`.env`)

Fornecemos na raiz do projeto o arquivo `.env.example`. Você deve replicar ou preencher essas credenciais no ambiente onde rodar o script.

```env
# Token do GitHub com permissões de 'contents: write' e 'pull-requests: write'
GITHUB_TOKEN=ghp_chave_aqui

# Chave do Google AI Studio (modelo de linguagem)
GEMINI_API_KEY=AIzaSy_chave_aqui

# Token de Integração do Notion
NOTION_API_KEY=secret_chave_aqui

# ID de 32 caracteres da página/tarefa no Notion
NOTION_TASK_ID=identificador_da_pagina

# O caminho relativo ao dono do repositório de trabalho
GITHUB_REPOSITORY=org/projeto
```

### 2. Uso Local (Debug e Testes Isolados)

No seu terminal local, execute os comandos:

```bash
# 1. Configurar isolamento virtual
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 2. Instalar motor do orquestrador
pip install -r requirements.txt

# 3. Exportar suas variáveis contidas no .env (utilize o utilitário do seu shell ou declare no terminal)
export GITHUB_TOKEN="sua_chave"
export GEMINI_API_KEY="sua_chave"
export NOTION_API_KEY="sua_chave"
export NOTION_TASK_ID="seu_id"
export GITHUB_REPOSITORY="seu_usuario/seu_repositorio"

# 4. Iniciar rotina do Squad
python main.py
```

### 3. Integração Contínua (GitHub Actions)

Para instanciar essa força de trabalho automatizada direto no portal GitHub de um outro projeto cliente (operando na nuvem):

1. Acesse o **Projeto Cliente > Settings > Secrets and variables > Actions**.
2. Armazene o `GITHUB_TOKEN`, `GEMINI_API_KEY` e `NOTION_API_KEY` como `Repository Secrets`.
3. Adicione o seguinte Workflow no diretório `.github/workflows/ai-squad.yml` do projeto cliente:

```yaml
name: 'AI Squad Builder'
on: 
  workflow_dispatch:
    inputs:
      notion_task_id:
        description: 'Cole o ID da Tarefa do Notion'
        required: true

jobs:
  run-squad:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Chamando Squad via Action
        uses: seu_usuario/ai-agents-core@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
          notion_api_key: ${{ secrets.NOTION_API_KEY }}
          notion_task_id: ${{ github.event.inputs.notion_task_id }}
```

Desta forma, os desenvolvedores de negócio não manipulam código em máquina física, precisando apenas acionar o gatilho "Run workflow" e informar o ID da tarefa originada no Notion. O Esquadrão publicará o Pull Request contendo a resolução.

---

## 🔒 Diretrizes e Governança

- **Redução Sistemática de Alucinação:** A extração do *response_schema* baseada nos objetos tipados em `pydantic` impossibilita descritivos extensos que desviem o encadeamento operacional para fora da instrução lógica.
- **Validação Cruzada de Segurança:** Implantações e blocos de código oriundos do Developer não progridem de estágio caso a detecção no *prompt* de Security levante bloqueios críticos ou reescreva o objeto com violações.
