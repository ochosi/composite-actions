#!/usr/bin/python3

"""Step interactively through the release process for osbuild"""

# Requires: pip install ghapi (https://ghapi.fast.ai/)

import argparse
import contextlib
import subprocess
import sys
import os
import getpass
import time
from datetime import date
import yaml
from ghapi.all import GhApi


class fg:  # pylint: disable=too-few-public-methods
    """Set of constants to print colored output in the terminal"""
    BOLD = '\033[1m'  # bold
    OK = '\033[32m'  # green
    INFO = '\033[33m'  # yellow
    ERROR = '\033[31m'  # red
    RESET = '\033[0m'  # reset


def msg_error(body):
    """Print error and exit"""
    print(f"{fg.ERROR}{fg.BOLD}Error:{fg.RESET} {body}")
    sys.exit(1)


def msg_info(body):
    """Print info message"""
    print(f"{fg.INFO}{fg.BOLD}Info:{fg.RESET} {body}")


def msg_ok(body):
    """Print ok status message"""
    print(f"{fg.OK}{fg.BOLD}OK:{fg.RESET} {body}")


def run_command(argv):
    """Run a shellcommand and return stdout"""
    result = subprocess.run(  # pylint: disable=subprocess-run-check
        argv,
        capture_output=True,
        text=True,
        encoding='utf-8').stdout
    return result.strip()


def autoincrement_version(latest_tag):
    """Bump the version of the latest git tag by 1"""
    if latest_tag == "":
        msg_info("There are no tags yet in this repository.")
        version = "1"
    elif "." in latest_tag:
        version = latest_tag.replace("v", "").split(".")[0] + "." + str(int(latest_tag[-1]) + 1)
    else:
        version = int(latest_tag.replace("v", "")) + 1
    return version


def list_prs_for_hash(args, api, repo, commit_hash):
    """Get pull request for a given commit hash"""
    query = f'{commit_hash} type:pr is:merged base:{args.base} repo:osbuild/{repo}'
    try:
        res = api.search.issues_and_pull_requests(q=query, per_page=20)
    except:
        msg_info(f"Couldn't get PR infos for {commit_hash}.")
        res = None

    if res is not None:
        items = res["items"]

        if len(items) == 1:
            ret = items[0]
        else:
            msg_info(f"There are {len(items)} pull requests associated with {commit_hash} - skipping...")
            for item in items:
                msg_info(f"{item.html_url}")
            ret = None
    else:
        ret = None

    return ret


def get_pullrequest_infos(args, repo, hashes):
    """Fetch the titles of all related pull requests"""
    api = GhApi(repo=repo, owner='ochosi', token=args.token)
    summaries = []
    i = 0

    for commit_hash in hashes:
        i += 1
        print(f"Fetching PR {i}")
        time.sleep(2)
        pull_request = list_prs_for_hash(args, api, repo, commit_hash)
        if pull_request is not None:
            if repo == "cockpit-composer":
                msg = f"- {pull_request.title} (#{pull_request.number})"
            else:
                msg = f"  * {pull_request.title} (#{pull_request.number})"
        summaries.append(msg)

    summaries = list(dict.fromkeys(summaries))
    msg_ok(f"Collected summaries from {len(summaries)} pull requests ({i} commits).")
    return "\n".join(summaries)


def get_contributors(args):
    """Collect all contributors to a release based on the git history"""
    contributors = run_command(["git", "log", '--format="%an"', f"{args.latest_tag}..HEAD"])
    contributor_list = contributors.replace('"', '').split("\n")
    names = ""
    for name in sorted(set(contributor_list)):
        if name != "":
            names += f"{name}, "

    return names[:-2]


def create_release_tag(args, repo, tag):
    """Create a release tag"""
    today = date.today()
    contributors = get_contributors(args)

    summaries = ""
    hashes = run_command(['git', 'log', '--format=%H', f'{args.latest_tag}..HEAD']).split("\n")
    msg_info(f"Found {len(hashes)} commits since {args.latest_tag} in {args.base}:")
    print("\n".join(hashes))
    summaries = get_pullrequest_infos(args, repo, hashes)

    if repo == "cockpit-composer":
        tag = str(args.version)
        message = (f"{args.version}:\n\n"
               f"{summaries}\n")
    else:
        tag = f'v{args.version}'
        message = (f"CHANGES WITH {args.version}:\n\n"
                f"----------------\n"
                f"{summaries}\n\n"
                f"Contributions from: {contributors}\n\n"
                f"— Somewhere on the internet, {today.strftime('%Y-%m-%d')}")

    subprocess.call(['git', 'tag', '-s', '-m', message, tag, 'HEAD'])


def print_config(args, repo):
    """Print the values used for the release playbook"""
    print("\n--------------------------------\n"
          f"{fg.BOLD}Release:{fg.RESET}\n"
          f"  Component:     {repo}\n"
          f"  Version:       {args.version}\n"
          f"  Base branch:   {args.base}\n"
          f"{fg.BOLD}GitHub{fg.RESET}:\n"
          f"  User:          {args.user}\n"
          f"  Token:         {bool(args.token)}\n"
          f"--------------------------------\n")


def main():
    """Main function"""
    # Get some basic fallback/default values
    repo = os.path.basename(os.getcwd())
    latest_tag = run_command(['git', 'describe', '--tags', '--abbrev=0'])
    version = autoincrement_version(latest_tag)
    username = getpass.getuser()

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version",
                        help=f"Set the version for the release (Default: {version})",
                        default=version)
    parser.add_argument("-c", "--component",
                        help=f"Set the component for the release (Default: {repo})",
                        default=repo)
    parser.add_argument("-u", "--user", help=f"Set the username on GitHub (Default: {username})",
                        default=username)
    parser.add_argument("-t", "--token", help=f"Set the GitHub token")
    parser.add_argument(
        "-b", "--base",
        help=f"Set the base branch that the release targets (Default: 'main')",
        default='main')

    args = parser.parse_args()

    args.latest_tag = latest_tag

    if args.token is None:
        msg_error("Please supply a valid GitHub token.")

    print_config(args, repo)

    # Create a release tag
    if repo == "cockpit-composer":
        tag = str(args.version)
    else:
        tag = f'v{args.version}'
    create_release_tag(args, repo, tag)

    subprocess.call(['git', 'push', 'origin', tag])
    msg_ok(f"Pushed tag '{tag}' to branch '{args.base}'")


if __name__ == "__main__":
    main()
