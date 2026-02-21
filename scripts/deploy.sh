#!/bin/bash
set -e

# Deployment Helper Script for Cats vs Dogs API
# Usage: ./scripts/deploy.sh [prod|staging|local] [image-tag]

ENVIRONMENT=${1:-local}
IMAGE_TAG=${2:-latest}
REGISTRY=${DOCKER_REGISTRY:-ghcr.io}
USERNAME=${GITHUB_ACTOR:-your-username}
IMAGE="${REGISTRY}/${USERNAME}/cats-dogs:${IMAGE_TAG}"
NAMESPACE="default"
DEPLOYMENT_NAME="cats-dogs-api"

echo "🚀 Deploying Cats vs Dogs API"
echo "Environment: $ENVIRONMENT"
echo "Image: $IMAGE"
echo "Namespace: $NAMESPACE"

# Function: Deploy to Kubernetes
deploy_kubernetes() {
  echo "📦 Deploying to Kubernetes ($ENVIRONMENT)..."
  
  # Update image in deployment
  kubectl set image deployment/${DEPLOYMENT_NAME} \
    ${DEPLOYMENT_NAME}=${IMAGE} \
    --record \
    -n ${NAMESPACE} || true
  
  # Trigger rollout
  kubectl rollout restart deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE}
  
  # Wait for rollout
  echo "⏳ Waiting for rollout to complete..."
  kubectl rollout status deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE} --timeout=5m
  
  # Show status
  echo "✅ Deployment complete!"
  kubectl get deployment ${DEPLOYMENT_NAME} -n ${NAMESPACE}
  kubectl get pods -n ${NAMESPACE} -l app=cats-dogs-api
}

# Function: Deploy with Kustomize
deploy_kustomize() {
  echo "🔧 Deploying with Kustomize..."
  
  # Update image in kustomization.yaml
  cd k8s
  kustomize edit set image cats-dogs-api=${IMAGE}
  cd ..
  
  # Apply kustomized resources
  kubectl apply -k k8s/
  
  # Wait for rollout
  kubectl rollout status deployment/${DEPLOYMENT_NAME} -n ${NAMESPACE} --timeout=5m
  
  echo "✅ Kustomize deployment complete!"
}

# Function: Deploy with Argo CD
deploy_argocd() {
  echo "🔄 Syncing Argo CD application..."
  
  # Check if argocd CLI is available
  if ! command -v argocd &> /dev/null; then
    echo "❌ argocd CLI not found. Install with: curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
    exit 1
  fi
  
  # Sync application
  argocd app sync cats-dogs-app --prune
  
  # Wait for sync
  argocd app wait cats-dogs-app --sync
  
  echo "✅ Argo CD sync complete!"
}

# Function: Verify deployment
verify_deployment() {
  echo "🔍 Verifying deployment..."
  
  # Check pod status
  READY_PODS=$(kubectl get deployment ${DEPLOYMENT_NAME} -n ${NAMESPACE} -o jsonpath='{.status.readyReplicas}')
  DESIRED_PODS=$(kubectl get deployment ${DEPLOYMENT_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}')
  
  if [ "$READY_PODS" == "$DESIRED_PODS" ]; then
    echo "✅ All pods are ready ($READY_PODS/$DESIRED_PODS)"
    
    # Port-forward for quick test
    POD_NAME=$(kubectl get po -n ${NAMESPACE} -l app=cats-dogs-api -o jsonpath='{.items[0].metadata.name}')
    echo "📝 To test the API:"
    echo "   kubectl port-forward pod/${POD_NAME} 8000:8000 -n ${NAMESPACE}"
    echo "   curl http://localhost:8000/health"
  else
    echo "⚠️  Pods not ready yet ($READY_PODS/$DESIRED_PODS)"
    kubectl get pods -n ${NAMESPACE} -l app=cats-dogs-api
    exit 1
  fi
}

# Function: Run smoke tests
run_smoke_tests() {
  echo "🧪 Running smoke tests..."
  
  # Check if Python and requests are available
  if ! command -v python3 &> /dev/null; then
    echo "⚠️  Python3 not found, skipping smoke tests"
    return 0
  fi
  
  # Install requests if needed
  python3 -m pip install requests -q 2>/dev/null || true
  
  # Setup port forwarding in background
  echo "Setting up port forwarding..."
  kubectl port-forward -n ${NAMESPACE} svc/${DEPLOYMENT_NAME} 8001:8000 > /dev/null 2>&1 &
  PORT_FORWARD_PID=$!
  
  # Wait for port forward to establish
  sleep 2
  
  # Run smoke tests
  if [ -f "tests/smoke_test.py" ]; then
    echo "Running Python smoke tests..."
    if python3 tests/smoke_test.py http://localhost:8001 --max-retries 20 --retry-delay 1; then
      echo "✅ Smoke tests passed!"
      SMOKE_TEST_RESULT=0
    else
      echo "❌ Smoke tests failed!"
      SMOKE_TEST_RESULT=1
    fi
  elif [ -f "scripts/smoke-test.sh" ]; then
    echo "Running bash smoke tests..."
    if bash scripts/smoke-test.sh http://localhost:8001 20 1; then
      echo "✅ Smoke tests passed!"
      SMOKE_TEST_RESULT=0
    else
      echo "❌ Smoke tests failed!"
      SMOKE_TEST_RESULT=1
    fi
  else
    echo "⚠️  Smoke test script not found, skipping"
    SMOKE_TEST_RESULT=0
  fi
  
  # Clean up port forwarding
  kill $PORT_FORWARD_PID 2>/dev/null || true
  wait $PORT_FORWARD_PID 2>/dev/null || true
  
  return $SMOKE_TEST_RESULT
}

# Main deployment logic
case $ENVIRONMENT in
  local)
    deploy_kubernetes
    ;;
  staging|prod)
    if command -v argocd &> /dev/null; then
      deploy_argocd
    else
      deploy_kustomize
    fi
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Usage: $0 [local|staging|prod] [image-tag]"
    exit 1
    ;;
esac

verify_deployment

# Run smoke tests
run_smoke_tests
if [ $? -ne 0 ]; then
  echo "❌ Deployment failed - smoke tests did not pass"
  exit 1
fi

echo "🎉 Deployment successful!"
