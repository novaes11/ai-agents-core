
## [2026-10-05] Implementação do Agente Revisor com Gemini
- Migração de infraestrutura: Substituição do placeholder por integração real com a API do Gemini.
- action.yml: Adicionada a exigência da variável GEMINI_API_KEY.
- requirements.txt: Incluída a dependência google-generativeai.
- main.py: Implementada a extração de diffs via GitHub API, configuração do modelo Gemini (gemini-1.5-pro, temperatura 0.2) e envio de prompt de revisão. O resultado do modelo é postado como comentário.
