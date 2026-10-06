import re
from urllib.parse import urlparse

import httpx


GITHUB_API = "https://api.github.com"
MAX_README_CHARS = 12000
MAX_CODE_FILES = 12
MAX_FILE_CHARS = 6000

SOURCE_EXTENSIONS = {
    ".py", ".sql", ".r", ".m", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".ipynb",
}

IMPORTANT_FILENAMES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
    "readme.md",
    "app.py",
    "main.py",
}


def _repo_full_name(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("GitHub repository URL is required.")

    if not raw.startswith(("http://", "https://")):
        raw = "https://github.com/" + raw.lstrip("/")

    parsed = urlparse(raw)
    if parsed.netloc.lower() != "github.com":
        raise ValueError("Only github.com repository URLs are supported.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("Enter a GitHub repository URL such as https://github.com/owner/repository.")

    owner, name = parts[0], parts[1]
    name = name.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError("Invalid GitHub repository URL.")
    return f"{owner}/{name}"


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "CVForge/1.0",
    }


def _get(client: httpx.Client, path: str):
    response = client.get(f"{GITHUB_API}{path}", headers=_headers())
    if response.status_code == 404:
        raise ValueError("GitHub repository was not found or is not public.")
    if response.status_code == 403:
        raise ValueError("GitHub public API rate limit reached. Try again later.")
    response.raise_for_status()
    return response.json()


def _technology_hints(files: list[str], languages: dict[str, int], readme: str) -> list[str]:
    values = set(languages.keys())

    mapping = {
        "requirements.txt": ["Python", "pip"],
        "pyproject.toml": ["Python"],
        "package.json": ["JavaScript", "Node.js"],
        "dockerfile": ["Docker"],
        "docker-compose.yml": ["Docker Compose"],
        "docker-compose.yaml": ["Docker Compose"],
        ".ipynb": ["Jupyter"],
        "streamlit": ["Streamlit"],
        "fastapi": ["FastAPI"],
        "flask": ["Flask"],
        "langchain": ["LangChain"],
        "pyspark": ["PySpark"],
        "spark": ["Apache Spark"],
        "xgboost": ["XGBoost"],
        "lightgbm": ["LightGBM"],
        "pytorch": ["PyTorch"],
        "tensorflow": ["TensorFlow"],
        "postgres": ["PostgreSQL"],
        "mysql": ["MySQL"],
    }

    haystack = " ".join(files + [readme]).lower()
    for needle, hints in mapping.items():
        if needle in haystack:
            values.update(hints)

    return sorted(values)


def inspect_public_repository(url: str) -> dict:
    full_name = _repo_full_name(url)

    with httpx.Client(timeout=12.0, follow_redirects=True) as client:
        repo = _get(client, f"/repos/{full_name}")

        if repo.get("private") or repo.get("visibility") != "public":
            raise ValueError("This repository is not public. CVForge only inspects public repositories.")

        owner = repo["owner"]["login"]
        name = repo["name"]
        default_branch = repo.get("default_branch") or "main"

        languages = _get(client, f"/repos/{owner}/{name}/languages")
        topics_payload = _get(client, f"/repos/{owner}/{name}/topics")
        topics = topics_payload.get("names", [])

        readme = ""
        try:
            readme_payload = _get(client, f"/repos/{owner}/{name}/readme")
            import base64
            encoded = readme_payload.get("content", "")
            readme = base64.b64decode(encoded).decode("utf-8", errors="ignore")
            readme = readme[:MAX_README_CHARS]
        except Exception:
            readme = ""

        tree = _get(
            client,
            f"/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1",
        )
        tree_items = tree.get("tree", [])

        files = [
            item["path"]
            for item in tree_items
            if item.get("type") == "blob"
        ]

        important = [
            path
            for path in files
            if path.lower().split("/")[-1] in IMPORTANT_FILENAMES
        ]

        source_files = [
            path
            for path in files
            if any(path.lower().endswith(ext) for ext in SOURCE_EXTENSIONS)
        ]

        selected = []
        for path in important + source_files:
            if path not in selected:
                selected.append(path)
            if len(selected) >= MAX_CODE_FILES:
                break

        samples = []
        for path in selected:
            try:
                payload = _get(
                    client,
                    f"/repos/{owner}/{name}/contents/{path}?ref={default_branch}",
                )
                if payload.get("encoding") != "base64":
                    continue
                import base64
                raw = base64.b64decode(payload.get("content", "")).decode(
                    "utf-8",
                    errors="ignore",
                )
                samples.append(
                    {
                        "path": path,
                        "content": raw[:MAX_FILE_CHARS],
                    }
                )
            except Exception:
                continue

        technologies = _technology_hints(files, languages, readme)

        summary_parts = [
            f"Repository: {full_name}.",
            f"Description: {repo.get('description') or 'Not provided'}.",
            f"Primary language: {max(languages, key=languages.get) if languages else 'Not detected'}.",
            f"Technologies inferred from repository evidence: {', '.join(technologies) or 'Not detected'}.",
            f"Important files: {', '.join(important[:20]) or 'None detected'}.",
            f"Topics: {', '.join(topics) or 'None'}.",
        ]

        return {
            "full_name": full_name,
            "name": name,
            "url": repo["html_url"],
            "default_branch": default_branch,
            "description": repo.get("description") or "",
            "visibility": repo.get("visibility") or "public",
            "language": max(languages, key=languages.get) if languages else "",
            "languages": languages,
            "topics": topics,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "readme": readme,
            "technologies": technologies,
            "important_files": important[:30],
            "code_samples": samples,
            "evidence_summary": " ".join(summary_parts),
        }
