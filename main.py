#!/usr/bin/env python3
"""Open issues in repos for errors in publiccode.yml."""

import os
import re
import requests
import logging

import jinja2
import github

from collections import namedtuple

API_BASEURL = os.getenv('API_BASEURL', 'https://api.developers.italia.it/v1')

SoftwareLog = namedtuple("SoftwareLog", "repo formatted_error_output")

def to_markdown(error: str) -> str:
    out = "|Line|Message|\n|-|-|\n"
    icons = {
        "error": "❌",
        "warning": ":warning:",
    }

    # FIXME
    url = "https://github.com/italia/publiccode-editor"

    for line in error.splitlines():
        m = re.match(r"^publiccode.yml:(?P<line_num>\d)+:\d+: (?P<level>.*?): (?P<msg>.*)", line)
        if m is None:
            out += line
            continue

        line_num = m.group('line_num')
        level = m.group('level')
        msg = m.group('msg')

        out += f"|{icons.get(level, '')} [`publiccode.yml:{line_num}`]({url}/blob/HEAD/publiccode.yml#L{line_num})| `{msg}`|\n"

    return out

def software_logs():
    logs = []

    page = True
    page_after = ""

    while page:
        res = requests.get(f"{API_BASEURL}/logs{page_after}")
        res.raise_for_status()

        body = res.json()
        logs += body['data']

        page_after = body['links']['next']
        page = bool(page_after)
        page = False

    for log in logs:
        match = re.search(r"^\[(?P<repo>.+?)\] BAD publiccode.yml: (?P<parser_output>.*)", log['message'], re.MULTILINE|re.DOTALL)
        if match:
            yield SoftwareLog(match.group('repo'), to_markdown(match.group('parser_output')))

def main():
    gh = github.Github(os.getenv("GITHUB_TOKEN"))
    github.enable_console_debug_logging()

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = environment.get_template("github/issue.tpl.txt")

    for log in software_logs():
        content = template.render(
            {"formatted_error_output": log.formatted_error_output},
        )

        repo = gh.get_repo(f"{log.repo}", lazy=True)
        repo.create_issue(title="Errors in publiccode.yml file", body=content)

if __name__ == "__main__":
    main()
