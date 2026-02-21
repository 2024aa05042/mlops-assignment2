import os
import random
from torchvision import transforms, datasets
from torch.utils.data import DataLoader, random_split


def get_dataloaders(data_dir, batch_size=32, img_size=224, val_split=0.1, test_split=0.1, num_workers=4):
    """Return train, val, test dataloaders.

    Behavior:
    - If `data_dir` contains `train/`, `val/`, and `test/` subfolders, load them.
    - If it contains `train/` and `val/` only, load them and return `test_loader` as None.
    - If it's a single folder, split into train/val/test using `val_split` and `test_split`.
    """
    # training augmentations
    transform_train = transforms.Compose([
        transforms.RandomResizedCrop(img_size),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(0.2, 0.2, 0.2, 0.1),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    # validation / test: deterministic
    transform_eval = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_folder = os.path.join(data_dir, "train")
    val_folder = os.path.join(data_dir, "val")
    test_folder = os.path.join(data_dir, "test")

    if os.path.isdir(train_folder) and os.path.isdir(val_folder):
        train_ds = datasets.ImageFolder(train_folder, transform=transform_train)
        val_ds = datasets.ImageFolder(val_folder, transform=transform_eval)
        test_loader = None
        if os.path.isdir(test_folder):
            test_ds = datasets.ImageFolder(test_folder, transform=transform_eval)
            test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    else:
        # single folder: load and split into train/val/test
        full = datasets.ImageFolder(data_dir, transform=transform_train)
        n_total = len(full)
        n_test = int(n_total * test_split)
        n_val = int(n_total * val_split)
        n_train = max(n_total - n_val - n_test, 0)
        lengths = [n_train, n_val, n_test]
        # if any length is zero, adjust to avoid error
        if sum(lengths) == 0:
            raise ValueError("Dataset directory appears empty: %s" % data_dir)
        parts = random_split(full, lengths)
        train_ds = parts[0]
        val_ds = parts[1] if len(parts) > 1 else None
        test_ds = parts[2] if len(parts) > 2 else None
        # ensure eval transforms apply
        if val_ds is not None:
            val_ds.dataset.transform = transform_eval
        if test_ds is not None:
            test_ds.dataset.transform = transform_eval
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers) if test_ds is not None else None

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    # obtain classes
    try:
        classes = train_ds.dataset.classes
    except Exception:
        classes = train_ds.classes if hasattr(train_ds, 'classes') else []

    return train_loader, val_loader, test_loader, classes
