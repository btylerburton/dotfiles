#!/usr/bin/env python3
"""
Traverse all directories from a root parent, run `git pull` on every
git repository found, and report which ones errored out and why.

Features:
  - Parallel execution across repos
  - --dry-run to just list what would be pulled
  - Logging to a file (in addition to the console)

Usage:
    python git_pull_all.py [root_dir] [options]

Examples:
    python git_pull_all.py
    python git_pull_all.py /path/to/root
    python git_pull_all.py /path/to/root --workers 8
    python git_pull_all.py /path/to/root --dry-run
    python git_pull_all.py /path/to/root --log pull.log --recurse-nested
"""

import os
import sys
import argparse
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


# --------------------------------------------------------------------------- #
# Logging setup
# --------------------------------------------------------------------------- #
def setup_logging(log_file=None):
    """Configure logging to console and (optionally) a file."""
    logger = logging.getLogger("git_pull_all")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # avoid duplicate handlers on re-runs

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


# --------------------------------------------------------------------------- #
# Repo discovery
# --------------------------------------------------------------------------- #
def find_git_repos(root, recurse_nested=False):
    """Yield paths of directories containing a .git folder."""
    for dirpath, dirnames, _ in os.walk(root):
        if ".git" in dirnames:
            yield dirpath
            # Never descend into the .git folder itself
            dirnames.remove(".git")
            # By default, don't recurse into subdirs of a found repo
            if not recurse_nested:
                dirnames[:] = []


# --------------------------------------------------------------------------- #
# Git pull
# --------------------------------------------------------------------------- #
def git_pull(repo_path, timeout=300):
    """
    Run `git pull` in repo_path.
    Returns (repo_path, success: bool, message: str).
    """
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return repo_path, False, "git executable not found on PATH"
    except subprocess.TimeoutExpired:
        return repo_path, False, f"git pull timed out after {timeout}s"
    except Exception as e:  # catch-all for unexpected issues
        return repo_path, False, f"unexpected error: {e}"

    if result.returncode == 0:
        return repo_path, True, result.stdout.strip()
    else:
        reason = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return repo_path, False, reason


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(
        description="Run `git pull` on every git repo under a root directory."
    )
    parser.add_argument(
        "root", nargs="?", default=os.getcwd(),
        help="Root directory to scan (default: current working directory)."
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=4,
        help="Number of parallel workers (default: 4)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only list the repositories that would be pulled; don't pull."
    )
    parser.add_argument(
        "--log", metavar="FILE", default=None,
        help="Also write output to this log file."
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Per-repo timeout in seconds (default: 300)."
    )
    parser.add_argument(
        "--recurse-nested", action="store_true",
        help="Also pull nested repos/submodules found inside a repo."
    )
    return parser.parse_args()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    args = parse_args()
    logger = setup_logging(args.log)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        logger.error(f"'{root}' is not a valid directory.")
        sys.exit(1)

    logger.info(f"Scanning for git repositories under: {root}")

    repos = list(find_git_repos(root, recurse_nested=args.recurse_nested))
    logger.info(f"Found {len(repos)} repositor{'y' if len(repos) == 1 else 'ies'}.")

    # ---- Dry run ----
    if args.dry_run:
        logger.info("Dry run - the following repos would be pulled:")
        for repo in repos:
            logger.info(f"  {repo}")
        sys.exit(0)

    if not repos:
        logger.info("Nothing to do.")
        sys.exit(0)

    successes = []
    failures = []

    # ---- Parallel pulls ----
    logger.info(f"Pulling with {args.workers} worker(s)...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_repo = {
            executor.submit(git_pull, repo, args.timeout): repo
            for repo in repos
        }
        for future in as_completed(future_to_repo):
            repo, ok, message = future.result()
            if ok:
                logger.info(f"OK      {repo}")
                successes.append(repo)
            else:
                logger.error(f"FAILED  {repo}")
                for line in message.splitlines():
                    logger.error(f"          {line}")
                failures.append((repo, message))

    # ---- Report ----
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total repos processed: {len(successes) + len(failures)}")
    logger.info(f"Succeeded: {len(successes)}")
    logger.info(f"Failed:    {len(failures)}")

    if failures:
        logger.info("Errored repositories:")
        for repo, message in failures:
            logger.info(f"  {repo}")
            for line in message.splitlines():
                logger.info(f"      {line}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()