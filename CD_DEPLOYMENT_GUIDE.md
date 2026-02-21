# Continuous Deployment (CD) Setup Guide

This document explains three approaches to automatically deploy your MLOps pipeline on main branch changes.

---

## 📋 Overview

| Approach | Complexity | GitOps | Auto-Sync | Best For |
|----------|-----------|--------|-----------|----------|
| **GitHub Actions** | ⭐ Low | ❌ No | ✅ Yes | Quick setup, small teams |
| **Argo CD** | ⭐⭐⭐ Medium | ✅ Yes | ✅ Yes | Production, compliance |
| **Deployment Script** | ⭐ Low | ❌ No | ⚠️ Manual | Local dev, testing |

---

## 🔧 Option 1: GitHub Actions (Recommended for Quick Start)

Automatically deploy on every push to `main` branch.

### Setup

1. **Add Docker Registry Credentials** to GitHub Secrets:
   - `DOCKER_USERNAME` (optional for DockerHub)
   - `DOCKER_PASSWORD` (optional for DockerHub)
   - `KUBECONFIG` (base64-encoded kubeconfig for your cluster)

2. **Generate Kubeconfig Secret**:
   ```bash
   # For cloud K8s (AWS EKS, GCP GKE, Azure AKS):
   cat ~/.kube/config | base64 -w0 > /tmp/kubeconfig.b64
   
   # For minikube:
   kubectl config view --raw | base64 -w0 > /tmp/kubeconfig.b64
   ```

3. **Add to GitHub Secrets**:
   - Go to: Settings → Secrets and variables → Actions
   - New Repository Secret: `KUBECONFIG` = [paste base64 output]

4. **Verify Workflow**:
   - File: `.github/workflows/ci.yml`
   - Deploy job runs after publish (if on main branch)

### How It Works

```
Code Push → Tests → Build Image → Push to Registry → Deploy to K8s
                                                              ↓
                                    kubectl set image + rollout
```

### Advantages
- ✅ No additional tools needed
- ✅ Works with any K8s cluster
- ✅ Built-in GitHub integration
- ✅ Easy to debug (logs visible in Actions tab)

### Limitations
- ❌ Not true GitOps (imperative, not declarative)
- ❌ Requires pushing kubeconfig to GitHub (security consideration)
- ❌ No drift detection if cluster modified manually

### Test It

```bash
# 1. Make a code change
echo "# Updated" >> README.md
git add .
git commit -m "Test CD: trigger deployment"
git push origin main

# 2. Watch deployment
# Go to: GitHub repo → Actions tab → Select latest workflow run
# View: deploy job logs in real-time
```

---

## 🎯 Option 2: Argo CD (Production GitOps Best Practice)

Declarative, Git-driven deployment with automatic drift detection.

### Installation

```bash
# 1. Install Argo CD in cluster
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Access Argo CD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Login: admin / $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)

# 3. Install argocd CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
```

### Setup

1. **Update Application Config**:
   Edit `k8s/argocd-application.yaml`:
   ```yaml
   source:
     repoURL: https://github.com/YOUR_USERNAME/YOUR_REPO
   ```

2. **Create Application**:
   ```bash
   kubectl apply -f k8s/argocd-application.yaml
   ```

3. **Verify**:
   ```bash
   argocd app get cats-dogs-app
   argocd app sync cats-dogs-app
   ```

### Update GitHub Actions to Notify Argo CD

Add to `.github/workflows/ci.yml` after publish job:
```yaml
  notify-argocd:
    needs: publish
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Trigger Argo CD sync
        run: |
          # Argo CD polls Git every 3 minutes by default
          echo "✅ New image pushed. Argo CD will sync automatically."
          echo "Monitor at: <ARGOCD_URL>/applications/cats-dogs-app"
```

### How It Works

```
Code Push → Tests → Build & Push Image → Commits new manifests
                                                      ↓
                                    Argo CD detects Git change (every 3 min)
                                                      ↓
                                    Auto-syncs to match Git state
```

### Advantages
- ✅ **True GitOps**: Git is single source of truth
- ✅ Detects and corrects cluster drift
- ✅ Automatic rollback to previous commit
- ✅ Declarative, repeatable deployments
- ✅ Multi-environment support (staging, prod)
- ✅ Built-in audit trail (who changed what, when)

### Limitations
- ⚠️  More infrastructure to maintain
- ⚠️  Requires Argo CD installed in cluster

### Bonus: Image Update Automation

Use **Renovate** or **Flux** to automatically update image tags in Git:

```bash
# Or manually update kustomization.yaml
cd k8s
kustomize edit set image cats-dogs-api=ghcr.io/user/cats-dogs:v1.2.3
git add kustomization.yaml
git commit -m "ci: update cats-dogs-api to v1.2.3"
git push
```

---

## 🚀 Option 3: Manual Deployment Script

For local development or manual control.

### Usage

