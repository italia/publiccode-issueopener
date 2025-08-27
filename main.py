#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,too-many-locals,too-many-branches,too-many-statements,line-too-long

"""Open issues in repos for errors in publiccode.yml."""

import argparse
import hashlib
import os
import re
import sys
import time
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import github
import jinja2
import requests

API_BASEURL = os.getenv("API_BASEURL", "https://api.developers.italia.it/v1")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "publiccode-validator-bot")
DEFAULT_TIMEOUT = 20

SoftwareLog = namedtuple(
    "SoftwareLog", "log_url software formatted_error_output datetime"
)


def to_markdown(error: str, repo_url: str) -> str:
    """Convert parser output to a compact Markdown table with source links."""
    out = "| |Message|\n|-|-|\n"
    icons = {
        "error": "❌",
        "warning": ":warning:",
    }

    for line in error.splitlines():
        m = re.match(
            r"^publiccode.yml:(?P<line_num>\d+):\d+: (?P<level>.*?): (?P<msg>.*)", line
        )
        if m is None:
            out += f"|❌|`{line}`|\n"
            continue

        line_num = m.group("line_num")
        level = m.group("level")
        msg = m.group("msg")

        repo_url = repo_url.removesuffix(".git")

        out += f"|{icons.get(level, '')} [`publiccode.yml:{line_num}`]({repo_url}/blob/HEAD/publiccode.yml#L{line_num})| `{msg}`|\n"

    return out


