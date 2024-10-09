"""
GitHub Actions Version Updater.

This script scans a specified folder for files containing GitHub Actions references,
then checks for the latest available versions of each action on GitHub. If a newer version
is found, the script can automatically update the file to use the latest version's commit SHA.
It supports optional features such as creating backups of modified files, running in dry-run
mode to preview changes, and recursively scanning subdirectories.

Features:
    - Checks for the latest version of GitHub Actions by querying the GitHub API.
    - Updates action references within files if a newer version is available.
    - Supports dry-run mode to preview changes without modifying files.
    - Creates backups of updated files in a 'backups' directory at the same level as the original file.
    - Allows specifying custom file extensions and optional recursive scanning of subdirectories.
    - Rate limit handling for GitHub API requests, including automatic wait times when limits are exceeded.
    - Detailed logging options for verbose output.

Dependencies:
    - requests: For making HTTP requests to the GitHub API.
    - packaging.version: For reliable version comparison of GitHub Actions tags.
    - tabulate: For formatted console output of summary statistics.

Usage:
    Run the script from the command line and specify the folder path to scan, as well as any
    optional parameters. For example:

        python github_actions_updater.py --path /path/to/folder --github-token YOUR_GITHUB_TOKEN --recursive --verbose

    See '--help' for a full list of options.

Arguments:
    - --path (str): Path to the folder containing GitHub Actions files (default is current directory).
    - --github-token (str): GitHub personal access token to increase API rate limits.
    - --dry-run (bool): If specified, prints changes without modifying files.
    - --backup (bool): If specified, creates a backup of each file before updating.
    - --extensions (str): Comma-separated list of file extensions to check (default is 'yml,yaml').
    - --recursive (bool): If specified, recursively searches subdirectories.
    - --verbose (bool): If specified, prints detailed information about the update process.
"""

import os
import re
import shutil
import argparse
import time
import sys

from typing import Any, Dict, List, Optional, Tuple

import requests

from packaging import version  # For version comparison
from tabulate import tabulate

# Constants
GITHUB_TAGS_API_URL = "https://api.github.com/repos/{owner}/{repo}/tags"

# Global cache and rate-limiting flag
version_cache: Dict[Tuple[str, str], Tuple[str, str]] = {}
rate_limit_exceeded = False  # Flag to stop further requests if API rate limit is hit


def main() -> None:
    """Parse command-line arguments and initiates the action updating process."""
    parser = argparse.ArgumentParser(description="Update GitHub Actions in a folder to the latest version.")
    parser.add_argument("--path", default=".", help="Path to the folder containing GitHub Actions files. Default is current directory.")
    parser.add_argument("--github-token", help="GitHub personal access token for authenticated requests.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without modifying files.")
    parser.add_argument("--backup", action="store_true", help="Create a backup of each file before updating.")
    parser.add_argument("--extensions", default="yml,yaml", help="Comma-separated list of file extensions to check. Default is 'yml,yaml'.")
    parser.add_argument("--recursive", action="store_true", help="Recursively search for files in subdirectories.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed information about the update process.")

    args: argparse.Namespace = parser.parse_args()

    # Split extensions argument by comma and add dot prefix
    extensions: List[str] = [f".{ext.strip()}" for ext in args.extensions.split(",")]

    update_all_actions(
        folder_path=args.path,
        github_token=args.github_token,
        dry_run=args.dry_run,
        backup=args.backup,
        extensions=extensions,
        recursive=args.recursive,
        verbose=args.verbose
    )


def get_latest_version(owner: str, repo: str, github_token: Optional[str], verbose: bool) -> Optional[Tuple[str, str]]:
    """
    Fetch the latest version tag and corresponding SHA for a given GitHub repo.

    Arguments:
        owner (str): The owner of the GitHub repository.
        repo (str): The name of the GitHub repository.
        github_token (Optional[str]): GitHub personal access token for authenticated requests.
        verbose (bool): If True, prints detailed information.

    Returns:
        Optional[Tuple[str, str]]: The latest version tag and its commit SHA, or None if the request fails or is rate-limited.
    """
    if check_rate_limit(verbose):
        return None

    cached_result: Tuple[str] | None = get_cached_version(owner, repo)
    if cached_result:
        return cached_result

    response: requests.Response | None = execute_github_request(owner, repo, github_token)
    if response:
        return handle_version_response(response, owner, repo)

    return None


def check_rate_limit(verbose: bool) -> bool:
    """
    Check the global rate limit flag.

    Arguments:
        verbose (bool): If True, prints detailed information.

    Returns:
        bool: True if the rate limit flag is set, False otherwise.
    """
    if rate_limit_exceeded:
        if verbose:
            print("Skipping API request due to rate limit.")
        return True
    return False


def get_cached_version(owner: str, repo: str) -> Optional[Tuple[str, str]]:
    """
    Check if the latest version is available in the cache.

    Arguments:
        owner (str): The owner of the GitHub repository.
        repo (str): The name of the GitHub repository.

    Returns:
        Optional[Tuple[str, str]]: The cached version and SHA, or None if not cached.
    """
    return version_cache.get((owner, repo))


