import os
import sys
import google.generativeai as genai
from github import Github, GithubException

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

        # Instrução para o Agente Revisor
        prompt = f"""Atue como um Agente Revisor de Código Sênior. 
Analise as alterações de código abaixo e identifique erros lógicos, falhas de segurança ou violações de boas práticas. 
Mantenha a resposta técnica, direta e estruturada. Caso não encontre erros, aprove a alteração.

Diff do Pull Request:
{diff_text}
"""
        # Geração do feedback via Gemini
        response = model.generate_content(prompt)
        feedback = response.text
        
        # Adicionar o aviso de IA no topo
        comment_body = f"🤖 **Revisão Automatizada (AI Agent)**\n\n{feedback}"
        
        pr.create_issue_comment(comment_body)
        print("Revisão executada e comentário postado com sucesso no PR.")
        
    except Exception as e:
        print(f"Erro na execução da revisão via Gemini ou falha na API do GitHub: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
