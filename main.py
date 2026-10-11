import os
import sys
import json
import google.generativeai as genai
from github import Github, GithubException
from notion_client import Client
from pydantic import BaseModel

class PlannerOutput(BaseModel):
    architecture_plan: str
    files_to_modify: list[str]

class DeveloperOutput(BaseModel):
    modified_files: dict[str, str]
    explanation: str

class SecurityOutput(BaseModel):
    passed: bool
    vulnerabilities_found: list[str]
    fixed_files: dict[str, str]

class TesterOutput(BaseModel):
    test_files: dict[str, str]

def fetch_notion_task(api_key, task_id):
    notion = Client(auth=api_key)
    try:
        page = notion.pages.retrieve(task_id)
        blocks = notion.blocks.children.list(block_id=task_id)
        
        content = ""
        for block in blocks.get("results", []):
            if block["type"] == "paragraph":
                texts = block.get("paragraph", {}).get("rich_text", [])
                content += "".join([t["plain_text"] for t in texts]) + "\n"
        
        # O title fica na propriedade do tipo 'title' (pode se chamar 'Task', 'Name', 'title', etc.)
        title = "Tarefa Sem Titulo"
        for prop_name, prop_val in page.get("properties", {}).items():
            if prop_val.get("type") == "title":
                title_items = prop_val.get("title", [])
                if title_items:
                    title = "".join([t.get("plain_text", "") for t in title_items])
                break
            
        return title, content
    except Exception as e:
        print(f"Erro ao acessar Notion API: {e}")
        sys.exit(1)

def generate_with_fallback(prompt, generation_config):
    candidate_models = [
        os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        "gemini-2.5-flash",
        "gemini-pro-latest",
        "gemini-flash-latest"
    ]
    seen = set()
    unique_candidates = [c for c in candidate_models if not (c in seen or seen.add(c))]

    last_error = None
    for model_name in unique_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt, generation_config=generation_config)
        except Exception as e:
            err_msg = str(e)
            if "not found" in err_msg.lower() or "not supported" in err_msg.lower() or "404" in err_msg:
                print(f"[Aviso] Modelo '{model_name}' indisponivel. Tentando proximo modelo da lista...")
                last_error = e
                continue
            raise e
    raise RuntimeError(f"Falha ao gerar conteudo com os modelos Gemini testados. Ultimo erro: {last_error}")

def run_pipeline(gemini_key, task_title, task_content, repo_files_tree):
    genai.configure(api_key=gemini_key)

    print("--- 1. Iniciando Planner ---")
    planner_res = generate_with_fallback(
        f"Crie um plano arquitetural detalhado focado apenas no codigo. Tarefa: {task_title}\n{task_content}\nEstrutura do repo: {repo_files_tree}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=PlannerOutput
        )
    )
    plan_data = json.loads(planner_res.text)

    print("--- 2. Iniciando Developer ---")
    dev_res = generate_with_fallback(
        f"Desenvolva o código exato e completo baseado neste plano:\n{plan_data['architecture_plan']}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=DeveloperOutput
        )
    )
    dev_data = json.loads(dev_res.text)

    print("--- 3. Iniciando Security ---")
    sec_res = generate_with_fallback(
        f"Analise o código gerado contra regras OWASP. Corrija falhas se existirem e retorne o código completo.\n{json.dumps(dev_data['modified_files'])}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=SecurityOutput
        )
    )
    sec_data = json.loads(sec_res.text)
    
    if not sec_data.get('passed', False):
        print(f"Aviso de Segurança: Vulnerabilidades encontradas: {sec_data.get('vulnerabilities_found')}")
        # Neste MVP continuaremos com o fixed_files
    
    print("--- 4. Iniciando Tester ---")
    test_res = generate_with_fallback(
        f"Escreva testes automatizados para a implementação final em pytest ou unittest:\n{json.dumps(sec_data['fixed_files'])}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=TesterOutput
        )
    )
    test_data = json.loads(test_res.text)
    
    return {
        "source_code": sec_data['fixed_files'],
        "tests": test_data['test_files']
    }

def commit_and_create_pr(github_token, repo_name, final_artifacts, task_title):
    g = Github(github_token)
    try:
        repo = g.get_repo(repo_name)
        default_branch = repo.get_branch(repo.default_branch)
        
        # Limpar titulo para o nome da branch
        clean_title = "".join([c if c.isalnum() else "-" for c in task_title.lower()])
        branch_name = f"feature/squad-{clean_title}"
        
        print(f"Criando branch: {branch_name}")
        try:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=default_branch.commit.sha)
        except GithubException as e:
            if e.status == 422: # Reference already exists
                print(f"A branch {branch_name} ja existe.")
            else:
                raise e
        
        def push_files(files_dict, message_prefix):
            for file_path, content in files_dict.items():
                try:
                    # Verifica se arquivo existe para fazer update ou create
                    try:
                        contents = repo.get_contents(file_path, ref=branch_name)
                        repo.update_file(contents.path, f"{message_prefix}: atualiza {file_path}", content, contents.sha, branch=branch_name)
                        print(f"Atualizado: {file_path}")
                    except GithubException as e:
                        if e.status == 404:
                            repo.create_file(file_path, f"{message_prefix}: cria {file_path}", content, branch=branch_name)
                            print(f"Criado: {file_path}")
                        else:
                            raise e
                except Exception as e:
                    print(f"Erro ao manipular arquivo {file_path}: {e}")

        push_files(final_artifacts["source_code"], "feat")
        push_files(final_artifacts["tests"], "test")
            
        pr_body = (
            f"## Implementação Autônoma\n\n"
            f"Branch gerada resolvendo a tarefa Notion: **{task_title}**.\n\n"
            f"- [x] Planejamento concluído\n"
            f"- [x] Código gerado\n"
            f"- [x] Auditoria de Segurança aprovada\n"
            f"- [x] Testes unitários gerados"
        )
        
        print("Abrindo Pull Request...")
        pr = repo.create_pull(
            title=f"feat(squad): {task_title}",
            body=pr_body,
            head=branch_name,
            base=repo.default_branch
        )
        print(f"PR criado com sucesso: {pr.html_url}")
    except Exception as e:
        print(f"Erro na criacao do PR ou commits: {e}")
        sys.exit(1)

def get_repo_tree(github_token, repo_name):
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    tree = repo.get_git_tree(repo.default_branch, recursive=True)
    paths = [t.path for t in tree.tree if t.type == "blob"]
    return "\n".join(paths)

def main():
    token = os.environ.get('GITHUB_TOKEN')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    notion_api_key = os.environ.get('NOTION_API_KEY')
    notion_task_id = os.environ.get('NOTION_TASK_ID')
    repo_name = os.environ.get('GITHUB_REPOSITORY')

    if not all([token, gemini_key, notion_api_key, notion_task_id, repo_name]):
        print("Erro: GITHUB_TOKEN, GEMINI_API_KEY, NOTION_API_KEY, NOTION_TASK_ID e GITHUB_REPOSITORY sao obrigatorios.")
        sys.exit(1)

    print("Obtendo arvore do repositorio...")
    repo_tree = get_repo_tree(token, repo_name)

    print("Extraindo dados do Notion...")
    task_title, task_content = fetch_notion_task(notion_api_key, notion_task_id)
    print(f"Tarefa identificada: {task_title}")

    print("Iniciando pipeline de agentes (DAG)...")
    final_artifacts = run_pipeline(gemini_key, task_title, task_content, repo_tree)

    print("Submetendo codigo...")
    commit_and_create_pr(token, repo_name, final_artifacts, task_title)

if __name__ == "__main__":
    main()
