# Cats vs Dogs MLOps Pipeline

Baseline MLOps project for binary image classification (Cats vs Dogs).

Quick start:

1. Download the Kaggle Cats vs Dogs dataset and extract images into `data/raw/`.
   - You can use `scripts/prepare_data.py --raw-dir data/raw --out-dir data/processed` to prepare `data/processed/train` and `data/processed/val` folders.

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Train locally with mlflow tracking:

```bash
python src/train.py --data-dir data/processed --epochs 5 --batch-size 32
```

4. Build Docker image:

```bash
docker build -t cats-dogs:latest .
```

CI/CD: a GitHub Actions workflow is included at `.github/workflows/ci.yml` to run a simple check and build the Docker image. To push images to DockerHub configure `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets.

Files of interest:
- `src/train.py` — training script that logs to MLflow and saves the best model
- `src/data.py` — data loaders and preprocessing
- `src/model.py` — model factory (ResNet18 backbone)
- `scripts/prepare_data.py` — prepare ImageFolder layout from Kaggle filenames
- `Dockerfile` — containerize training
