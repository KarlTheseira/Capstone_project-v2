#!/bin/bash
# Google Drive Secret Update Script
# Usage: ./update_gdrive_secret.sh "your-json-content" "your-folder-id"

echo "Updating Google Drive secrets..."

# Delete existing secret
kubectl delete secret google-drive-secrets -n flash

# Create new secret with your credentials
kubectl create secret generic google-drive-secrets \
  --from-literal=GOOGLE_DRIVE_CREDENTIALS_JSON="$1" \
  --from-literal=GOOGLE_DRIVE_FOLDER_ID="$2" \
  --namespace=flash

echo "Secret updated! Restarting deployment..."

# Restart the deployment to pick up new secrets
kubectl rollout restart deployment/flashstudio-monolith -n flash

echo "Deployment restarted. Waiting for pods to be ready..."
kubectl rollout status deployment/flashstudio-monolith -n flash

echo "✅ Google Drive integration is ready!"
echo "📱 Access admin interface at: http://4.144.240.181/admin/gdrive-videos"
