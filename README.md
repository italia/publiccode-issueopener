# publiccode-issueopener

<p align="center">
  <a href="README.md">English</a> | 
  <a href="README.it.md">Italiano</a>
</p>

[![License](https://img.shields.io/github/license/italia/publiccode-issueopener.svg)](https://github.com/italia/publiccode-issueopener/blob/main/LICENSE)
[![Join the #publiccode channel](https://img.shields.io/badge/Slack%20channel-%23publiccode-blue.svg)](https://app.slack.com/client/T6C27AXE0/CAM3F785T)
[![Get invited](https://slack.developers.italia.it/badge.svg)](https://slack.developers.italia.it/)

publiccode-issueopener is a Python-based automation bot designed to ensure the correctness
of `publiccode.yml` files in GitHub repositories.

This bot gets the list of repositories in the [Italian software catalog](https://developers.italia.it/en/search)
through the [developers-italia-api](https://github.com/italia/developers-italia-api),
checks the validity of the `publiccode.yml` file for errors, logs them, and opens GitHub issues
accordingly.

This aids in maintaining the high quality of software catalog metadata, and eventually
ensures smooth public code sharing and reuse across different agencies.

## 🚀 Features

- **Automated issue generation:** Any detected errors in the `publiccode.yml` file
automatically trigger the creation of GitHub issues.
- **publiccode.yml compliance:** Ensures publiccode.yml files adhere to the Standard set
by the publiccode.yml schema.

## 💻 Getting Started

### Prerequisites

- Python 3.6 or higher

Install the required Python libraries using pip:

```bash
pip install argparse os hashlib re requests logging jinja2 PyGithub
```

### Installation

Clone the repository to your local machine.

```bash
git clone https://github.com/italia/publiccode-issueopener
cd publiccode-issueopener
```

## 🎮 Usage

You can run the script with the following command:

```bash
./publiccode-issueopener.py [--since NUMBER_OF_DAYS]

```

The `--since` option defines the number of past days to analyze in the logs.
By default, the script checks the past day's logs for any publiccode.yml errors.

### Environment Variables

To use the bot, you'll need to set some environment variables in your system:

- `BOT_GITHUB_TOKEN`: (**required**) The GitHub token for the bot, used to authenticate when opening issues in repositories
- `GITHUB_USERNAME`: The username of the GitHub bot that will open the issues. Default is `publiccode-validator-bot`
- `API_BASEURL`: The base URL for the API used to retreive the errors in publiccode.yml files. Default is `https://api.developers.italia.it/v1`

## 🤝 Contributing

We always welcome contributions! Feel free to open issues, fork the repository or submit a Pull Request.

## 🔗 Related Projects

* [publiccode-crawler](https://github.com/italia/publiccode-crawler)
* [developers-italia-api](https://github.com/italia/developers-italia-api)

## 👥 Maintainers

This software is maintained by the [Developers Italia team](https://developers.italia.it).

## 📄 License

Copyright© 2022-present - Presidency of the Council of Ministers (Italy)

This software is released under the EUPL-1.2 license. Please see the LICENSE file for more details.
