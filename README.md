# AI Agents Core 🤖

Infraestrutura central de orquestração de múltiplos agentes de Inteligência Artificial para atuação direta em esteiras de CI/CD (GitHub Actions). Este repositório atua como uma **Custom Composite Action**, sendo consumido remotamente por outros repositórios.

## 🎯 Arquitetura e Objetivo

O projeto segue o princípio de separação de responsabilidades:
- Toda a lógica de IA (código Python, orquestração e configuração de modelos) fica isolada neste repositório.
- Repositórios alvo ("clientes") consomem a inteligência via GitHub Actions, anulando a necessidade de uso de submódulos no Git.

O núcleo operacional trabalha sob o modelo de **Squad de Agentes**. Repositórios clientes configuram a ativação simultânea de especialistas (como Revisores de Código, Engenheiros de Segurança ou Otimizadores de Banco de Dados) para análise de Pull Requests. O orquestrador executa inferências individuais de cada perfil e publica um comentário estruturado consolidando as correções.

A arquitetura de linguagem e processamento do diff é executada pela API do **Gemini 1.5 Pro**.

---

## 🛠️ O Catálogo de Especialistas (Squad Builder)

A seleção dos agentes que atuarão nos projetos clientes ocorre por meio da ferramenta `squad-builder`. A ferramenta atua com base no repositório de perfis open source [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents), baixando perfis e estruturando o fluxo em novos ambientes sem carregar arquivos desnecessários.

---

## 🚀 Guia de Integração para Novos Projetos (Repositórios Alvo)

Para instanciar o serviço de revisão automatizada em um novo código-fonte, proceda com os passos abaixo diretamente do diretório raiz do **seu projeto cliente**.

### 1. Selecionar e Instalar o Squad

Execute o assistente residente no `ai-agents-core` (garanta que possui Python 3.9+ e substitua o caminho conforme a estrutura do seu ambiente local):

```bash
# Listar os grupos de especialistas disponíveis e o hash de commit:
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py list

# Extrair as definições do agente alvo (exemplo: engineering-code-reviewer):
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py show engineering-code-reviewer

# Instalar os perfis de interesse apontando os respectivos códigos listados
# Exemplo: instalando Code Reviewer (3.09) e Application Security (14.02)
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py install --agents 3.09,14.02 --ref <SHA-DA-LISTAGEM>
```
*O comando irá gerar a pasta local `.squad/` contendo os perfis formatados e o manifesto YAML de execução (`squad-config.yml`).*

### 2. Provisionar o Workflow de CI/CD

Ainda na raiz do repositório cliente, provisione a esteira para o GitHub Actions:

```bash
python /caminho/para/ai-agents-core/skills/squad-builder/scripts/squad.py init
```
*Isso gerará o arquivo `.github/workflows/ai-review.yml`, referenciando diretamente a Composite Action.*

### 3. Autenticar Variáveis

O núcleo de IA exige a autenticação na API do Google AI Studio. Para manter a regra Zero Secrets no código:
1. No repositório alvo no GitHub, navegue em **Settings > Secrets and variables > Actions**.
2. Cadastre o token da plataforma na variável `Repository secret` denominada `GEMINI_API_KEY`.

### 4. Consolidar e Operar

Faça o *commit* da pasta `.squad` e do diretório `.github` no seu repositório alvo. O sistema de IA analisará automaticamente as extensões e sintaxes incluídas em cada novo Pull Request ou modificações subsequentes, postando os feedbacks em threads automatizadas.

---

## 🔒 Diretrizes e Governança

A ação prioriza as seguintes métricas na operação:

- **Zero Acesso Livre ao CLI:** Os agentes operacionais atuam no paradigma estático (análise direta sobre os diffs na memória) e escrita via API Rest do GitHub. A execução de comandos shell de maneira arbitrária via LLM não ocorre.
- **Contenção Estrita de Custos:** A verificação se baseia na restrição sistêmica de loop. Agentes ativados operam limitados a uma iteração isolada, suprimindo o desperdício computacional em diálogos autônomos.
- **Uniformidade Clínica:** Traços de personalidade provenientes do catálogo público sofrem sobreposição (override) dentro do executor em Python. As requisições determinam estritamente comunicações diretas, análises factuais e devolutivas essencialmente técnicas, removendo tom humorístico ou retórica descritiva em formato de venda.