def execute_github_request(owner: str, repo: str, github_token: Optional[str]) -> Optional[requests.Response]:
    """
    Execute the HTTP request to GitHub to fetch the latest version information.

    Arguments:
        owner (str): The owner of the GitHub repository.
        repo (str): The name of the GitHub repository.
        github_token (Optional[str]): GitHub personal access token for authenticated requests.

    Returns:
        Optional[requests.Response]: The HTTP response object if the request is successful, None otherwise.
    """
    url: str = GITHUB_TAGS_API_URL.format(owner=owner, repo=repo)
    headers: Dict[str, str] = {"Authorization": f"token {github_token}"} if github_token else {}

    try:
        response: requests.Response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        handle_http_error(response, http_err, owner, repo)
    except requests.exceptions.ConnectionError:
        print("Network connection error. Please check your internet connection.")
    except requests.exceptions.Timeout:
        print(f"Request for {owner}/{repo} timed out. Retrying may be necessary.")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred during the request for {owner}/{repo}: {req_err}")

    return None


def handle_http_error(response: requests.Response, http_err: requests.exceptions.HTTPError, owner: str, repo: str) -> None:
    """
    Handle HTTP errors that occur during the GitHub request.

    Arguments:
        response (requests.Response): The HTTP response object.
        http_err (requests.exceptions.HTTPError): The HTTP error raised.
        owner (str): The owner of the GitHub repository.
        repo (str): The name of the GitHub repository.
    """
    if response.status_code == 401:
        print("Invalid GitHub token. Please provide a valid token and try again.")
        sys.exit(1)
    elif response.status_code == 403:
        handle_rate_limit(response)
    else:
        print(f"HTTP error occurred for {owner}/{repo}: {http_err}")


def handle_version_response(response: requests.Response, owner: str, repo: str) -> Optional[Tuple[str, str]]:
    """
    Handle the response from the GitHub API to extract the latest version information.

    Arguments:
        response (requests.Response): The response object from the GitHub API.
        owner (str): The owner of the GitHub repository.
        repo (str): The name of the GitHub repository.

    Returns:
        Optional[Tuple[str, str]]: The latest version tag and its commit SHA, or None if the request fails.
    """
    if response.status_code == 200:
        try:
            tags: Any = response.json()
            if tags:
                latest_version: Any = tags[0]['name']
                latest_sha: Any = tags[0]['commit']['sha']
                version_cache[(owner, repo)] = (latest_version, latest_sha)
                return latest_version, latest_sha
        except (ValueError, KeyError) as e:
            print(f"Error parsing the JSON response for {owner}/{repo}: {e}")
    return None


def handle_rate_limit(response: requests.Response) -> None:
    """
    Manage GitHub API rate-limiting by setting the global flag and optionally waiting for the reset time.

    Arguments:
        response (requests.Response): The response object containing rate limit information.
    """
    global rate_limit_exceeded
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

    if remaining == 0:
        wait_time: int = max(0, reset_time - int(time.time()))
        print(f"Rate limit exceeded. Waiting {wait_time} seconds until reset.")
        time.sleep(wait_time)
        rate_limit_exceeded = False  # Reset the flag after waiting
    else:
        rate_limit_exceeded = True
        print("Rate limit reached. Skipping further API calls until reset.")


