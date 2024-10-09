<!-- markdownlint-disable -->
<p align="center">
    <a href="https://github.com/GitHubToolbox/">
        <img src="https://cdn.wolfsoftware.com/assets/images/github/organisations/githubtoolbox/black-and-white-circle-256.png" alt="GitHubToolbox logo" />
    </a>
    <br />
    <a href="https://github.com/GitHubToolbox/update-actions-package/actions/workflows/cicd.yml">
        <img src="https://img.shields.io/github/actions/workflow/status/GitHubToolbox/update-actions-package/cicd.yml?branch=master&label=build%20status&style=for-the-badge" alt="Github Build Status" />
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/blob/master/LICENSE.md">
        <img src="https://img.shields.io/github/license/GitHubToolbox/update-actions-package?color=blue&label=License&style=for-the-badge" alt="License">
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package">
        <img src="https://img.shields.io/github/created-at/GitHubToolbox/update-actions-package?color=blue&label=Created&style=for-the-badge" alt="Created">
    </a>
    <br />
    <a href="https://github.com/GitHubToolbox/update-actions-package/releases/latest">
        <img src="https://img.shields.io/github/v/release/GitHubToolbox/update-actions-package?color=blue&label=Latest%20Release&style=for-the-badge" alt="Release">
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/releases/latest">
        <img src="https://img.shields.io/github/release-date/GitHubToolbox/update-actions-package?color=blue&label=Released&style=for-the-badge" alt="Released">
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/releases/latest">
        <img src="https://img.shields.io/github/commits-since/GitHubToolbox/update-actions-package/latest.svg?color=blue&style=for-the-badge" alt="Commits since release">
    </a>
    <br />
    <a href="https://github.com/GitHubToolbox/update-actions-package/blob/master/.github/CODE_OF_CONDUCT.md">
        <img src="https://img.shields.io/badge/Code%20of%20Conduct-blue?style=for-the-badge" />
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/blob/master/.github/CONTRIBUTING.md">
        <img src="https://img.shields.io/badge/Contributing-blue?style=for-the-badge" />
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/blob/master/.github/SECURITY.md">
        <img src="https://img.shields.io/badge/Report%20Security%20Concern-blue?style=for-the-badge" />
    </a>
    <a href="https://github.com/GitHubToolbox/update-actions-package/issues">
        <img src="https://img.shields.io/badge/Get%20Support-blue?style=for-the-badge" />
    </a>
</p>

## Overview

A Python script to automate the updating of GitHub Actions in a specified folder by checking for newer versions on GitHub and updating the pinned
versions based on their commit SHAs. This tool is useful for keeping GitHub Actions up-to-date across multiple workflows in a repository.

## Features

- **Automatic Version Updates**: Checks for the latest version of each GitHub Action and updates to the latest version if available.
- **Dry Run Mode**: Preview changes without modifying any files.
- **Backup Creation**: Optionally create backups of modified files before updates.
- **Recursive Directory Scan**: Supports scanning all subdirectories for GitHub Actions.
- **Rate Limit Handling**: Automatically detects GitHub API rate limits and waits or skips requests accordingly.
- **Verbose Output**: Provides detailed information about the update process.

## Prerequisites

This script requires Python 3.6 or higher. The following Python packages are also needed:

- `requests`: For making HTTP requests to the GitHub API.
- `packaging`: For handling version comparison.
- `tabulate`: For displaying summary statistics in a table format.

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/GitHubToolbox/github-actions-updater.git
   cd github-actions-updater
   ```

2. Install the required packages using `pip`:

   ```bash
   pip install requests packaging tabulate
   ```

## Usage

Run the script with the following command-line arguments:

```bash
python github_actions_updater.py --path <folder_path> [OPTIONS]
```

### Command-Line Arguments

- `--path`: (Optional) Path to the folder containing GitHub Actions files. Default is the current directory (`.`).
- `--github-token`: (Optional) GitHub personal access token for authenticated requests. Provides higher API rate limits.
- `--dry-run`: (Optional) If specified, prints changes without modifying files.
- `--backup`: (Optional) If specified, creates a backup of each file before updating.
- `--extensions`: (Optional) Comma-separated list of file extensions to check. Default is `yml,yaml`.
- `--recursive`: (Optional) If specified, recursively searches subdirectories.
- `--verbose`: (Optional) If specified, prints detailed information about the update process.

### Examples

1. **Basic Usage**:
   
   Update GitHub Actions in the current directory:
   
   ```bash
   python github_actions_updater.py --path .
   ```

2. **Dry Run**:
   
   Preview changes without making any updates:
   
   ```bash
   python github_actions_updater.py --path /path/to/folder --dry-run
   ```

3. **Recursive Search**:
   
   Search all subdirectories for GitHub Actions files:
   
   ```bash
   python github_actions_updater.py --path /path/to/folder --recursive
   ```

4. **With Backup**:
   
   Create a backup before updating any files:
   
   ```bash
   python github_actions_updater.py --path /path/to/folder --backup
   ```

5. **Authenticated Requests**:
   
   Use a GitHub token to increase the rate limit:
   
   ```bash
   python github_actions_updater.py --path /path/to/folder --github-token YOUR_GITHUB_TOKEN
   ```

## Handling GitHub API Rate Limits

The script handles rate limits by checking the GitHub API response. If the rate limit is reached, it will either wait until the rate limit resets or skip further API requests, depending on the configured behaviour.

For more frequent updates or larger repositories, it is recommended to use a GitHub personal access token with the `--github-token` option to increase the rate limit.

<br />
<p align="right"><a href="https://wolfsoftware.com/"><img src="https://img.shields.io/badge/Created%20by%20Wolf%20on%20behalf%20of%20Wolf%20Software-blue?style=for-the-badge" /></a></p>
