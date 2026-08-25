#!/usr/bin/env python3
"""Health-check candidate OSS repos for contribution suitability.

Usage: python3 check_repo_health.py owner/repo [owner/repo ...]

Prints per repo: stars, last push, last merged PR date, open PR count,
good-first-issue count, primary language.

Uses the unauthenticated GitHub API (~60 req/hr limit), so batch ALL
candidates in one run. Uses the search API for merged-PR recency: the
pulls endpoint returns stale rows with old merged_at even on active repos.
"""
import json
import sys
import urllib.request


def get(url):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "hermes-oss-health-check"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main(repos):
    for repo in repos:
        try:
            d = get(f"https://api.github.com/repos/{repo}")
            s = get(
                f"https://api.github.com/search/issues?q=repo:{repo}+type:pr+is:merged"
                "&sort=updated&order=desc&per_page=6"
            )
            merges = [i["closed_at"][:10] for i in s.get("items", []) if i.get("closed_at")]
            o = get(f"https://api.github.com/search/issues?q=repo:{repo}+type:pr+is:open&per_page=1")
            g = get(
                f"https://api.github.com/search/issues?q=repo:{repo}+type:issue+is:open"
                '+label:"good first issue"&per_page=1'
            )
            print(
                f"{repo:42s} stars={d['stargazers_count']:>6} "
                f"pushed={d['pushed_at'][:10]} most-recently-updated merged PR={merges[0] if merges else 'NONE'} "
                f"openPRs={o.get('total_count'):>3} goodFirst={g.get('total_count')} "
                f"lang={d.get('language')}"
            )
        except Exception as e:
            print(f"{repo:42s} ERROR {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
