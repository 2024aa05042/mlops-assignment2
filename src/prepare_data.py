"""Prepare Cats vs Dogs dataset into ImageFolder train/val/test layout.

Expected input: folder with images named like `cat.0.jpg` and `dog.0.jpg` (Kaggle format).
Output: `output_dir/train/cat`, `output_dir/train/dog`, `output_dir/val/cat`, `output_dir/test/dog`, etc.
"""
import os
import shutil
import random
from pathlib import Path


def prepare(raw_dir, output_dir, val_frac=0.1, test_frac=0.1, seed=42):
    """Split images into train/val/test folders per class.

    Defaults to 80% train / 10% val / 10% test when val_frac=0.1 and test_frac=0.1.
    """
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    train_dir = Path(output_dir) / "train"
    val_dir = Path(output_dir) / "val"
    test_dir = Path(output_dir) / "test"
    for d in [train_dir, val_dir, test_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # collect files by class directories if present, otherwise fall back to filename prefixes
    classes = {}
    raw_path = Path(raw_dir)

    # helper to gather image files from a folder
    def _images_in(folder):
        imgs = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
            imgs.extend(list(folder.glob(ext)))
        return imgs

    # 1) check immediate subdirectories of raw_path for images
    found = False
    for child in raw_path.iterdir():
        if child.is_dir():
            imgs = _images_in(child)
            if imgs:
                classes[child.name.lower()] = imgs
                found = True

    # 2) if none found at depth 1, check depth 2 (e.g., PetImages/Cat)
    if not found:
        for child in raw_path.iterdir():
            if child.is_dir():
                for sub in child.iterdir():
                    if sub.is_dir():
                        imgs = _images_in(sub)
                        if imgs:
                            classes[sub.name.lower()] = imgs
                            found = True

    # 3) fallback: filenames indicate class prefix (cat.*, dog.*)
    if not found:
        for p in raw_path.glob("*"):
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                name = p.name.lower()
                if name.startswith("cat"):
                    classes.setdefault("cat", []).append(p)
                elif name.startswith("dog"):
                    classes.setdefault("dog", []).append(p)

    if not classes:
        raise RuntimeError(f"No images found in raw directory: {raw_dir}")

    for cls, files in classes.items():
        random.shuffle(files)
        n_total = len(files)
        n_test = int(n_total * test_frac)
        n_val = int(n_total * val_frac)
        # ensure at least one in train if counts small
        n_train = max(n_total - n_val - n_test, 0)
        val_files = files[:n_val]
        test_files = files[n_val:n_val + n_test]
        train_files = files[n_val + n_test:]

        target_train = train_dir / cls
        target_val = val_dir / cls
        target_test = test_dir / cls
        target_train.mkdir(parents=True, exist_ok=True)
        target_val.mkdir(parents=True, exist_ok=True)
        target_test.mkdir(parents=True, exist_ok=True)

        for f in train_files:
            shutil.copy(f, target_train / f.name)
        for f in val_files:
            shutil.copy(f, target_val / f.name)
        for f in test_files:
            shutil.copy(f, target_test / f.name)


def _discover_raw_dir(provided_raw_dir=None):
    """Resolve dataset input directory. If `provided_raw_dir` is not given, use the repository `data/` folder.

    Accepts absolute paths as well. Returns a Path object pointing to the folder containing images
    or nested class folders.
    """
    if provided_raw_dir:
        p = Path(provided_raw_dir)
        if p.exists():
            return p
        # try relative to repo
        p = Path(__file__).resolve().parents[1] / provided_raw_dir
        if p.exists():
            return p
        raise FileNotFoundError(f"Provided raw data directory not found: {provided_raw_dir}")

    # default: repo root `data/` folder
    repo_root = Path(__file__).resolve().parents[1]
    default = repo_root / "data"
    if default.exists():
        return default
    # as a fallback, allow absolute /data (unix-like) if present
    abs_data = Path("/data")
    if abs_data.exists():
        return abs_data
    raise FileNotFoundError("No raw data directory found. Provide --raw-dir or create a `data/` folder in the repo.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=str, default=None, help="Input data folder (defaults to ./data/ in repo)")
    parser.add_argument("--out-dir", type=str, default="data/processed")
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--test-frac", type=float, default=0.1)
    args = parser.parse_args()
    raw_path = _discover_raw_dir(args.raw_dir)
    print(f"Preparing data from: {raw_path}")
    prepare(raw_path, args.out_dir, args.val_frac, args.test_frac)
