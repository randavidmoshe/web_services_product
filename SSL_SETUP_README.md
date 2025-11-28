# SSL/HTTPS Setup Guide

## Quick Start (Development)

### 1. Generate Self-Signed Certificates

```bash
chmod +x generate-certs.sh
./generate-certs.sh
```

This creates:
- `nginx/certs/server.crt`
- `nginx/certs/server.key`

### 2. Create Required Directories

```bash
mkdir -p nginx/certs nginx/certbot
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access Points

| Service | URL |
|---------|-----|
| Web App | https://localhost |
| API | https://localhost/api/ |
| API Direct (debug) | http://localhost:8001 |

### 5. Update Agent

Your agent needs to either:

**Option A: Skip verification (development only)**
```python
import urllib3
urllib3.disable_warnings()
response = requests.get(url, verify=False)
```

**Option B: Trust the certificate**
```python
response = requests.get(url, verify='/path/to/nginx/certs/server.crt')
```

---

## Production Setup (Let's Encrypt)

### 1. Point DNS to Your Server

Create A records:
- `api.quathera.com` → Your server IP
- `app.quathera.com` → Your server IP

### 2. Get Let's Encrypt Certificates

```bash
# Install certbot
sudo apt install certbot

# Get certificate (run on server with ports 80/443 open)
sudo certbot certonly --standalone -d api.quathera.com -d app.quathera.com
```

### 3. Copy Certificates

```bash
# Certificates are in /etc/letsencrypt/live/api.quathera.com/
sudo cp /etc/letsencrypt/live/api.quathera.com/fullchain.pem nginx/certs/server.crt
sudo cp /etc/letsencrypt/live/api.quathera.com/privkey.pem nginx/certs/server.key
```

### 4. Update nginx.conf

Change `server_name localhost` to your actual domain:
```nginx
server_name api.quathera.com;
```

### 5. Auto-Renewal

Add cron job for certificate renewal:
```bash
0 0 1 * * certbot renew && cp /etc/letsencrypt/live/api.quathera.com/*.pem /path/to/nginx/certs/ && docker-compose restart nginx
```

---

## File Structure

```
web_services_product/
├── docker-compose.yml        # Updated with Nginx service
├── generate-certs.sh         # Certificate generation script
├── nginx/
│   ├── nginx.conf           # Nginx configuration
│   ├── certs/
│   │   ├── server.crt       # SSL certificate
│   │   └── server.key       # Private key
│   └── certbot/             # Let's Encrypt challenge folder
├── api-server/
├── web-app/
└── ...
```

---

## Troubleshooting

### Certificate Errors in Browser
Expected with self-signed certs. Click "Advanced" → "Proceed" or add exception.

### Agent Connection Refused
1. Check Nginx is running: `docker-compose ps`
2. Check logs: `docker-compose logs nginx`
3. Verify agent uses `https://` not `http://`

### 502 Bad Gateway
API server not ready yet. Check: `docker-compose logs api-server`
