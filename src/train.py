import os
import argparse
import time
from pathlib import Path
import sys

# Ensure repository root is on sys.path so `from src...` imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mlflow
import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

from src.data import get_dataloaders
from src.model import create_model


def _save_model(model, path, fmt="pth", sample_input=None, device=None):
    """Save model in different formats.

    fmt: 'pth' -> state_dict (default), 'pt' -> full model via torch.save, 'onnx' -> ONNX export (requires sample_input)
    """
    path = str(path)
    if fmt == "pth":
        torch.save(model.state_dict(), path)
    elif fmt == "pt":
        torch.save(model, path)
    elif fmt == "onnx":
        if sample_input is None:
            raise ValueError("ONNX export requires a sample_input tensor")
        model.eval()
        sample = sample_input.to(device) if device is not None else sample_input
        torch.onnx.export(model, sample, path, opset_version=11)
    else:
        raise ValueError(f"Unsupported save format: {fmt}")


def _load_best_model(model, path, fmt="pth", device=None):
    """Load a saved model into `model` or return loaded model for fmt 'pt'.
    Returns the model (may be a new object for 'pt').
    """
    if fmt == "pth":
        model.load_state_dict(torch.load(path, map_location=device))
        return model
    elif fmt == "pt":
        loaded = torch.load(path, map_location=device)
        if isinstance(loaded, torch.nn.Module):
            return loaded
        # fallback: assume state_dict
        model.load_state_dict(loaded)
        return model
    else:
        # ONNX not loadable back into PyTorch here
        raise ValueError("Loading ONNX into PyTorch not supported by this helper")
def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    for inputs, labels in loader:
        inputs = inputs.to(device)
        labels = labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * inputs.size(0)
        _, preds = outputs.max(1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)
    return running_loss / total, correct / total


def eval_epoch(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            running_loss += loss.item() * inputs.size(0)
            _, preds = outputs.max(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return running_loss / total, correct / total


def main(args):
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(args.experiment_name)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, test_loader, classes = get_dataloaders(args.data_dir, args.batch_size, args.img_size)

    # Verify data folders exist and log counts
    def _count(loader):
        if loader is None:
            return 0
        try:
            return len(loader.dataset)
        except Exception:
            # fallback: iterate quickly
            cnt = 0
            for _batch in loader:
                cnt += _batch[0].size(0) if isinstance(_batch, tuple) and hasattr(_batch[0], 'size') else 0
            return cnt

    n_train = _count(train_loader)
    n_val = _count(val_loader)
    n_test = _count(test_loader)
    print(f"Data sizes - train: {n_train}, val: {n_val}, test: {n_test}")


    model = create_model(num_classes=max(2, len(classes)))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    with mlflow.start_run(run_name=args.run_name):
        mlflow.log_params({
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "img_size": args.img_size,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
        })

        best_acc = 0.0
        for epoch in range(1, args.epochs + 1):
            t0 = time.time()
            train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc = eval_epoch(model, val_loader, criterion, device)
            epoch_time = time.time() - t0
            mlflow.log_metrics({
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "epoch_time": epoch_time,
            }, step=epoch)
            print(f"Epoch {epoch}/{args.epochs} - train_acc: {train_acc:.4f} val_acc: {val_acc:.4f} time: {epoch_time:.1f}s")

            # save best (format-aware)
            if val_acc > best_acc:
                best_acc = val_acc
                out_dir = args.output_dir
                os.makedirs(out_dir, exist_ok=True)
                if args.save_format == "pth":
                    fname = "best_model.pth"
                elif args.save_format == "pt":
                    fname = "best_model.pt"
                elif args.save_format == "onnx":
                    fname = "best_model.onnx"
                else:
                    fname = f"best_model.{args.save_format}"
                model_path = os.path.join(out_dir, fname)
                # prepare sample input for ONNX export if needed
                sample_input = None
                if args.save_format == "onnx":
                    sample_input = torch.randn(1, 3, args.img_size, args.img_size)
                _save_model(model, model_path, fmt=args.save_format, sample_input=sample_input, device=device)
                mlflow.log_artifact(model_path, artifact_path="model")

        # log class names and save mapping
        mlflow.log_param("classes", ",".join(classes))
        try:
            os.makedirs(args.output_dir, exist_ok=True)
            cls_path = os.path.join(args.output_dir, "classes.txt")
            with open(cls_path, "w") as f:
                for c in classes:
                    f.write(f"{c}\n")
            mlflow.log_artifact(cls_path, artifact_path="model")
        except Exception:
            pass

        # If test set exists, evaluate best model on test and log
        if test_loader is not None:
            if args.save_format == "pth":
                best_model_path = os.path.join(args.output_dir, "best_model.pth")
            elif args.save_format == "pt":
                best_model_path = os.path.join(args.output_dir, "best_model.pt")
            elif args.save_format == "onnx":
                best_model_path = os.path.join(args.output_dir, "best_model.onnx")
            else:
                best_model_path = os.path.join(args.output_dir, f"best_model.{args.save_format}")

            if os.path.exists(best_model_path):
                try:
                    model = _load_best_model(model, best_model_path, fmt=args.save_format, device=device)
                    model = model.to(device)
                    test_loss, test_acc = eval_epoch(model, test_loader, criterion, device)
                    mlflow.log_metric("test_loss", test_loss)
                    mlflow.log_metric("test_acc", test_acc)
                    print(f"Test - loss: {test_loss:.4f} acc: {test_acc:.4f}")
                except ValueError:
                    print("Best model is in a non-PyTorch format (e.g. ONNX); skipping PyTorch test eval.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data/processed", help="Path to processed data (ImageFolder) or folder to split")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--output-dir", type=str, default="artifacts")
    parser.add_argument("--mlflow-uri", type=str, default="file:./mlruns")
    parser.add_argument("--experiment-name", type=str, default="cats-dogs")
    parser.add_argument("--run-name", type=str, default="run")
    parser.add_argument("--save-format", type=str, choices=["pth", "pt", "onnx"], default="pth", help="Format to save the best model: pth (state_dict), pt (full torch), onnx")
    args = parser.parse_args()
    main(args)
