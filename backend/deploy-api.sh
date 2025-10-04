#!/bin/bash
#
# Deploy Wink Analytics API to production VPS
#

set -e

echo "=================================================="
echo "  Wink Analytics API - Production Deployment"
echo "=================================================="

# Configuration
VPS_USER="root"
VPS_HOST="64.227.139.236"
DEPLOY_PATH="/var/www/wink-api"
SERVICE_NAME="wink-api"

# Build and package
echo "📦 Packaging application..."
tar -czf wink-api.tar.gz \
    main.py \
    requirements.txt \
    alembic.ini \
    alembic/ \
    src/

# Upload to VPS
echo "📤 Uploading to VPS..."
scp -o StrictHostKeyChecking=no wink-api.tar.gz ${VPS_USER}@${VPS_HOST}:/tmp/

# Deploy on VPS
echo "🚀 Deploying on VPS..."
ssh -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
set -e

# Create deployment directory
mkdir -p /var/www/wink-api
cd /var/www/wink-api

# Extract application
rm -rf *
tar -xzf /tmp/wink-api.tar.gz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f .env ]; then
    cat > .env << EOF
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/wink
JWT_SECRET_KEY=$(openssl rand -hex 32)
DISABLE_CAMERA_PROCESSORS=true
OPENAI_API_KEY=
EOF
    echo "⚠️  Created .env file - UPDATE DATABASE_URL and other settings!"
fi

# Run database migrations
source .env
alembic upgrade head

echo "✓ Application deployed"
ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. SSH into VPS: ssh ${VPS_USER}@${VPS_HOST}"
echo "  2. Update /var/www/wink-api/.env with correct settings"
echo "  3. Run seed script: cd /var/www/wink-api && source venv/bin/activate && python seed_minimal.py"
echo "  4. Start service: systemctl restart ${SERVICE_NAME}"
echo ""
