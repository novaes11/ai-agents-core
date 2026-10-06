import os
import sys
import yaml
import google.generativeai as genai
from github import Github, GithubException

def read_file_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Erro ao ler arquivo {path}: {e}")
        return None

def main():
    token = os.environ.get('GITHUB_TOKEN')
    pr_number_str = os.environ.get('PR_NUMBER')
    repo_name = os.environ.get('GITHUB_REPOSITORY')
    gemini_key = os.environ.get('GEMINI_API_KEY')

    if not token or not pr_number_str or not repo_name or not gemini_key:
        print("Erro: As variáveis GITHUB_TOKEN, PR_NUMBER, GITHUB_REPOSITORY e GEMINI_API_KEY são obrigatórias.")
        sys.exit(1)

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        print(f"Erro: PR_NUMBER '{pr_number_str}' não é um número válido.")
        sys.exit(1)

    # Configuração do Gemini
    genai.configure(api_key=gemini_key)
    generation_config = genai.types.GenerationConfig(temperature=0.2)
    model = genai.GenerativeModel('gemini-1.5-pro', generation_config=generation_config)

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
    except GithubException as e:
        print(f"Erro de autenticação ou falha ao acessar o repositório {repo_name}: {e}")
        sys.exit(1)

    try:
        pr = repo.get_pull(pr_number)
        
        # Obter os arquivos alterados e montar o diff
        files = pr.get_files()
        diff_text = ""
        for f in files:
            diff_text += f"Arquivo: {f.filename}\nPatch:\n{f.patch}\n\n"
            
        if not diff_text.strip():
            print("Nenhuma alteração de código detectada neste PR.")
            sys.exit(0)

        # Logica de Squad (Phase 2)
        workspace = os.getcwd()
        squad_config_path = os.path.join(workspace, '.squad', 'squad-config.yml')
        agents_to_run = []
        
        if os.path.exists(squad_config_path):
            print("Configuração de Squad detectada. Carregando agentes...")
            with open(squad_config_path, 'r', encoding='utf-8') as f:
                squad_config = yaml.safe_load(f)
            
            for agent_info in squad_config.get('agents', []):
                agent_file_path = os.path.join(workspace, '.squad', agent_info['file'])
                agent_profile = read_file_safe(agent_file_path)
                if agent_profile:
                    # Enforcar a diretriz técnica e remover o estilo de formatação do perfil
                    system_prompt = (
                        f"{agent_profile}\n\n"
                        "DIRETRIZ DE EXECUÇÃO ESTRITA:\n"
                        "Atue conforme o perfil acima, mas limite-se a uma linguagem puramente técnica, direta e factual. "
                        "Não use adjetivos de vendas, não adicione personalidade, humor ou emojis. Seja clínico. "
                        "Analise as alterações de código fornecidas e identifique falhas lógicas, de segurança ou boas práticas. "
                        "Se não houver problemas no seu escopo de análise, responda de forma breve."
                    )
                    agents_to_run.append({
                        'name': agent_info.get('slug', 'Agente'),
                        'prompt': system_prompt
                    })
                else:
                    print(f"Aviso: Perfil não encontrado para o agente {agent_info.get('slug')}.")
        
        if not agents_to_run:
            print("Nenhum squad configurado ou arquivos ausentes. Utilizando agente revisor padrão (Fallback).")
            prompt = f"""Atue como um Agente Revisor de Código Sênior. 
Analise as alterações de código abaixo e identifique erros lógicos, falhas de segurança ou violações de boas práticas. 
Mantenha a resposta técnica, direta e estruturada. Caso não encontre erros, aprove a alteração.

Diff do Pull Request:
{diff_text}
"""
            agents_to_run.append({
                'name': 'Agente Revisor Padrão',
                'prompt': prompt
            })

        feedbacks = []
        for agent in agents_to_run:
            print(f"Executando inferência para: {agent['name']}")
            full_prompt = f"{agent['prompt']}\n\n--- INÍCIO DO DIFF ---\n{diff_text}\n--- FIM DO DIFF ---"
            
            response = model.generate_content(full_prompt)
            feedbacks.append(f"### 🤖 Feedback: {agent['name']}\n\n{response.text}\n")
        
        comment_body = f"## Revisão Automatizada (AI Squad)\n\n" + "\n---\n".join(feedbacks)
        
        pr.create_issue_comment(comment_body)
        print("Revisão executada e comentário postado com sucesso no PR.")
        
    except Exception as e:
        print(f"Erro na execução da revisão via Gemini ou falha na API do GitHub: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
