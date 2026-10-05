#!/usr/bin/env python3
"""Cataloga, inspeciona e instala perfis de agentes de msitarzewski/agency-agents.

Somente biblioteca padrao. Acessa apenas api.github.com e
raw.githubusercontent.com para um unico repositorio fixo, sempre em um commit
resolvido para SHA. Nao executa nenhum conteudo baixado.

Comandos:
  list     lista divisoes e agentes com codigos (ex.: 2.14)
  show     exibe nome e descricao de um agente
  install  baixa os agentes escolhidos e grava o manifesto squad-config.yml
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "msitarzewski/agency-agents"
API = f"https://api.github.com/repos/{REPO}"
RAW = f"https://raw.githubusercontent.com/{REPO}"
DEFAULT_REF = "main"
DEFAULT_DEST = ".squad"
MAX_AGENT_BYTES = 200_000
EXCLUDED_DIRS = {
    "scripts", "strategy", "docs", "examples", "integrations",
    "assets", "tests", "test", "node_modules",
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class SquadError(Exception):
    pass


def _get(url, accept=None, limit=None):
    headers = {"User-Agent": "ai-agents-core-squad-builder"}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(limit + 1) if limit else response.read()
    except urllib.error.HTTPError as exc:
        raise SquadError(f"HTTP {exc.code} ao acessar {url}") from exc
    except urllib.error.URLError as exc:
        raise SquadError(f"Falha de rede ao acessar {url}: {exc.reason}") from exc
    if limit and len(data) > limit:
        raise SquadError(f"Resposta maior que {limit} bytes: {url}")
    return data


def resolve_ref(ref):
    if SHA_RE.match(ref):
        return ref
    url = f"{API}/commits/{urllib.parse.quote(ref, safe='')}"
    sha = _get(url, accept="application/vnd.github.sha").decode("ascii").strip()
    if not SHA_RE.match(sha):
        raise SquadError(f"Referencia '{ref}' nao resolveu para um SHA valido.")
    return sha


def build_catalog(sha):
    """Retorna [(indice, divisao, [(codigo, slug, caminho), ...]), ...]."""
    tree = json.loads(_get(f"{API}/git/trees/{sha}?recursive=1"))
    if tree.get("truncated"):
        raise SquadError("A arvore do repositorio veio truncada pela API do GitHub.")
    divisions = {}
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) != 2 or not parts[1].endswith(".md"):
            continue
        division, filename = parts
        slug = filename[:-3]
        if division.startswith(".") or division in EXCLUDED_DIRS:
            continue
        if not SLUG_RE.match(division) or not SLUG_RE.match(slug):
            continue
        divisions.setdefault(division, []).append((slug, item["path"]))
    catalog = []
    for d_index, division in enumerate(sorted(divisions), start=1):
        agents = [
            (f"{d_index}.{a_index:02d}", slug, path)
            for a_index, (slug, path) in enumerate(sorted(divisions[division]), start=1)
        ]
        catalog.append((d_index, division, agents))
    return catalog


def select_agents(catalog, tokens):
    by_key = {}
    for _, _, agents in catalog:
        for code, slug, path in agents:
            by_key[code] = (code, slug, path)
            by_key[slug] = (code, slug, path)
    selected, unknown = [], []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token in by_key:
            if by_key[token] not in selected:
                selected.append(by_key[token])
        else:
            unknown.append(token)
    if unknown:
        raise SquadError("Codigos ou nomes desconhecidos: " + ", ".join(unknown))
    if not selected:
        raise SquadError("Nenhum agente selecionado.")
    return selected


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return {}


def fetch_agent(sha, path):
    raw = _get(f"{RAW}/{sha}/{urllib.parse.quote(path)}", limit=MAX_AGENT_BYTES)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SquadError(f"{path} nao esta em UTF-8.") from exc
    meta = parse_frontmatter(text)
    if not meta.get("name"):
        raise SquadError(f"{path} nao tem frontmatter com o campo 'name'.")
    return raw, meta


def cmd_list(args):
    sha = resolve_ref(args.ref)
    catalog = build_catalog(sha)
    if args.json:
        print(json.dumps(
            {"repository": REPO, "commit": sha, "divisions": [
                {"code": d, "name": name,
                 "agents": [{"code": c, "slug": s, "path": p} for c, s, p in agents]}
                for d, name, agents in catalog]},
            ensure_ascii=False, indent=2))
        return
    total = sum(len(agents) for _, _, agents in catalog)
    print(f"Repositorio: {REPO}")
    print(f"Commit: {sha}")
    print(f"Divisoes: {len(catalog)} | Agentes: {total}")
    for d_index, division, agents in catalog:
        print(f"\n[{d_index}] {division} ({len(agents)})")
        for code, slug, _ in agents:
            print(f"  {code:>6}  {slug}")
    print(f"\nPara fixar esta listagem use: --ref {sha}")


def cmd_show(args):
    sha = resolve_ref(args.ref)
    code, slug, path = select_agents(build_catalog(sha), [args.agent])[0]
    _, meta = fetch_agent(sha, path)
    print(f"Codigo: {code}")
    print(f"Arquivo: {path}")
    print(f"Nome: {meta.get('name', '')}")
    print(f"Descricao: {meta.get('description', '')}")


def _resolve_dest(dest):
    root = Path.cwd().resolve()
    target = (root / dest).resolve()
    if target == root or root not in target.parents:
        raise SquadError("--dest deve ser um subdiretorio do diretorio atual.")
    return target


def cmd_install(args):
    sha = resolve_ref(args.ref)
    catalog = build_catalog(sha)
    selected = select_agents(catalog, args.agents.split(","))
    division_of = {path: division for _, division, agents in catalog for _, _, path in agents}
    dest = _resolve_dest(args.dest)

    downloaded = []
    for code, slug, path in selected:
        raw, meta = fetch_agent(sha, path)
        downloaded.append((code, slug, path, raw, meta))

    agents_dir = dest / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    manifest = [
        "# Gerado por skills/squad-builder/scripts/squad.py. Revise antes de commitar.",
        "source:",
        f"  repository: {REPO}",
        f"  commit: {sha}",
        "limits:",
        "  max_iterations_per_agent: 1",
        "agents:",
    ]
    for code, slug, path, raw, meta in downloaded:
        (agents_dir / f"{slug}.md").write_bytes(raw)
        manifest += [
            f"  - slug: {slug}",
            f"    code: \"{code}\"",
            f"    division: {division_of[path]}",
            f"    file: agents/{slug}.md",
            f"    sha256: {hashlib.sha256(raw).hexdigest()}",
        ]
        print(f"Instalado {code} {slug} ({meta['name']})")
    (dest / "squad-config.yml").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"\nManifesto: {dest / 'squad-config.yml'}")
    print(f"Agentes: {len(downloaded)} | Commit de origem: {sha}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="lista divisoes e agentes com codigos")
    p_list.add_argument("--ref", default=DEFAULT_REF, help="branch, tag ou SHA (padrao: main)")
    p_list.add_argument("--json", action="store_true", help="saida em JSON")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="exibe nome e descricao de um agente")
    p_show.add_argument("agent", help="codigo (ex.: 2.14) ou slug")
    p_show.add_argument("--ref", default=DEFAULT_REF)
    p_show.set_defaults(func=cmd_show)

    p_install = sub.add_parser("install", help="instala os agentes escolhidos")
    p_install.add_argument("--agents", required=True, help="codigos ou slugs separados por virgula")
    p_install.add_argument("--ref", default=DEFAULT_REF, help="use o SHA exibido por 'list'")
    p_install.add_argument("--dest", default=DEFAULT_DEST, help=f"padrao: {DEFAULT_DEST}")
    p_install.set_defaults(func=cmd_install)

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        args.func(args)
    except SquadError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
