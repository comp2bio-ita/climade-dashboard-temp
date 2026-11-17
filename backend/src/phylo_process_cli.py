#!/usr/bin/env python3

import argparse
import os
import signal
import subprocess
import sys
import time
import shutil

from pathlib import Path


PYTHON = shutil.which("python")

if PYTHON is None:
    raise RuntimeError("Could not find 'python' in PATH")

MODULE = "phylo_module.pipeline_phylo"

BASE_DIR = Path.cwd()
PID_FILE = BASE_DIR / "pipeline_phylo.pid"
LOG_FILE = BASE_DIR / "pipeline.log"
ERR_FILE = BASE_DIR / "pipeline.err"


def read_pid():
    """Read the stored pipeline PID."""
    if not PID_FILE.exists():
        return None

    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def process_exists(pid):
    """Check whether a process exists."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def get_status(pid):
    """Return ps output for the given PID."""
    result = subprocess.run(
        [
            "ps",
            "-p",
            str(pid),
            "-o",
            "pid,%cpu,%mem,etime,stat,cmd",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    lines = result.stdout.strip().splitlines()

    if len(lines) < 2:
        return None

    return "\n".join(lines)


def status():
    """Print the current pipeline status."""
    pid = read_pid()

    if pid is None:
        print("┌─────────────────────────────────────────────┐")
        print("│ Pipeline status: NOT RUNNING                │")
        print("└─────────────────────────────────────────────┘")

        if PID_FILE.exists():
            PID_FILE.unlink()

        return 1

    ps_output = get_status(pid)

    if ps_output is None:
        print("┌─────────────────────────────────────────────┐")
        print("│ Pipeline status: NOT RUNNING                │")
        print("└─────────────────────────────────────────────┘")
        return 1

    print("┌─────────────────────────────────────────────┐")
    print("│ Pipeline status: RUNNING                    │")
    print("└─────────────────────────────────────────────┘")
    print()
    print(ps_output)

    return 0


# def run(input_file):
def run():
    """Start the phylo pipeline with nohup."""
    existing_pid = read_pid()

    if existing_pid and get_status(existing_pid):
        print(f"Pipeline is already running (PID {existing_pid}).")
        return 1

    # Remove stale PID file.
    if PID_FILE.exists():
        PID_FILE.unlink()

    print(f"Starting phylo pipeline...")
    print(f"Module : {MODULE}")
    print(f"Log   : {LOG_FILE}")

    # Open the log file. stderr is intentionally discarded, matching
    # the original command: 2>/dev/null
    log_file = open(LOG_FILE, "a")
    err_file = open(ERR_FILE, "a")

    process = subprocess.Popen(
        [
            PYTHON,
            "-m",
            MODULE,
            # input_file,
        ],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=err_file,
        start_new_session=True,
    )

    print(process)

    PID_FILE.write_text(str(process.pid))

    # Give the process a moment to start.
    time.sleep(0.5)

    if process_exists(process.pid):
        print()
        print(f"✓ Pipeline started successfully (PID {process.pid})")
        print(f"  Log: {LOG_FILE}")
        print()
        return status()

    print("✗ Pipeline failed to start.")
    return 1


def stop():
    """Stop the running pipeline."""
    pid = read_pid()

    if pid is None:
        print("Pipeline is not running.")
        return 1

    if not process_exists(pid):
        print(f"Pipeline process {pid} is no longer running.")
        PID_FILE.unlink(missing_ok=True)
        return 1

    print(f"Stopping pipeline (PID {pid})...")

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        print("Pipeline was already stopped.")
        return 0

    # Wait briefly for graceful termination.
    for _ in range(20):
        if not process_exists(pid):
            PID_FILE.unlink(missing_ok=True)
            print("✓ Pipeline stopped.")
            return 0

        time.sleep(0.25)

    # Force kill if it did not respond to SIGTERM.
    print("Pipeline did not stop gracefully; sending SIGKILL.")

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    PID_FILE.unlink(missing_ok=True)
    print("✓ Pipeline killed.")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline_phylo_cli.py",
        description=(
            "Command-line interface for running and managing "
            "the phylo_module.pipeline_phylo pipeline."
        ),
        epilog="""
Examples:

  Start a pipeline:
    python pipeline_phylo_cli.py run input.nc

  Check pipeline status:
    python pipeline_phylo_cli.py status

  Stop the running pipeline:
    python pipeline_phylo_cli.py stop

  Show this manual:
    python pipeline_phylo_cli.py -h

Files:

  pipeline.log
      Pipeline standard output.

  pipeline_phylo.pid
      PID of the currently running pipeline.

Notes:

  The pipeline is started as a detached process. Standard output is
  written to pipeline.log and standard error is discarded.

  The status command uses:

    ps -p PID -o pid,%cpu,%mem,etime,stat,cmd
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="COMMAND",
    )

    # run
    run_parser = subparsers.add_parser(
        "run",
        help="Start the phylo pipeline.",
    )

    # run_parser.add_argument(
    #     "input",
    #     default="pipeline_phylo.py",
    #     required=False,
    #     help="Input argument/file passed to pipeline_phylo.",
    # )

    # status
    subparsers.add_parser(
        "status",
        help="Show the current pipeline status.",
    )

    # stop
    subparsers.add_parser(
        "stop",
        help="Stop the running phylo pipeline.",
    )

    args = parser.parse_args()

    if args.command == "run":
        # return run(args.input)
        return run()

    if args.command == "status":
        return status()

    if args.command == "stop":
        return stop()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())