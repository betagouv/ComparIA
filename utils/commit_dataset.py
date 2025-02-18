import asyncio
from tqdm import tqdm
import pandas as pd

import logging as logger
import sys
import os
import subprocess
import os
import shutil
from datetime import datetime

logger.basicConfig(
            level=logger.INFO)

def commit_datasets():
    

    # Git operations (keep your existing code)
    repos = ['comparia-preferences', 'comparia-questions', 'comparia-samples']
    for repo in repos:

        repo_path = os.path.join("../languia-data", repo)
        if not os.path.exists(repo_path):
            logger.error(f"Repository directory not found: {repo_path}")
            continue
        result = subprocess.run(['git', '-C', repo_path, 'pull'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully pulled latest changes for {repo}")
        else:
            logger.error(f"Failed to pull changes for {repo}: {result.stderr}")


    # Define table to repository mappings
    table_repos = {
        'votes': 'comparia-preferences',
        'reactions': 'comparia-preferences',
        'questions': 'comparia-questions',
        'questions_only': 'comparia-questions'
    }

    dataset_dir = 'datasets'
    if not os.path.exists(dataset_dir):
        logger.error(f"Dataset directory {dataset_dir} does not exist. No files to copy.")
        return

    # Copy exported files to respective repositories
    for filename in os.listdir(dataset_dir):
        src_path = os.path.join(dataset_dir, filename)
        if not os.path.isfile(src_path):
            continue

        # Determine destination repositories
        if '_samples' in filename:
            base_name = filename.split('_samples')[0]
            is_sample = True
        else:
            base_name = os.path.splitext(filename)[0]
            is_sample = False

        main_repo = table_repos.get(base_name)
        destinations = []

        if main_repo:
            if not is_sample:
                destinations.append(main_repo)
            else:
                destinations.append(main_repo)
                destinations.append('comparia-samples')
        else:
            if is_sample:
                destinations.append('comparia-samples')

        # Copy to each destination
        for dest_repo in destinations:
            dest_path = os.path.join("../languia-data", dest_repo, filename)
            try:
                shutil.copy(src_path, dest_path)
                logger.info(f"Copied {filename} to {dest_repo}")
            except Exception as e:
                logger.error(f"Failed to copy {filename} to {dest_repo}: {e}")

    # Commit and push changes for each repository
    for repo in repos:
        repo_path = os.path.join("../languia-data", repo)
        if not os.path.exists(repo_path):
            continue

        # Check for changes
        status_result = subprocess.run(['git', '-C', repo_path, 'status', '--porcelain'], capture_output=True, text=True)
        if status_result.returncode != 0:
            logger.error(f"Failed to check status for {repo}: {status_result.stderr}")
            continue

        if status_result.stdout.strip():
            # Add all changes
            add_result = subprocess.run(['git', '-C', repo_path, 'add', '.'])
            if add_result.returncode != 0:
                logger.error(f"Failed to add changes in {repo}")
                continue

            # Commit
            commit_message = f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            commit_result = subprocess.run(['git', '-C', repo_path, 'commit', '-m', commit_message])
            if commit_result.returncode != 0:
                logger.error(f"Failed to commit changes in {repo}: {commit_result.stderr}")
                continue

            # Push
            logger.info(f"Would run: git -C {repo_path} push")
            # push_result = subprocess.run(['git', '-C', repo_path, 'push'])
            # if push_result.returncode == 0:
            #     logger.info(f"Successfully pushed changes for {repo}")
            # else:
            #     logger.error(f"Failed to push changes for {repo}: {push_result.stderr}")
        else:
            logger.info(f"No changes to commit in {repo}")



if __name__ == "__main__":
    commit_datasets()