```bash
# Deploy to local/minikube with latest image
./scripts/deploy.sh local latest

# Deploy to staging with specific tag
./scripts/deploy.sh staging v1.0.0

# Deploy to production with Argo CD
./scripts/deploy.sh prod latest
```

### Features
- ✅ Works offline
- ✅ Rollout status verification
- ✅ Automatic pod readiness check
- ✅ Supports kustomize, kubectl, Argo CD

---

## 🔄 Complete CI/CD Pipeline

Your final pipeline looks like:

```
┌─────────────────────────────────────────────────────────┐
│  Developer commits to main                              │
└────────────────┬────────────────────────────────────────┘
                 ↓
        ┌────────────────────┐
        │  GitHub Actions    │
        │  - Run tests       │
        │  - Lint code       │
        │  - Build Docker    │
        └────────┬───────────┘
                 ↓
        ┌────────────────────┐
        │  Push to Registry  │
        │  (Docker Hub/GHCR) │
        └────────┬───────────┘
                 ↓
    ┌───────────────────────────┐
    │  Option 1: Direct kubectl │ ──→ ✅ Deploy immediately
    │  Option 2: Notify Argo CD │ ──→ 🔄 Auto-sync from Git
    │  Option 3: Manual deploy  │ ──→ 📝 Manual trigger
    └───────────────────────────┘
                 ↓
        ┌────────────────────┐
        │  New Pod Starts    │
        │  Health checks ✅  │
        │  Ready to serve    │
        └────────────────────┘
```

---

## 📊 Deployment Comparison

### GitHub Actions + kubectl
```
Workflow trigger: Automatic on push
Deployment type: Imperative (kubectl commands)
Git integration: No (image tag is source)
Rollback: Manual (git revert + push)
Drift: Not detected
Time to deploy: 2-3 minutes
```

### Argo CD
```
Workflow trigger: Automatic on Git commit
Deployment type: Declarative (Git manifests)
Git integration: Yes (Git is truth)
Rollback: Automatic (sync to previous commit)
Drift: Auto-detected and fixed
Time to deploy: 3-5 minutes
```

### Manual Script
```
Workflow trigger: Human (./scripts/deploy.sh)
Deployment type: Imperative
Git integration: No
Rollback: Manual
Drift: Not detected
Time to deploy: 1 minute
```

---

## ✅ Testing Your CD Setup

### 1. Test GitHub Actions Deployment

```bash
# Make a code change that passes tests
echo "# Auto-deployed at $(date)" >> README.md
git add README.md
git commit -m "test: trigger CD deployment"
git push origin main

# Watch at: GitHub → Actions (see deploy job running)
```

### 2. Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=cats-dogs-api

# Check deployment history
kubectl rollout history deployment/cats-dogs-api

# Tail logs
kubectl logs -f deployment/cats-dogs-api
```

### 3. Test Rollback

```bash
# Git revert + push
git revert HEAD
git push

# Argo CD (if used) will automatically sync to previous version
argocd app sync cats-dogs-app
```

---

## 🛡️ Security Best Practices

1. **Never commit secrets**
   - Use GitHub Secrets for credentials
   - Use RBAC for k8s access

2. **Use read-only kubeconfig**
   ```bash
   kubectl create serviceaccount github-actions
   kubectl create clusterrole deploy-cats-dogs --verb=get,list,watch,create,update,patch,delete --resource=deployments
   kubectl create clusterrolebinding deploy-cats-dogs --clusterrole=deploy-cats-dogs --serviceaccount=default:github-actions
   ```

3. **Monitor deployments**
   - Enable audit logging in K8s
   - Set up alerts for deployment failures
   - Use network policies to restrict pod communication

---

## 🆘 Troubleshooting

### Deployment Not Triggering

- ✅ Check: Is code on `main` branch?
- ✅ Check: Did tests pass?
- ✅ Check: GitHub Actions tab for errors

### Kubeconfig Error

- ✅ Verify secret is base64-encoded correctly
- ✅ Ensure kubeconfig file has correct permissions
- ✅ Test with: `kubectl auth can-i create deployments`

### Argo CD Not Syncing

- ✅ Check Argo CD logs: `kubectl logs -f -n argocd deployment/argocd-controller-manager`
- ✅ Verify Git repo is accessible: `argocd repo list`
- ✅ Check image pull secrets configured

---

## 📚 Next Steps

1. ✅ Choose deployment method (GitHub Actions recommended for MVP)
2. ✅ Set up credentials (kubeconfig in GitHub Secrets)
3. ✅ Test on non-critical branch first
4. ✅ Monitor first few deployments
5. ✅ Graduate to Argo CD for production
6. ✅ Add notifications (Slack, email on deployment)

---

## 🔗 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Argo CD Getting Started](https://argo-cd.readthedocs.io/en/stable/getting_started/)
- [Kustomize Guide](https://kustomize.io/docs/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
