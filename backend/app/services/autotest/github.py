from __future__ import annotations

from urllib.parse import urlparse


def validate_github_url(repo_url: str) -> bool:
    try:
        parsed = urlparse(str(repo_url or "").strip())
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    if parsed.params or parsed.query or parsed.fragment:
        return False
    cleaned_path = parsed.path.strip("/")
    parts = [part for part in cleaned_path.split("/") if part]
    if len(parts) != 2:
        return False
    owner, repo = parts
    if not owner or not repo:
        return False
    if any(token in repo_url for token in (";", "\\", "..", "%00")):
        return False
    repo_name = repo.removesuffix(".git")
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return set(owner) <= allowed_chars and set(repo_name) <= allowed_chars and bool(repo_name)


def get_repo_info(repo_url: str) -> dict[str, object]:
    if not validate_github_url(repo_url):
        raise ValueError("Invalid GitHub URL.")
    parsed = urlparse(repo_url.strip())
    owner, repo = [part for part in parsed.path.strip("/").split("/") if part]
    normalized_repo = repo.removesuffix(".git")
    normalized_url = f"https://github.com/{owner}/{normalized_repo}"
    return {
        "owner": owner,
        "repo": normalized_repo,
        "url": normalized_url,
        "default_branch": "",
        "provider": "github",
        "clone_supported": False,
        "analysis_scope": "queued_local_intake_only",
    }
