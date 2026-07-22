#!/usr/bin/env python3
"""Render the markdown neofetch README with live GitHub stats.

Single source of truth for README.md. Edit profile text/skills in INFO below.
Runs in CI via .github/workflows/stats.yml. Locally:
    ACCESS_TOKEN=ghp_xxx python3 stats.py

Stats need a token that can read your private contributions:
  - ACCESS_TOKEN: a personal access token with scopes `read:user` and `repo`
    (recommended — includes private contributions).
  - Falls back to GITHUB_TOKEN (public stats only) when ACCESS_TOKEN is unset.
"""

import datetime
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USERNAME", "angeeelvega")
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")

# ---------------------------------------------------------------------------
# Profile content — edit here
# ---------------------------------------------------------------------------
TITLE = "angel@vega"
PROMPT_NAME = "angel@dev"
TERMINAL = [  # lines shown inside the ASCII terminal (below the title bar)
    "$ whoami", "> angel_vega", "",
    "$ cat role.txt", "> data & ai engineer", "",
    "$ location", "> colombia", "",
    "$ status", "> building software... _", "",
]
TOP = [
    ("OS:", "Colombia"),
    ("Host:", "NyxN"),
    ("Role:", "Data & AI Engineer"),
    ("Shell:", "building software"),
    ("Editor:", "VS Code, Cursor"),
    ("AI Tools:", "Codex, Claude Code"),
]
STACK = [
    ("Languages.Code:", "JavaScript, TypeScript, Python, Java"),
    ("Languages.Web:", "HTML, CSS, React, Angular, Next.js"),
    ("Frameworks:", "Node.js, NestJS, Spring, FastAPI"),
    ("Databases:", "PostgreSQL, MySQL, MongoDB, Oracle"),
    ("Cloud:", "AWS, Terraform, Docker, Supabase"),
    ("Design:", "Figma, Photoshop, Illustrator"),
]
CONTACT = [
    ("Portfolio:", "portfolio-angel-vega.vercel.app"),
    ("LinkedIn:", "angelvega1"),
]
LINKS = """
<div align="center">

<a href="https://portfolio-angel-vega.vercel.app/"><img src="https://img.shields.io/badge/Portfolio-visit-00c9a7?style=flat-square&logo=vercel&logoColor=white" alt="Portfolio" /></a>
<a href="https://www.linkedin.com/in/angelvega1/"><img src="https://img.shields.io/badge/LinkedIn-connect-0a66c2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
<a href="https://github.com/angeeelvega"><img src="https://img.shields.io/badge/GitHub-follow-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub" /></a>

</div>
"""

INNER = 27  # terminal inner width

# ---------------------------------------------------------------------------
# GitHub stats
# ---------------------------------------------------------------------------
def _gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USER,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_stats():
    """Return dict with repos, stars, followers, contrib. Contributions include
    private activity (totalCommitContributions + restrictedContributionsCount
    summed across every year since the account was created)."""
    # Counts ALL owned repos the token can see: with ACCESS_TOKEN (repo scope)
    # this includes private repos → whole-account totals. With only GITHUB_TOKEN
    # it falls back to public repos.
    base = _gql(
        '{ user(login: "%s") { createdAt followers { totalCount } '
        'repos: repositories(ownerAffiliations: OWNER, first: 100) '
        '{ totalCount nodes { stargazerCount } } } }' % USER
    )["user"]

    repos = base["repos"]["totalCount"]
    stars = sum(n["stargazerCount"] for n in base["repos"]["nodes"])
    followers = base["followers"]["totalCount"]

    year0 = int(base["createdAt"][:4])
    now = datetime.datetime.now(datetime.timezone.utc).year
    aliases = " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", '
        f'to: "{y}-12-31T23:59:59Z") '
        "{ totalCommitContributions restrictedContributionsCount }"
        for y in range(year0, now + 1)
    )
    data = _gql('{ user(login: "%s") { %s } }' % (USER, aliases))["user"]
    contrib = sum(
        data[f"y{y}"]["totalCommitContributions"]
        + data[f"y{y}"]["restrictedContributionsCount"]
        for y in range(year0, now + 1)
    )
    return {"repos": repos, "stars": stars, "followers": followers, "contrib": contrib}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _box():
    lines = [
        "╭" + "─" * (INNER + 2) + "╮",
        "│ " + f"  o  o  o    {PROMPT_NAME}".ljust(INNER) + " │",
        "├" + "─" * (INNER + 2) + "┤",
    ]
    for c in TERMINAL:
        lines.append("│ " + ("  " + c if c else "").ljust(INNER) + " │")
    lines.append("╰" + "─" * (INNER + 2) + "╯")
    return lines


def _right(stats):
    sep = "─" * 29
    rows = [TITLE, sep]
    rows += [k.ljust(15) + v for k, v in TOP]
    rows.append("")
    rows += [k.ljust(17) + v for k, v in STACK]
    rows.append("")
    rows += ["Contact", sep]
    rows += [k.ljust(12) + v for k, v in CONTACT]
    rows += ["", "GitHub Stats", sep]
    rows.append(
        f"Repos: {stats['repos']}    Stars: {stats['stars']}    "
        f"Contributions: {stats['contrib']}    Followers: {stats['followers']}"
    )
    return rows


def render(stats):
    box, right = _box(), _right(stats)
    lw = max(len(x) for x in box) + 3
    n = max(len(box), len(right))
    body = []
    for i in range(n):
        left = box[i] if i < len(box) else ""
        rt = right[i] if i < len(right) else ""
        body.append((left.ljust(lw) + rt).rstrip())
    return "```\n" + "\n".join(body) + "\n```\n" + LINKS


def _timestamp_block():
    # Colombia time (UTC-5, no DST).
    cot = datetime.timezone(datetime.timedelta(hours=-5))
    now = datetime.datetime.now(datetime.timezone.utc).astimezone(cot)
    stamp = now.strftime("%b %d, %Y · %I:%M %p").replace("· 0", "· ")
    return (
        '\n<div align="center">\n'
        f"<sub>⏱ Last updated: {stamp} (COT) · auto-updated daily</sub>\n"
        "</div>\n"
    )


def main():
    try:
        stats = fetch_stats()
    except Exception as e:  # noqa: BLE001 — never fail the workflow on API hiccups
        print(f"Could not fetch stats ({e}); leaving README.md unchanged.")
        return 0
    print("Stats:", stats)
    # Always rewrite with a fresh "Last updated" timestamp, so every run bumps
    # the time and produces a commit — even when the stats themselves are unchanged.
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(render(stats) + _timestamp_block())
    print("Wrote README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
