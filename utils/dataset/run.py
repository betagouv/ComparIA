import argparse
import logging
import os
import subprocess

from utils.logger import configure_logger
from utils.utils import UTILS_DIR

from .compute import DATASET_CONFIG, count_dataset_rows, process_dataset

logger = configure_logger(logging.getLogger("dataset.export"))


def main():
    """
    Main entry point for dataset export script.

    Args (via command line):
        export_base_path: directory for export (positional, default: ".")
        dataset: specific dataset to export (positional, optional)
        --dry-run: skip HuggingFace upload (optional)

    Examples:
        python export_dataset.py ./exports conversations
        python export_dataset.py --dry-run
        python export_dataset.py ./exports --dry-run
    """
    parser = argparse.ArgumentParser(
        description="Export ComparIA datasets from PostgreSQL to HuggingFace Hub"
    )
    parser.add_argument(
        "export_base_path",
        nargs="?",
        type=str,
        default=UTILS_DIR / "local_dataset",
        help="Directory for local export (default: utils/local_dataset)",
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=str,
        default=None,
        help="Specific dataset to export (conversations, votes, reactions, conversations_raw). Default: all",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip HuggingFace upload (only export to utils/local_dataset/)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Display row counts for each dataset without exporting",
    )

    args = parser.parse_args()

    # If --count flag is set, display counts and exit
    if args.count:
        count_dataset_rows()
        return

    # Log spam detection info
    logger.info("Spam detection enabled for filtering dataset")

    # Authenticate with HuggingFace CLI (skip if dry_run)
    if not args.dry_run:
        logger.info("hf auth login --token $HF_PUSH_DATASET_KEY")

        _login_result = subprocess.run(
            args=[
                "hf",
                "auth",
                "login",
                "--token",
                os.getenv("HF_PUSH_DATASET_KEY", ""),
            ]
        )

        if _login_result.returncode == 0:
            logger.info("Logged in")
        else:
            logger.error(f"Failed to login: {_login_result.stderr}")
            return False
    else:
        logger.info("[DRY RUN] Skipping HuggingFace authentication")

    if args.dataset:
        logger.warning(f"only processing dataset: {args.dataset}")

    # Process each dataset (or just the specified one)
    try:
        for dataset_name, config in DATASET_CONFIG.items():
            if not args.dataset or args.dataset == dataset_name:
                process_dataset(
                    dataset_name, config, args.export_base_path, dry_run=args.dry_run
                )

        logger.info("Finished processing all datasets.")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Export interrupted by user (Ctrl+C)")
        return


if __name__ == "__main__":
    main()
