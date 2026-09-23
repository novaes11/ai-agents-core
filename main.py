import os
import sys
from github import Github, GithubException

def main():
    token = os.environ.get('GITHUB_TOKEN')
    pr_number_str = os.environ.get('PR_NUMBER')
    repo_name = os.environ.get('GITHUB_REPOSITORY')

    if not token or not pr_number_str or not repo_name:
        print("Erro: As variáveis de ambiente GITHUB_TOKEN, PR_NUMBER e GITHUB_REPOSITORY são obrigatórias.")
        sys.exit(1)

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        print(f"Erro: PR_NUMBER '{pr_number_str}' não é um número válido.")
        sys.exit(1)

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
    except GithubException as e:
        print(f"Erro de autenticação ou falha ao acessar o repositório {repo_name}: {e}")
        sys.exit(1)

    try:
        pr = repo.get_pull(pr_number)
        comment_body = "✅ [Infraestrutura] O script base do ai-agents-core conectou com sucesso neste Pull Request. O encanamento está pronto."
        pr.create_issue_comment(comment_body)
        print("Comentário postado com sucesso no PR.")
    except GithubException as e:
        print(f"Erro ao acessar o Pull Request #{pr_number} ou postar o comentário: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
