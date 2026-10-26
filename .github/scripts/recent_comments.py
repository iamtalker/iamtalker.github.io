#!/usr/bin/env python3
"""Write recent-comments.json: the newest giscus comments (Discussions) of a repository.

Run by .github/workflows/comments.yml whenever a comment is created; it only
needs the gh CLI (GH_TOKEN in the environment) and can be run by hand:

  python .github/scripts/recent_comments.py [owner/name] [output.json]

owner/name defaults to $GITHUB_REPOSITORY, output to recent-comments.json.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse

QUERY = """
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    discussions(first:30, orderBy:{field:UPDATED_AT, direction:DESC}) {
      nodes {
        title
        comments(last:20) {
          nodes {
            createdAt url bodyText author { login }
            replies(last:10) { nodes { createdAt url bodyText author { login } } }
          }
        }
      }
    }
  }
}
"""
KEEP = 20          # comments kept in the file
SNIPPET = 140      # characters of each comment shown


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REPOSITORY", "")
    out = sys.argv[2] if len(sys.argv) > 2 else "recent-comments.json"
    if "/" not in repo:
        sys.exit("usage: recent_comments.py owner/name [output.json]")
    owner, name = repo.split("/", 1)

    r = subprocess.run(
        ["gh", "api", "graphql", "-f", "query=" + QUERY, "-F", "owner=" + owner, "-F", "name=" + name],
        capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit("gh api failed:\n" + r.stdout + r.stderr)
    data = json.loads(r.stdout)
    if data.get("errors"):
        sys.exit("GraphQL errors:\n" + json.dumps(data["errors"], ensure_ascii=False))

    items = []
    for d in (data["data"]["repository"]["discussions"]["nodes"] or []):
        for c in (d["comments"]["nodes"] or []):
            for x in [c] + ((c.get("replies") or {}).get("nodes") or []):
                text = re.sub(r"\s+", " ", x["bodyText"] or "").strip()
                items.append({
                    "createdAt": x["createdAt"],
                    "author": (x["author"] or {}).get("login", "ghost"),
                    "page": urllib.parse.unquote(d["title"]),   # giscus names the discussion after the (URL-encoded) page path
                    "text": text[:SNIPPET] + ("…" if len(text) > SNIPPET else ""),
                    "url": x["url"],
                })
    items.sort(key=lambda i: i["createdAt"], reverse=True)
    result = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "comments": items[:KEEP]}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("%d comments -> %s" % (len(result["comments"]), out))


if __name__ == "__main__":
    main()
