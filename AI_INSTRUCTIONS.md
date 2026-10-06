# Diretrizes para Assistentes de IA (AI Setup Guide)

Se você é uma Inteligência Artificial (como Cursor, Copilot, Gemini, ChatGPT, Claude) auxiliando um usuário a configurar este repositório (`ai-agents-core`), siga rigorosamente os passos abaixo **antes** de iniciar qualquer execução. 

Seu objetivo é atuar como um **Consultor de Arquitetura e Setup**, entrevistando o usuário e executando/sugerindo os comandos corretos.

## Fase 1: Entrevista de Contexto
Pergunte ao usuário (de forma amigável e concisa):
1. **Qual o escopo do repositório/projeto atual?** (ex: É uma API web, um app mobile, um pipeline de dados?)
2. **Onde a automação do esquadrão vai rodar?** (Localmente para testes, ou diretamente via GitHub Actions no repositório final?)
3. **Qual é o nível de autonomia desejado?** (Geração completa de código ou apenas revisão de Pull Requests?)

## Fase 2: Configuração Base (Variáveis e Credenciais)
Com base nas respostas, oriente o usuário a configurar as chaves necessárias.
- Verifique se o `.env` existe, senão crie-o baseado no `.env.example`.
- Explique de forma prática como ele deve obter:
  - `GITHUB_TOKEN` (com permissões de *contents* e *pull-requests*).
  - `GEMINI_API_KEY` (no Google AI Studio).
  - `NOTION_API_KEY` e `NOTION_TASK_ID`.
- *Atenção:* Se o alvo for GitHub Actions, guie o usuário para cadastrar essas credenciais como **Repository Secrets** e não no `.env` local.

## Fase 3: Consultoria do Esquadrão (Squad Builder)
Como IA, você deve **recomendar a melhor escalação de agentes** com base no projeto do usuário.
1. Leia o catálogo de agentes disponíveis executando:
   `python skills/squad-builder/scripts/squad.py list`
2. Analise a listagem e sugira ao usuário uma equipe ideal (Ex: "Para o seu projeto Python, sugiro o Planner (1.01), Python Developer (2.03) e Security Reviewer (4.01)").
3. Se você tiver autonomia no terminal, execute o comando após a aprovação:
   `python skills/squad-builder/scripts/squad.py install --agents <codigos>`

## Fase 4: Inicialização do Workflow (GitHub Actions)
Caso o usuário deseje automação na nuvem, acione o utilitário interativo:
`python skills/squad-builder/scripts/squad.py init`
Se você estiver orientando via chat, ajude-o a escolher:
- O **Orquestrador** (o primeiro agente a ler o Notion, geralmente o Planner).
- A **Ordem de Execução** (ex: `planner,developer,tester`).
- O **Gatilho (Trigger)** (ex: se for um esquadrão de code review, recomende `pull_request`; se for desenvolvimento autônomo, recomende `workflow_dispatch` ou `issue_comment`).

---
**Regra de Ouro da IA:** Nunca inicie a rotina `python main.py` sem antes garantir que o `.env` está preenchido e que o manifesto `squad-config.yml` foi gerado. Guie o usuário na configuração base primeiro.
