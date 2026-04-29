#!/usr/bin/env python3
"""Fetch PR comments, reviews, and inline review threads from GitHub."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

QUERY = """\
query(
  $owner: String!,
  $repo: String!,
  $number: Int!,
  $commentsCursor: String,
  $reviewsCursor: String,
  $threadsCursor: String
) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      url
      title
      state
      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          body
          createdAt
          updatedAt
          author { login }
        }
      }
      reviews(first: 100, after: $reviewsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          state
          body
          submittedAt
          author { login }
        }
      }
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          diffSide
          startLine
          startDiffSide
          originalLine
          originalStartLine
          resolvedBy { login }
          comments(first: 100) {
            nodes {
              id
              body
              createdAt
              updatedAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""


def _run(cmd: list[str], stdin: str | None = None) -> str:
    proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "command failed")
    return proc.stdout


def _run_json(cmd: list[str], stdin: str | None = None) -> dict[str, Any]:
    return json.loads(_run(cmd, stdin=stdin))


def _ensure_auth() -> None:
    try:
        _run(["gh", "auth", "status"])
    except RuntimeError as exc:
        raise RuntimeError("gh auth is required; run `gh auth status` / `gh auth login`") from exc


def _current_branch_pr() -> tuple[str, str, int]:
    pr = _run_json(
        [
            "gh",
            "pr",
            "view",
            "--json",
            "number,headRepositoryOwner,headRepository",
        ]
    )
    owner = pr["headRepositoryOwner"]["login"]
    repo = pr["headRepository"]["name"]
    number = int(pr["number"])
    return owner, repo, number


def _fetch_page(
    owner: str,
    repo: str,
    number: int,
    comments_cursor: str | None,
    reviews_cursor: str | None,
    threads_cursor: str | None,
) -> dict[str, Any]:
    cmd = [
        "gh",
        "api",
        "graphql",
        "-F",
        "query=@-",
        "-F",
        f"owner={owner}",
        "-F",
        f"repo={repo}",
        "-F",
        f"number={number}",
    ]
    if comments_cursor:
        cmd += ["-F", f"commentsCursor={comments_cursor}"]
    if reviews_cursor:
        cmd += ["-F", f"reviewsCursor={reviews_cursor}"]
    if threads_cursor:
        cmd += ["-F", f"threadsCursor={threads_cursor}"]
    return _run_json(cmd, stdin=QUERY)


def _fetch_all(owner: str, repo: str, number: int) -> dict[str, Any]:
    conversation_comments: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    review_threads: list[dict[str, Any]] = []
    comments_cursor = None
    reviews_cursor = None
    threads_cursor = None
    pull_request = None

    while True:
        payload = _fetch_page(
            owner,
            repo,
            number,
            comments_cursor,
            reviews_cursor,
            threads_cursor,
        )
        errors = payload.get("errors")
        if errors:
            raise RuntimeError(json.dumps(errors, indent=2))

        pr = payload["data"]["repository"]["pullRequest"]
        if pull_request is None:
            pull_request = {
                "number": pr["number"],
                "url": pr["url"],
                "title": pr["title"],
                "state": pr["state"],
                "owner": owner,
                "repo": repo,
            }

        comments = pr["comments"]
        review_list = pr["reviews"]
        threads = pr["reviewThreads"]
        conversation_comments.extend(comments.get("nodes") or [])
        reviews.extend(review_list.get("nodes") or [])
        review_threads.extend(threads.get("nodes") or [])

        comments_cursor = comments["pageInfo"]["endCursor"] if comments["pageInfo"]["hasNextPage"] else None
        reviews_cursor = review_list["pageInfo"]["endCursor"] if review_list["pageInfo"]["hasNextPage"] else None
        threads_cursor = threads["pageInfo"]["endCursor"] if threads["pageInfo"]["hasNextPage"] else None
        if not (comments_cursor or reviews_cursor or threads_cursor):
            break

    return {
        "pull_request": pull_request,
        "conversation_comments": conversation_comments,
        "reviews": reviews,
        "review_threads": review_threads,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner")
    parser.add_argument("--repo")
    parser.add_argument("--number", type=int)
    args = parser.parse_args()

    _ensure_auth()
    if args.owner or args.repo or args.number:
        if not (args.owner and args.repo and args.number):
            raise RuntimeError("pass --owner, --repo, and --number together")
        owner, repo, number = args.owner, args.repo, args.number
    else:
        owner, repo, number = _current_branch_pr()

    result = _fetch_all(owner, repo, number)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
