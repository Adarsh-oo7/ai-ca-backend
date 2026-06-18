#!/bin/bash

# Study Commander AI — Production VPS Deployment Script
# Targets: Ubuntu/Debian Linux VPS with Docker installed.

set -e

# Styling colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}         STUDY COMMANDER AI DEPLOYMENT MANAGER          ${NC}"
echo -e "${GREEN}=======================================================${NC}"

# 1. Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}[ERROR] .env file not found in current directory!${NC}"
    echo -e "${YELLOW}Please create one using .env.example template.${NC}"
    exit 1
fi

# 2. Export environment variables
export $(grep -v '^#' .env | xargs)

# Required validations
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}[ERROR] GEMINI_API_KEY is not defined in .env!${NC}"
    exit 1
fi

if [ -z "$STUDENT_EMAIL" ] || [ -z "$STUDENT_PASSWORD" ]; then
    echo -e "${YELLOW}[WARNING] STUDENT_EMAIL or STUDENT_PASSWORD is empty. Seeding student user will be skipped.${NC}"
fi

# 3. Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker is not installed on this VPS!${NC}"
    echo -e "${YELLOW}Please install Docker using: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose is not installed on this VPS!${NC}"
    exit 1
fi

# Define docker compose command format (modern syntax vs old)
DC="docker compose"
if ! docker compose version &> /dev/null; then
    DC="docker-compose"
fi

# 4. Compile Nginx production config from template
echo -e "${GREEN}==> Compiling Nginx production config from template...${NC}"
TARGET_DOMAIN=${DOMAIN_NAME:-localhost}
sed "s/\${DOMAIN_NAME}/$TARGET_DOMAIN/g" nginx/nginx.prod.conf.template > nginx/nginx.prod.conf

# 5. Pull and build containers
echo -e "${GREEN}==> Building production Docker images...${NC}"
$DC -f docker-compose.prod.yml build

# 6. Bring up services except Nginx (nginx requires SSL cert folder initially)
echo -e "${GREEN}==> Spinning up backend, database, and cache worker services...${NC}"
$DC -f docker-compose.prod.yml up -d db redis backend celery_worker

# 7. Database Migrations & Assets Compilation
echo -e "${GREEN}==> Executing Django migrations...${NC}"
$DC -f docker-compose.prod.yml exec backend python manage.py migrate --noinput

echo -e "${GREEN}==> Collecting Django static assets...${NC}"
$DC -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

echo -e "${GREEN}==> Seeding CA Foundation student account...${NC}"
$DC -f docker-compose.prod.yml exec backend python manage.py seed_student

echo -e "${GREEN}==> Seeding CA Foundation syllabus curriculum...${NC}"
$DC -f docker-compose.prod.yml exec backend python manage.py seed_curriculum

# 8. Setup SSL & Nginx
if [ "$TARGET_DOMAIN" != "localhost" ] && [ -n "$DOMAIN_NAME" ]; then
    echo -e "${GREEN}==> Setup SSL Certificates and starting Nginx...${NC}"
    chmod +x scripts/ssl-setup.sh
    ./scripts/ssl-setup.sh
else
    echo -e "${YELLOW}==> DOMAIN_NAME is localhost or empty. Skipping Let's Encrypt certificate flow...${NC}"
    echo -e "${GREEN}==> Starting local Nginx container...${NC}"
    # Create self-signed fake certificates so local nginx starts up cleanly
    mkdir -p "nginx/ssl/live/$TARGET_DOMAIN"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "nginx/ssl/live/$TARGET_DOMAIN/privkey.pem" \
        -out "nginx/ssl/live/$TARGET_DOMAIN/fullchain.pem" \
        -subj "/CN=localhost" || true
    
    $DC -f docker-compose.prod.yml up -d nginx
fi

echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}     STUDY COMMANDER AI DEPLOYED SUCCESSFUL!           ${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo -e "Access link: ${YELLOW}https://${DOMAIN_NAME:-localhost}${NC}"
echo -e "API admin path: ${YELLOW}https://${DOMAIN_NAME:-localhost}/admin/${NC}"
echo -e "Student Email: ${YELLOW}${STUDENT_EMAIL}${NC}"
echo -e "Spaced repetition scheduler and prediction calc is online."
