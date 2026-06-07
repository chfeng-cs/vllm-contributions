#!/usr/bin/env python3
"""
Sync PR statuses from GitHub API and update README.md automatically.

Mode: hybrid
  - Auto-discover all PRs authored by GITHUB_USER in TARGET_REPOS
  - Manual annotations (category, impact) loaded from ANNOTATIONS dict
  - PRs without annotations still appear, just with less detail

Usage: python scripts/update_readme.py
Requires: GITHUB_TOKEN env var (read:public_repo scope)
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────
GITHUB_USER  = "chfeng-cs"
TARGET_REPOS = [
    "vllm-project/vllm",
    # "sgl-project/sglang",
    # "triton-lang/triton",
]

CATEGORY_ORDER = ["Issue", "Core Feature", "Bug Fix", "Review / Discussion", "Docs", "Other"]

# ── MANUAL ANNOTATIONS ────────────────────────────────────────────────────────
# Key: ("owner/repo", pr_number)
# Only fill in PRs you want to highlight.
# Unannotated PRs still appear automatically under "Other".
ANNOTATIONS: dict[tuple[str, int], dict] = {
    ("vllm-project/vllm", 42321): {
        "category": "Core Feature",
        "impact": "~25% TTFT reduction (benchmarked under high load with disk KV prefetch, L20)",
    },
    ("vllm-project/vllm", 41847): {
        "category": "Core Feature",
        "impact": "Reduces user config burden; fixes MultiConnector gap vs PR #42045",
    },
    ("vllm-project/vllm", 42206): {
        "category": "Metrics",
        "impact": "Add group-aware KV cache capacity Prometheus gauges",
    },
    ("vllm-project/vllm", 44101): {
        "category": "Bug Fix",
        "impact": "—",
    },
    ("vllm-project/vllm", 44097): {
        "category": "Bug Fix",
        "impact": "—",
    },
    # ("vllm-project/vllm", XXXX): {   # ← Prometheus overcounting PR, fill when open
    #     "category": "Bug Fix",
    #     "impact": "Correctness fix: Prometheus metrics overcounting for HMA hybrid models",
    # },
    ("vllm-project/vllm", 41622): {
        "category": "Review / Discussion",
        "impact": "Root cause analysis for ROCm/LoRA/CUDA graph capture bug",
    },
    ("vllm-project/vllm", 42073): {
        "category": "Docs",
        "impact": "—",
    },
    ("vllm-project/vllm", 42066): {
        "category": "Docs",
        "impact": "—",
    },
    ("vllm-project/vllm", 42160): {
        "category": "Docs",
        "impact": "—",
    },
    ("vllm-project/vllm", 42077): {
        "category": "Docs",
        "impact": "—",
    },
    ("vllm-project/vllm", 42872): {
        "category": "Bug Fix",
        "impact": "Closed: implemented by core maintainer",
    },
    ("vllm-project/vllm", 42214): {
        "category": "Other", 
        "impact": "Closed: duplicate",
    },
    ("vllm-project/vllm", 42086): {
        "category": "Other",
        "impact": "Closed: first version of PR #42321, abandoned due to significant design differences",
    },
    ("vllm-project/vllm", 42846): {
        "category": "Issue",
        "impact": "—",
    },
}
# ──────────────────────────────────────────────────────────────────────────────

README_PATH   = "README.md"
SECTION_START = "<!-- PR_TABLE_START -->"
SECTION_END   = "<!-- PR_TABLE_END -->"


def gh_api(path: str, params: dict | None = None) -> dict | list:
    token = os.environ.get("GITHUB_TOKEN", "")
    query = ""
    if params:
        query = "?" + "&".join(
            f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()
        )
    url = f"https://api.github.com{path}{query}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}")
        return {}
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return {}


def fetch_all_prs_and_issues(repo: str) -> list[dict]:
    """Fetch all PRs and issues (open + closed) authored by GITHUB_USER in a repo."""
    owner, name = repo.split("/")
    all_items = []
    
    for item_type in ["pr", "issue"]:
        page = 1
        print(f"  Fetching {item_type}s from {repo}...")
        
        while True:
            result = gh_api("/search/issues", {
                "q": f"author:{GITHUB_USER} type:{item_type} repo:{repo}",
                "per_page": 100,
                "page": page,
            })
            items = result.get("items", [])
            if not items:
                break

            for item in items:
                number = item["number"]
                if item_type == "pr":
                    # Search API doesn't include merged_at; fetch PR detail separately
                    detail = gh_api(f"/repos/{owner}/{name}/pulls/{number}")
                    merged_at = detail.get("merged_at") if isinstance(detail, dict) else None
                else:
                    merged_at = None
                    
                all_items.append({
                    "repo":      repo,
                    "number":    number,
                    "title":     item["title"],
                    "html_url":  item["html_url"],
                    "state":     item["state"],
                    "merged_at": merged_at,
                    "item_type": item_type,
                })
                time.sleep(0.1)

            if len(items) < 100:
                break
            page += 1
            time.sleep(0.5)

    print(f"  Found {len(all_items)} item(s) in {repo}")
    return all_items


def status_badge(item: dict) -> str:
    if item["state"] == "open":
        return "🔄 Open"
    if item.get("merged_at"):
        return "☑️ Merged"
    if item.get("item_type") == "issue":
        return "☑️ Closed"
    return "❌ Closed"


def build_table(all_items: list[dict]) -> str:
    rows_by_category: dict[str, list[str]] = {cat: [] for cat in CATEGORY_ORDER}

    for item in all_items:
        key        = (item["repo"], item["number"])
        annotation = ANNOTATIONS.get(key, {})
        category   = annotation.get("category", "Other")
        impact     = annotation.get("impact", "—")
        badge      = status_badge(item)
        url        = item["html_url"]
        number     = item["number"]
        # Shorten repo name for display: "vllm-project/vllm" → "vllm"
        repo_short = item["repo"].split("/")[-1]
        title      = item["title"]

        row = f"| [{repo_short}#{number}]({url}) | {title} | {badge} | {impact} |"
        rows_by_category.setdefault(category, []).append(row)

    lines = []
    for cat in CATEGORY_ORDER:
        rows = rows_by_category.get(cat, [])
        if not rows:
            continue
        if cat == "Issue":
            lines.append(f"\n<details>\n<summary>{cat}</summary>\n")
            lines.append("| Issue | Title | Status | Impact |")
            lines.append("|-------|-------|--------|--------|")
            lines.extend(rows)
            lines.append("</details>")
        else:
            lines.append(f"\n### {cat}\n")
            lines.append("| PR | Title | Status | Impact |")
            lines.append("|----|-------|--------|--------|")
            lines.extend(rows)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"\n> Last synced: {now}")
    return "\n".join(lines)


def update_readme(table: str) -> bool:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"{re.escape(SECTION_START)}.*?{re.escape(SECTION_END)}",
        re.DOTALL,
    )
    if not pattern.search(content):
        print(f"ERROR: markers not found in {README_PATH}")
        print(f"  Add  {SECTION_START}  and  {SECTION_END}  around the PR section.")
        sys.exit(1)

    replacement = f"{SECTION_START}\n{table}\n{SECTION_END}"
    new_content = pattern.sub(replacement, content)

    if new_content == content:
        print("No changes detected.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"{README_PATH} updated.")
    return True


if __name__ == "__main__":
    if not os.environ.get("GITHUB_TOKEN"):
        print("Warning: GITHUB_TOKEN not set — rate limit is 60 req/hr.")

    all_items = []
    for repo in TARGET_REPOS:
        all_items.extend(fetch_all_prs_and_issues(repo))

    def sort_key(item):
        cat = ANNOTATIONS.get((item["repo"], item["number"]), {}).get("category", "Other")
        cat_rank = CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else 99
        return (cat_rank, -item["number"])

    all_items.sort(key=sort_key)

    print(f"\nBuilding table for {len(all_items)} item(s)...")
    table = build_table(all_items)
    update_readme(table)
