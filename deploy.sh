#!/bin/bash

# Deployment script for WinkAI to winkai.in
# Run this script from your local machine

SERVER_IP="64.227.139.236"
SERVER_USER="root"
DOMAIN="winkai.in"

echo "🚀 Deploying WinkAI Frontend to $DOMAIN..."

# Step 1: Upload the tar file
echo "📦 Uploading build files..."
scp frontend/wink-frontend-dist.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

# Step 2: SSH into server and set up
echo "🔧 Setting up server..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
set -e

echo "📍 Installing required packages..."
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

echo "📁 Creating web directory..."
mkdir -p /var/www/winkai
cd /var/www/winkai

echo "📦 Extracting files..."
tar -xzf /tmp/wink-frontend-dist.tar.gz -C /var/www/winkai/
rm /tmp/wink-frontend-dist.tar.gz

echo "🔐 Setting permissions..."
chown -R www-data:www-data /var/www/winkai
chmod -R 755 /var/www/winkai

echo "⚙️ Configuring Nginx..."
cat > /etc/nginx/sites-available/winkai.in << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name winkai.in www.winkai.in;

    root /var/www/winkai;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/winkai.in /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Restart nginx
systemctl restart nginx
systemctl enable nginx

echo "✅ Deployment complete!"
echo "🌐 Your site should be accessible at http://winkai.in"
echo ""
echo "🔒 To enable HTTPS, run:"
echo "   certbot --nginx -d winkai.in -d www.winkai.in"
ENDSSH

echo ""
echo "✨ Deployment successful!"
echo "🌐 Visit: http://winkai.in"
echo ""
echo "Next steps:"
echo "1. Make sure your domain winkai.in points to $SERVER_IP"
echo "2. Run SSL setup: ssh $SERVER_USER@$SERVER_IP 'certbot --nginx -d winkai.in -d www.winkai.in'"

<system-reminder>
Background Bash 7cf9fa (command: cd "/Users/mrityunjaygupta/Downloads/winkfinal-main 4/frontend" && VITE_API_URL="/mock" npm run dev) (status: running) Has new output available. You can check its output using the BashOutput tool.
</system-reminder>

<system-reminder>
Background Bash 33f258 (command: cd "/Users/mrityunjaygupta/Downloads/winkfinal-main 4/frontend" && VITE_API_URL="/mock" npm run dev) (status: running) Has new output available. You can check its output using the BashOutput tool.
</system-reminder>