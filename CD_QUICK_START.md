# CD Quick Reference Card

## 🎯 Choose Your Deployment Method

### ⚡ Fastest: GitHub Actions (Automatic)
```bash
# 1. One-time setup:
# Go to GitHub repo → Settings → Secrets and variables → Actions
# Add new secret:
#   Name: KUBECONFIG
#   Value: [base64-encoded kubeconfig]

# 2. That's it! Push to main to deploy:
git commit -am "your changes"
git push origin main

# 3. Watch deployment:
# GitHub repo → Actions tab → ci workflow → deploy job
```

**Status**: ✅ Ready to use now!

---

### 🔄 Production: Argo CD (GitOps)
```bash
# 1. Install Argo CD (one-time):
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Create application:
kubectl apply -f k8s/argocd-application.yaml

# 3. Deploy by committing to git:
git push origin main  # Argo CD syncs automatically

# 4. Monitor:
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Login with: admin / $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)
```

**Status**: ✅ Ready to use now!

---

### 🛠️ Manual: Deploy Script
```bash
# Deploy immediately without waiting for GitHub Actions:
./scripts/deploy.sh local latest

# Or to staging:
./scripts/deploy.sh staging v1.0.0

# Or to production:
./scripts/deploy.sh prod latest
```

**Status**: ✅ Ready to use now!

---

### 💼 Enterprise: Jenkins
```bash
# 1. Install Jenkins (beyond scope of this guide)

# 2. Create new Pipeline job:
#   Repository URL: https://github.com/YOUR_USERNAME/YOUR_REPO
#   Build trigger: GitHub hook trigger
#   Pipeline script: from SCM (Jenkinsfile)

# 3. Create Jenkins credentials:
#   kubeconfig-prod
#   docker-registry (if Docker Hub)
#   github-container-registry (if GHCR)

# 4. Done! Builds automatically on push
```

**Status**: ✅ Jenkinsfile ready, requires Jenkins setup

---

## 📊 Quick Comparison

| Method | Speed | Complexity | GitOps | Cost |
|--------|-------|-----------|--------|------|
| GitHub Actions | ⚡⚡ 2-3 min | ⭐ | ❌ | Free |
| Argo CD | ⚡ 3-5 min | ⭐⭐ | ✅ | Free |
| Script | ⚡⚡⚡ 1 min | ⭐ | ❌ | Free |
| Jenkins | ⚡⚡ 2-3 min | ⭐⭐⭐ | ❌ | Free |

---

## 🚀 Get Started Now (5 minutes)

```bash
# 1. Get your kubeconfig
cat ~/.kube/config | base64 -w0

# 2. Add to GitHub Secrets
# Repo → Settings → Secrets and variables → Actions → New secret
#   Name: KUBECONFIG
#   Value: [paste base64 output]

# 3. Test it!
git commit -am "test: trigger CD"
git push origin main

# 4. Watch it deploy
# Repo → Actions → ci workflow → deploy job
```

---

## 🔍 Verify Deployment

```bash
# Check if pod updated
kubectl get pods -l app=cats-dogs-api -o wide

# Check deployment history
kubectl rollout history deployment/cats-dogs-api

# View logs
kubectl logs deployment/cats-dogs-api -f

# Test API
POD=$(kubectl get po -l app=cats-dogs-api -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward pod/$POD 8000:8000 &
curl http://localhost:8000/health
```

---

## 📚 Learn More

- **GitHub Actions**: `CD_DEPLOYMENT_GUIDE.md` (Option 1)
- **Argo CD**: `CD_DEPLOYMENT_GUIDE.md` (Option 2)
- **Setup**: `GITHUB_SECRETS_SETUP.md`
- **Script**: `scripts/deploy.sh --help`
- **Jenkins**: `Jenkinsfile`

---

## ❓ FAQs

**Q: Which should I use?**
> Start with GitHub Actions (simplest). Graduate to Argo CD when you need GitOps.

**Q: How often does it deploy?**
> Every push to `main` branch triggers a deployment.

**Q: How long does deployment take?**
> 2-3 minutes: tests (30s) + build (1m) + push (30s) + deploy (30s)

**Q: Can I rollback?**
> Yes: `kubectl rollout undo deployment/cats-dogs-api`

**Q: Is it secure?**
> Yes: credentials stored in GitHub Secrets (encrypted), RBAC enforced on cluster.

---

## ⚡ One-Line Setups

```bash
# GitHub Actions (requires kubeconfig in KUBECONFIG secret)
# After setup, deployment is automatic on every push to main

# Argo CD
kubectl apply -n argocd -f k8s/argocd-application.yaml && kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Manual deploy
./scripts/deploy.sh local latest
```

---

**Status**: Your pipeline is production-ready! 🎉
