import sys
from pathlib import Path

# Ensure repository root is on sys.path for pytest so tests can import `src` package
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
