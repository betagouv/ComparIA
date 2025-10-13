import os
from getpass import getpass
from pathlib import Path

# cache_dir = input("Indicate path to all Hugging Face caches:")
cache_dir = "cache"
os.environ["HF_DATASETS_CACHE"] = cache_dir
os.environ["HF_HUB_CACHE"] = cache_dir
try:
    os.environ["HF_TOKEN"]
except:
    os.environ["HF_TOKEN"] = getpass(f"HuggingFace token (puis presser Entrée):\n")

from rank_comparia.pipeline import RankingPipeline

pipeline = RankingPipeline(
    method="elo_random",
    include_votes=True,
    include_reactions=True,
    bootstrap_samples=1000,
    mean_how="token",
    export_path=Path("output"),
)

# ranker = pipeline.ranker
scores = pipeline.run()
