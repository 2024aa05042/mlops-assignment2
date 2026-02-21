# GitHub Secrets Configuration

## Quick Setup for CD Deployment

This guide shows how to configure GitHub Secrets for automatic deployment.

### 📋 Required Secrets for GitHub Actions Deployment

#### Option 1: Deploy to cloud K8s (AWS EKS, GCP GKE, Azure AKS)

1. **Generate Service Account with Deploy Role**

   ```bash
   # 1. Create namespace
   kubectl create namespace github-actions
   
   # 2. Create service account
   kubectl create serviceaccount github-cd -n github-actions
   
   # 3. Create role for deployment updates
   kubectl create role deploy-cats-dogs \
     --verb=get,list,watch,create,update,patch,delete \
     --resource=deployments,pods,replicasets \
     -n github-actions
   
   # 4. Bind role to service account
   kubectl create rolebinding github-cd-deploy \
     --role=deploy-cats-dogs \
     --serviceaccount=github-actions:github-cd \
     -n github-actions
   ```

2. **Get Kubeconfig**

   ```bash
   # Get token
   TOKEN=$(kubectl create token github-cd -n github-actions)
   
   # Get API server
   API_SERVER=$(kubectl cluster-info | grep 'Kubernetes master' | cut -d' ' -f7)
   
   # Get CA certificate
   CA_CERT=$(kubectl config view --raw --flatten \
     -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
   
   # Create kubeconfig
   cat > /tmp/github-kube.conf <<EOF
   apiVersion: v1
   kind: Config
   clusters:
   - name: production
     cluster:
       server: ${API_SERVER}
       certificate-authority-data: ${CA_CERT}
   contexts:
   - name: github-cd
     context:
       cluster: production
       namespace: github-actions
       user: github-cd-user
   current-context: github-cd
   users:
   - name: github-cd-user
     user:
       token: ${TOKEN}
   EOF
   ```

3. **Encode Kubeconfig for GitHub**

   ```bash
   # Linux/Mac
   cat /tmp/github-kube.conf | base64 -w0 > /tmp/kubeconfig.b64
   
   # Windows PowerShell
   [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes(
     (Get-Content /tmp/github-kube.conf -Raw)
   )) | Set-Clipboard
   ```

4. **Add to GitHub Secrets**

   - Go to: GitHub Repo → Settings → Secrets and variables → Actions
   - Click: "New repository secret"
   - Name: `KUBECONFIG`
   - Value: [Paste base64 output]
   - Click: "Add secret"

#### Option 2: Docker Hub Push (Optional)

1. **Get Docker Hub Token**
   
   ```bash
   # Go to: Docker Hub → Account Settings → Security → Access Tokens
   # Create new token: `github-actions-push`
   # Copy token (won't be shown again)
   ```

2. **Add to GitHub Secrets**

   - Secret 1:
     - Name: `DOCKER_USERNAME`
     - Value: `your-docker-username`
   
   - Secret 2:
     - Name: `DOCKER_PASSWORD`
     - Value: [Docker Hub token]

#### Option 3: Argo CD (For Argo CD workflow)

1. **Get Argo CD Credentials**

   ```bash
   # If Argo CD installed, get admin password
   kubectl -n argocd get secret argocd-initial-admin-secret \
     -o jsonpath='{.data.password}' | base64 -d
   
   # Get Argo CD server URL
   kubectl -n argocd get svc argocd-server
   ```

2. **Add to GitHub Secrets**

   - Secret 1:
     - Name: `ARGOCD_SERVER`
     - Value: `https://your-argocd-server:6443`
   
   - Secret 2:
     - Name: `ARGOCD_TOKEN`
     - Value: [Generated token from `argocd account generate-token`]

#### Option 4: Slack Notifications (Optional)

1. **Create Slack Webhook**

   - Go to: Slack Workspace → Apps → Create New App
   - Name: "GitHub Deployment Notifier"
   - Select workspace and channel
   - Copy Webhook URL

2. **Add to GitHub Secrets**

   - Name: `SLACK_WEBHOOK`
   - Value: [Slack Webhook URL]

---

## 🔍 Verify Secrets Are Set

```bash
# List secrets (values hidden)
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/actions/secrets | jq '.secrets[].name'

# Expected output:
# KUBECONFIG
# DOCKER_USERNAME
# DOCKER_PASSWORD
# ARGOCD_SERVER
# ARGOCD_TOKEN
# SLACK_WEBHOOK
```

---

## ✅ Test Deployment

```bash
# Make a small code change
git checkout -b test-cd
echo "# Test CD" >> README.md
git add README.md
git commit -m "test: trigger CD pipeline"
git push origin test-cd

# Create pull request and merge to main
# Watch: GitHub Actions → deploy job running

# Verify pod updated
kubectl get pods -l app=cats-dogs-api -o wide
kubectl logs deployment/cats-dogs-api
```

---

## 🔒 Security Considerations

### ✅ DO

- ✅ Use separate service accounts for GitHub Actions
- ✅ Grant minimal required RBAC permissions
- ✅ Rotate tokens regularly
- ✅ Use GitHub Environment Secrets for prod/staging separation
- ✅ Enable branch protection rules

### ❌ DON'T

- ❌ Never commit kubeconfig to repository
- ❌ Don't use admin credentials for GitHub Actions
- ❌ Never use root/system service account
- ❌ Don't store credentials in environment variables

---

## 🛠️ Environment-Specific Secrets

For production vs staging deployments:

1. **Create Environments** in GitHub:
   - Settings → Environments → New environment
   - Create `staging` and `production` envs

2. **Add Environment Secrets**:
   - Each environment can have its own secrets
   - Set different `KUBECONFIG` for each

3. **Update Workflow** to use environment:
   ```yaml
   deploy:
     environment: production  # or staging
     secrets: inherit
   ```

---

## 📊 Secrets Checklist

### Minimal Setup (GitHub Actions only)
- [ ] `KUBECONFIG` (base64-encoded)

### Full Setup (with Docker Hub push)
- [ ] `KUBECONFIG`
- [ ] `DOCKER_USERNAME`
- [ ] `DOCKER_PASSWORD`

### Production Setup (with Argo CD)
- [ ] `KUBECONFIG`
- [ ] `DOCKER_USERNAME`
- [ ] `DOCKER_PASSWORD`
- [ ] `ARGOCD_SERVER`
- [ ] `ARGOCD_TOKEN`
- [ ] `SLACK_WEBHOOK` (optional)

---

## 🆘 Troubleshooting

### "Deployment not triggered"
- Check: Are secrets visible in Actions tab? (No - they're masked)
- Check: Did code push to `main` branch?
- Check: GitHub Actions enabled in Settings?

### "Kubeconfig error: credentials not valid"
- Verify: Token hasn't expired
- Verify: Base64 encoding is correct: `echo $KUBE_CONFIG | base64 -d | head`
- Verify: Service account has correct RBAC

### "Cannot access registry"
- Verify: Docker credentials correct
- Verify: Registry token hasn't expired
- Check: Is repository private? (May need pull secret in k8s)

---

## 📚 References

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Kubernetes Service Accounts](https://kubernetes.io/docs/concepts/configuration/secret/)
- [kubectl auth](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/)