def update_action_version(file_path: str, github_token: Optional[str], dry_run: bool, backup: bool, stats: Dict[str, int], verbose: bool) -> None:
    """
    Update the GitHub action versions in a specific file if newer versions are available.

    Arguments:
        file_path (str): The path to the file to be updated.
        github_token (Optional[str]): GitHub personal access token for authenticated requests.
        dry_run (bool): If True, only prints changes without modifying the files.
        backup (bool): If True, creates a backup before modifying the file.
        stats (Dict[str, int]): A dictionary for tracking the number of files and changes made.
        verbose (bool): If True, prints detailed information.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines: List[str] = file.readlines()

        updated_lines: List = []
        changed: bool = False
        changes_made: int = 0
        updated_line: str
        was_changed: bool

        for line in lines:
            updated_line, was_changed = process_line(line, github_token, dry_run, verbose)
            updated_lines.append(updated_line)
            if was_changed:
                changed = True
                changes_made += 1

        finalize_update(file_path, updated_lines, changed, changes_made, dry_run, backup, stats, verbose)

    except (IOError, OSError) as e:
        print(f"Error processing file {file_path}: {e}")


def process_line(line: str, github_token: Optional[str], dry_run: bool, verbose: bool) -> Tuple[str, bool]:
    """
    Check and potentially updates a line in the file that references a GitHub action.

    Arguments:
        line (str): A single line from the file being processed.
        github_token (Optional[str]): GitHub personal access token for authenticated requests.
        dry_run (bool): If True, only prints changes without modifying the line.
        verbose (bool): If True, prints detailed information.

    Returns:
        Tuple[str, bool]: The potentially updated line, and a boolean indicating whether an update was made.
    """
    owner: str | Any
    repo: str | Any
    current_sha: str | Any
    current_version: str | Any
    latest_version: str | Any
    latest_sha: str | Any

    match: re.Match[str] | None = re.search(r'uses:\s+([\w-]+)/([\w-]+)@([a-f0-9]+)\s+#\s*v?([\d.]+)', line)
    if not match:
        return line, False

    owner, repo, current_sha, current_version = match.groups()
    latest_version, latest_sha = get_latest_version(owner, repo, github_token, verbose)

    # Normalize the latest_version to ensure it does not include a 'v' prefix (case-insensitive)
    if latest_version and latest_version.lower().startswith('v'):
        latest_version = latest_version[1:]

    # Update only if there is a newer version available
    if latest_version and latest_sha and version.parse(latest_version) > version.parse(current_version):
        if verbose:
            print(f"Found update for {owner}/{repo}: {current_version} -> {latest_version}")
        if dry_run:
            print(f"[Dry Run] Would update {current_sha} -> {latest_sha} with version v{latest_version}")
        else:
            # Replace the hash and ensure the version comment has a single 'v' prefix
            line = re.sub(r'@([a-f0-9]+)', f'@{latest_sha}', line)
            line = re.sub(r'#\s*v?[\d.]+', f'# v{latest_version}', line)
        return line, True

    return line, False


def finalize_update(file_path: str, updated_lines: List[str], changed: bool, changes_made: int, dry_run: bool,
                    backup: bool, stats: Dict[str, int], verbose: bool) -> None:
    """
    Finalize the file update process, creating a backup if specified, and updating statistics.

    Arguments:
        file_path (str): The path to the file that was potentially updated.
        updated_lines (List[str]): The list of lines, updated if necessary.
        changed (bool): Indicates if any changes were made to the file.
        changes_made (int): The number of changes made in the file.
        dry_run (bool): If True, does not actually write changes to the file.
        backup (bool): If True, creates a backup before modifying the file.
        stats (Dict[str, int]): Dictionary to update with stats about files and changes.
        verbose (bool): If True, prints detailed information.
    """
    if changed:
        stats['files_updated'] += 1
        stats['total_changes'] += changes_made

        if not dry_run:
            if backup:
                create_backup(file_path, verbose)
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(updated_lines)
                    if verbose:
                        print(f"Updated file: {file_path}")
            except (IOError, OSError) as e:
                print(f"Error writing updated file {file_path}: {e}")


def create_backup(file_path: str, verbose: bool) -> None:
    """
    Create a backup of the specified file.

    Arguments:
        file_path (str): The path to the file for which to create a backup.
        verbose (bool): If True, prints detailed information.
    """
    try:
        backup_dir: str = os.path.join(os.path.dirname(file_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file_path: str = os.path.join(backup_dir, os.path.basename(file_path))
        shutil.copyfile(file_path, backup_file_path)
        if verbose:
            print(f"Backup created: {backup_file_path}")
    except (IOError, OSError) as e:
        print(f"Error creating backup for {file_path}: {e}")


def update_all_actions(folder_path: str, github_token: Optional[str], dry_run: bool, backup: bool, extensions: List[str],
                       recursive: bool, verbose: bool) -> None:
    """
    Orchestrate the process of updating GitHub actions in all files within the specified folder and its subdirectories.

    Arguments:
        folder_path (str): The root directory to search for action files.
        github_token (Optional[str]): GitHub personal access token for authenticated requests.
        dry_run (bool): If True, only prints changes without modifying files.
        backup (bool): If True, creates a backup before updating.
        extensions (List[str]): List of file extensions to include.
        recursive (bool): If True, recursively searches subdirectories.
        verbose (bool): If True, prints detailed information.
    """
    stats: Dict[str, int] = {'total_files': 0, 'files_updated': 0, 'total_changes': 0}

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = sorted([d for d in dirs if d != "backups"])
        if not recursive:
            dirs.clear()

        for filename in sorted(files):
            if any(filename.endswith(ext) for ext in extensions):
                file_path: str = os.path.join(root, filename)
                if verbose:
                    print(f"Checking file: {file_path}")
                stats['total_files'] += 1
                update_action_version(file_path, github_token, dry_run, backup, stats, verbose)

    print_summary(stats)


def print_summary(stats: Dict[str, int]) -> None:
    """
    Print a summary of the script's actions, including the number of files scanned, updated, and total changes made.

    Arguments:
        stats (Dict[str, int]): Dictionary containing stats about total files, updated files, and changes made.
    """
    print("\nSummary Statistics")
    print(tabulate([
        ["Total Files Scanned", stats['total_files']],
        ["Total Files Updated", stats['files_updated']],
        ["Total Changes Made", stats['total_changes']]
    ], headers=["Statistic", "Count"], tablefmt="grid"))


if __name__ == "__main__":
    main()
