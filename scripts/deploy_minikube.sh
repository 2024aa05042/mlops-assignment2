#!/usr/bin/env bash
set -euo pipefail

IMAGE=cats-dogs-api:latest
DOCKERFILE=Dockerfile.api
K8S_DIR=k8s

echo "Building Docker image: $IMAGE"
docker build -t $IMAGE -f $DOCKERFILE .

echo "Ensuring minikube is running..."
if ! minikube status >/dev/null 2>&1; then
  echo "Starting minikube..."
  minikube start
fi

# Ensure host data directory exists and mount it into minikube
REPO_ROOT="$(pwd)"
HOST_DATA_DIR="${REPO_ROOT}/data"
if [ ! -d "$HOST_DATA_DIR" ]; then
  echo "Creating host data dir: $HOST_DATA_DIR"
  mkdir -p "$HOST_DATA_DIR"
fi

# Print a PowerShell-friendly command (Windows users should run this in pwsh)
if command -v cygpath >/dev/null 2>&1; then
  PS_PATH="$(cygpath -w "$HOST_DATA_DIR")"
else
  PS_PATH="$HOST_DATA_DIR"
fi
echo "PowerShell mount command (run in an elevated pwsh window if needed):"
echo "  minikube mount \"${PS_PATH}:/minikube-host/data\""

# Try to start mount in background (for bash environments). Logs at /tmp/minikube-mount.log
echo "Starting minikube mount in background (bash): ${HOST_DATA_DIR} -> /minikube-host/data"
nohup minikube mount "${HOST_DATA_DIR}:/minikube-host/data" >/tmp/minikube-mount.log 2>&1 &
MOUNT_PID=$!
sleep 1
if ps -p ${MOUNT_PID} >/dev/null 2>&1; then
  echo "minikube mount started with PID ${MOUNT_PID} (logs: /tmp/minikube-mount.log)"
else
  echo "Failed to start minikube mount in background. Run the PowerShell command shown above in a separate shell."
fi

echo "Loading image into minikube"
minikube image load $IMAGE

echo "Applying Kubernetes manifests"
kubectl apply -f ${K8S_DIR}/deployment.yaml
kubectl apply -f ${K8S_DIR}/service.yaml

echo "Deployment applied. Getting service URL (minikube)"
if command -v minikube >/dev/null 2>&1; then
  minikube service cats-dogs-api --url || true
else
  echo "Use kubectl to get NodePort and access the service on the cluster nodes."
fi

echo "Done."
