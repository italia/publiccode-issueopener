#!/usr/bin/env python3
"""Open issues in repos for errors in publiccode.yml."""

import argparse
import os
import time
import hashlib
import re
import requests
import logging

import jinja2
import github

from collections import namedtuple
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

API_BASEURL = os.getenv('API_BASEURL', 'https://api.developers.italia.it/v1')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'publiccode-validator-bot')

SoftwareLog = namedtuple("SoftwareLog", "log_url software formatted_error_output")

def to_markdown(error: str, repo_url: str) -> str:
    out = "| |Message|\n|-|-|\n"
    icons = {
        "error": "❌",
        "warning": ":warning:",
    }

    for line in error.splitlines():
        m = re.match(r"^publiccode.yml:(?P<line_num>\d+):\d+: (?P<level>.*?): (?P<msg>.*)", line)
        if m is None:
            out += f"|❌|`{line}`|\n"
            continue

        line_num = m.group('line_num')
        level = m.group('level')
        msg = m.group('msg')

        repo_url = repo_url.removesuffix('.git')

        out += f"|{icons.get(level, '')} [`publiccode.yml:{line_num}`]({repo_url}/blob/HEAD/publiccode.yml#L{line_num})| `{msg}`|\n"

    return out

def software():
    software = []

    page = True
    page_after = ""

    while page:
        res = requests.get(
            f'{API_BASEURL}/software{page_after}',
            params={
                'page[size]': 100,
            }
        )
        res.raise_for_status()

        body = res.json()
        software += body['data']

        page_after = body['links']['next']
        page = bool(page_after)

    return software

def software_logs(days):
    logs = []

    page = True
    page_after = ""

    begin = datetime.now(timezone.utc) - timedelta(days=days)

    while page:
        res = requests.get(
            f'{API_BASEURL}/logs{page_after}',
            params={
                'from': begin.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'page[size]': 100,
            }
        )
        res.raise_for_status()

        body = res.json()
        logs += body['data']

        page_after = body['links']['next']
        page = bool(page_after)

    # XXX: get last for repo

    for log in logs:
        match = re.search(r"^\[(?P<repo>.+?)\] BAD publiccode.yml: (?P<parser_output>.*)", log['message'], re.MULTILINE|re.DOTALL)
        if match:
            entity = log.get('entity')

            if not entity or entity == "//":
                continue

            res = requests.get(f'{API_BASEURL}{entity}')
            res.raise_for_status()

            software = res.json()

            yield SoftwareLog(f'{API_BASEURL}/logs/{log["id"]}', software, to_markdown(match.group('parser_output'), software['url']))

def issues(gh: github.Github, repo: str) -> list[github.Issue.Issue]:
    issues = gh.search_issues(
        "publiccode.yml in:title state:open is:issue",
        "updated",
        "desc",
        repo=repo,
        author=GITHUB_USERNAME
    )

    return [issue for issue in issues]

def issues_by_state(issues: list[github.Issue.Issue], state: str) -> list[github.Issue.Issue]:
    return list(filter(lambda issue: issue.state == state, issues))

def has_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(iter(issues), False)

def has_open_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(filter(lambda issue: issue.state == 'open', issues), None)

def has_closed_issue(issues: list[github.Issue.Issue]) -> github.Issue.Issue | None:
    return next(filter(lambda issue: issue.state == 'closed', issues), None)

def should_update_issue(sha1sum: str, issue: github.Issue.Issue) -> bool:
    compact = list(filter(None, issue.body.splitlines()))
    first_line = compact[0]

    m = re.match(r"^<!-- (?P<data>.*?) -->", first_line)
    if m is None:
        print(f"WARNING: can't find hidden_fields in issue {issue.html_url}")
        return False

    data = re.split("[,=]", m.group('data'))
    hidden_fields = dict(zip(data[::2], data[1::2]))

    return issue.state == 'open' or hidden_fields['sha1sum'] != sha1sum

def status(gh):
    issues = gh.search_issues(f"author:{GITHUB_USERNAME} type:issue sort:updated")

    for issue in issues:
        print(f"{issue.state}\t{issue.updated_at.isoformat()}\t{issue.html_url}")

def run(gh, since):
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = environment.get_template("github/issue.it.tpl.txt")

    for log in software_logs(since):
        time.sleep(1)
        if not log.software['url'].startswith("https://github.com/"):
            print(f"{log.software['url']} is not a GitHub repo. Only GitHub is supported for now.")
            continue

        if "are not in the same repo" in log.formatted_error_output:
            print(f"skipping {log.software['url']} (are not in the same repo)")
            continue
        if "timeout" in log.formatted_error_output:
            print(f"skipping {log.software['url']} (timeout)")
            continue

        if log.software['url'] == 'https://github.com/KnowageLabs/Knowage-Server.git' or \
           log.software['url'] == 'https://github.com/teamdigitale/dati-semantic-lode.git' or \
           log.software['url'] == 'https://github.com/FastReports/FastReport.git':
            print(f"Skipping {log.software['url']}")
            continue

        # if log.software['url'] != 'https://github.com/UniversitaDellaCalabria/uniTicket.git':
        #     print(f"Skipping {log.software['url']}")
        #     continue

        #print(log.formatted_error_output)
        debug = urlparse(log.software['url']).path
        sha1sum = hashlib.sha1(log.formatted_error_output.encode('utf-8')).hexdigest()

        content = template.render(
            {"formatted_error_output": log.formatted_error_output,
             "debug": debug,
             "api_log_url": log.log_url,
             "hidden_fields": {
                 "sha1sum": sha1sum
             }},
        )

        repo_path  = urlparse(log.software['url']).path[1:].removesuffix('.git')
        iss = issues(gh, repo_path)

        issue = has_issue(iss)
        try:
            if not issue:
                repo = gh.get_repo(f"{repo_path}", lazy=True)
                print(f"Creating issue for {log.software['url']}...")
                repo.create_issue(title="Errors in publiccode.yml file", body=content)
            elif should_update_issue(sha1sum, issue):
                print(f"(not) Updating issue for {log.software['url']}...")
                # issue.edit(body=content)
            else:
                print("Doing nothing")
        # github.GithubException.GithubException: 410 {"message": "Issues are disabled for this repo", "documentation_url": "https://docs.github.com/v3/issues/"}
        # https://github.com/ScuolaNormaleSuperiore/design-laboratori-wordpress-theme
        except Exception as e:
            # XXX
            print(e)
            continue

def main():
    parser = argparse.ArgumentParser(
        description="Open issues in repos for errors in publiccode.yml from the logs in Developers Italia API.",
    )
    parser.add_argument(
        '--since', action="store", dest="since", type=int,
        default=1, help="Number of days to go back for the analyzed logs (default: 1)"
    )

    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('status')

    args = parser.parse_args()

    gh = github.Github(os.getenv("BOT_GITHUB_TOKEN"))

    # logging.basicConfig(level=logging.DEBUG)
    # github.enable_console_debug_logging()

    if args.command == 'status':
        status(gh)
    else:
        run(gh, args.since)

if __name__ == "__main__":
    main()