def get_software():
    """Return all software entries from the API (paginated)."""
    software_list = []

    page = True
    page_after = ""

    while page:
        res = requests.get(
            f"{API_BASEURL}/software{page_after}",
            params={
                "page[size]": 100,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        res.raise_for_status()

        body = res.json()
        software_list += body["data"]

        page_after = body["links"]["next"]
        page = bool(page_after)

    return software_list


def get_software_logs(days):
    logs = []

    page = True
    page_after = ""

    begin = datetime.now(timezone.utc) - timedelta(days=days)

    while page:
        res = requests.get(
            f"{API_BASEURL}/logs{page_after}",
            params={
                "from": begin.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page[size]": 100,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        res.raise_for_status()

        body = res.json()
        logs += body["data"]

        page_after = body["links"]["next"]
        page = bool(page_after)

    seen_entities = set()

    for log in logs:
        match = re.search(
            r"^\[(?P<repo>.+?)\] BAD publiccode.yml: (?P<parser_output>.*)",
            log["message"],
            re.MULTILINE | re.DOTALL,
        )
        if match:
            entity = log.get("entity")

            if not entity or entity == "//":
                continue

            if entity in seen_entities:
                continue

            seen_entities.add(entity)

            res = requests.get(f"{API_BASEURL}{entity}", timeout=DEFAULT_TIMEOUT)
            res.raise_for_status()

            software = res.json()

            yield SoftwareLog(
                f'{API_BASEURL}/logs/{log["id"]}',
                software,
                to_markdown(match.group("parser_output"), software["url"]),
                datetime.fromisoformat(log["createdAt"]),
            )


def publiccodeyml_last_change(repo: github.Repository) -> datetime:
    commits = repo.get_commits(path="publiccode.yml")

    if commits.totalCount == 0:
        return datetime.fromtimestamp(0)

    return commits[0].commit.author.date.replace(tzinfo=timezone.utc)


def get_issues(gh: github.Github, repo: str) -> list[github.Issue.Issue]:
    issues = gh.search_issues(
        "publiccode.yml in:title state:open is:issue",
        "updated",
        "desc",
        repo=repo,
        author=GITHUB_USERNAME,
    )

    return list(issues)


def issues_by_state(
    issues: list[github.Issue.Issue], state: str
) -> list[github.Issue.Issue]:
    return list(filter(lambda issue: issue.state == state, issues))


def has_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(iter(issues), False)


def has_open_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(filter(lambda issue: issue.state == "open", issues), None)


def has_closed_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(filter(lambda issue: issue.state == "closed", issues), None)


def should_update_issue(sha1sum: str, issue: github.Issue.Issue) -> bool:
    compact = list(filter(None, issue.body.splitlines()))
    first_line = compact[0]

    m = re.match(r"^<!-- (?P<data>.*?) -->", first_line)
    if m is None:
        print(f"WARNING: can't find hidden_fields in issue {issue.html_url}")
        return False

    data = re.split("[,=]", m.group("data"))
    hidden_fields = dict(zip(data[::2], data[1::2]))

    return issue.state == "open" and hidden_fields["sha1sum"] != sha1sum


def status(gh):
    issues = gh.search_issues(f"author:{GITHUB_USERNAME} type:issue sort:updated")

    for issue in issues:
        print(f"{issue.state}\t{issue.updated_at.isoformat()}\t{issue.html_url}")


def run(gh, since, dry_run, lang):
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = environment.get_template(f"github/issue.{lang}.tpl.txt")

    issues_created = 0
    issues_updated = 0
    issues_untouched = 0

    for log in get_software_logs(since):
        url = log.software["url"].lower()
        if not url.startswith("https://github.com/"):
            print(f"🚫 {url} is not a GitHub repo. Only GitHub is supported for now.")
            continue

        # Ignore some reachability errors until we implement
        # https://github.com/italia/publiccode-issueopener/issues/24
        if ": forbidden resource" in log.formatted_error_output:
            print(f"skipping {url} (unreachability, forbidden resource...)")
            continue
        if ": i/o timeout" in log.formatted_error_output:
            print(f"skipping {url} (unreachability, i/o timeout...)")
            continue

        debug = urlparse(url).path
        sha1sum = hashlib.sha1(log.formatted_error_output.encode("utf-8")).hexdigest()

        content = template.render(
            {
                "formatted_error_output": log.formatted_error_output,
                "debug": debug,
                "api_log_url": log.log_url,
                "hidden_fields": {"sha1sum": sha1sum},
            },
        )

        repo_path = urlparse(url).path[1:].removesuffix(".git")

        try:
            iss = get_issues(gh, repo_path)

            issue = has_issue(iss)
            repo = gh.get_repo(f"{repo_path}", lazy=True)

            if publiccodeyml_last_change(repo) >= log.datetime:
                print(
                    f"⌛ publiccode.yml was changed in the repo after our log, doing nothing ({url})"
                )
                continue

            if not issue:
                print(f"➕ Creating issue for {url}...")
                if not dry_run:
                    repo.create_issue(
                        title="Errors in publiccode.yml file", body=content
                    )

                issues_created += 1
            elif should_update_issue(sha1sum, issue):
                print(f"🔄 Updating issue for {url}...")
                if not dry_run:
                    issue.edit(body=content)

                issues_updated += 1
            else:
                print(f"== Issue is open and unchanged, doing nothing ({url})")
                issues_untouched += 1
        except github.GithubException as e:
            if isinstance(e, github.RateLimitExceededException):
                reset_timestamp = int(e.headers.get("x-ratelimit-reset", 0))
                sleep_duration = max(0, reset_timestamp - int(time.time()) + 10)

                print(
                    f"Rate limit exceeded. Sleeping for {sleep_duration} seconds...",
                    end="",
                )
                sys.stdout.flush()
                time.sleep(sleep_duration)
                print("done")
            else:
                print(f"Error in the GitHub request, repo={url}: {e}")
            continue

    print("==== Summary ====")
    print(f"➕ Created issues:\t{issues_created}")
    print(f"🔄 Updated issues:\t{issues_updated}")
    print(f"== Untouched issues:\t{issues_untouched}")


def main():
    parser = argparse.ArgumentParser(
        description="Open issues in repos for errors in publiccode.yml from the logs in Developers Italia API.",
    )
    parser.add_argument(
        "--since",
        action="store",
        dest="since",
        type=int,
        default=1,
        help="Number of days to go back for the analyzed logs (default: 1)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="Don't actually create or update issues, just print",
    )
    parser.add_argument(
        "--lang",
        action="store",
        dest="lang",
        choices=["en", "it"],
        default="en",
        help="Use this language for the issues. (default: en)",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status")

    args = parser.parse_args()

    gh = github.Github(os.getenv("BOT_GITHUB_TOKEN"))

    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    # github.enable_console_debug_logging()

    if args.command == "status":
        status(gh)
    else:
        run(gh, args.since, args.dry_run, args.lang)


if __name__ == "__main__":
    main()
