#!/bin/bash

# Study Commander AI — SSL Setup Script
# Assumes running on Ubuntu VPS.

set -e

# Colors for feedback
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==> Initializing Study Commander AI SSL Setup...${NC}"

# Read DOMAIN_NAME from .env in parent folder
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}[ERROR] .env file not found. Please create .env first.${NC}"
    exit 1
fi

if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}[ERROR] DOMAIN_NAME is not set in .env.${NC}"
    exit 1
fi

if [ -z "$NOTIFICATION_EMAIL" ]; then
    echo -e "${RED}[ERROR] NOTIFICATION_EMAIL (or email preference) is not set in .env. Certbot needs this for updates.${NC}"
    exit 1
fi

echo -e "${GREEN}==> Domain targeted: $DOMAIN_NAME${NC}"
echo -e "${GREEN}==> Email targeted: $NOTIFICATION_EMAIL${NC}"

# Check if certs already exist and are valid (not self-signed placeholders)
if [ -f "nginx/ssl/live/$DOMAIN_NAME/fullchain.pem" ]; then
    if openssl x509 -in "nginx/ssl/live/$DOMAIN_NAME/fullchain.pem" -text -noout | grep -q "localhost"; then
        echo -e "${GREEN}==> Self-signed placeholder certificate detected. Proceeding to obtain real Let's Encrypt certificates...${NC}"
    else
        echo -e "${GREEN}==> SSL certificates already exist. Skipping renewal setup...${NC}"
        exit 0
    fi
fi

# Create directory structures
mkdir -p nginx/ssl
mkdir -p nginx/acme-challenge

# 1. Compile Nginx production config from template
echo -e "${GREEN}==> Compiling Nginx production config from template...${NC}"
sed "s/\${DOMAIN_NAME}/$DOMAIN_NAME/g" nginx/nginx.prod.conf.template > nginx/nginx.prod.conf

# 1.5. Create a placeholder SSL certificate so Nginx can start up initially
echo -e "${GREEN}==> Creating self-signed temporary SSL certificate for bootstrapping Nginx...${NC}"
mkdir -p "nginx/ssl/live/$DOMAIN_NAME"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "nginx/ssl/live/$DOMAIN_NAME/privkey.pem" \
    -out "nginx/ssl/live/$DOMAIN_NAME/fullchain.pem" \
    -subj "/CN=localhost" || true

# 2. Boot up Nginx container (along with other services) to serve the ACME challenge
echo -e "${GREEN}==> Starting Docker containers...${NC}"
docker compose -f docker-compose.prod.yml up --build -d nginx
sleep 5

# 3. Request actual certificates from Let's Encrypt
echo -e "${GREEN}==> Requesting certificate from Let's Encrypt using Certbot...${NC}"
rm -rf "nginx/ssl/live/$DOMAIN_NAME"
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot \
    --email $NOTIFICATION_EMAIL \
    -d $DOMAIN_NAME \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    --force-renewal

echo -e "${GREEN}==> Certificates successfully obtained. Reloading Nginx...${NC}"
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 4. Create Cron Job for automatic renewal
echo -e "${GREEN}==> Registering automatic SSL renewal cron jobs...${NC}"
(crontab -l 2>/dev/null; echo "0 12 * * * docker compose -f $(pwd)/docker-compose.prod.yml run --rm certbot renew --webroot -w /var/www/certbot --quiet && docker compose -f $(pwd)/docker-compose.prod.yml exec nginx nginx -s reload") | crontab -

echo -e "${GREEN}==> SSL setup completed successfully!${NC}"
