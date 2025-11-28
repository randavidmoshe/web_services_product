#!/bin/bash

# =============================================================================
# Generate Self-Signed SSL Certificates for Development
# =============================================================================
# For production, replace these with Let's Encrypt certificates:
#   1. Point api.quathera.com to your server
#   2. Run: certbot certonly --webroot -w /var/www/certbot -d api.quathera.com
#   3. Copy certs to nginx/certs/ or mount Let's Encrypt folder
# =============================================================================

CERT_DIR="./nginx/certs"

# Create certs directory if it doesn't exist
mkdir -p "$CERT_DIR"

echo "Generating self-signed SSL certificate..."
echo "========================================="

# Generate private key and self-signed certificate
openssl req -x509 \
    -nodes \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/C=US/ST=State/L=City/O=Quathera/OU=Development/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:api.quathera.com,DNS:app.quathera.com,DNS:quathera.com,IP:127.0.0.1"

# Set permissions
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo ""
echo "✅ Certificates generated successfully!"
echo ""
echo "Files created:"
echo "  - $CERT_DIR/server.crt (certificate)"
echo "  - $CERT_DIR/server.key (private key)"
echo ""
echo "⚠️  These are SELF-SIGNED certificates for development."
echo "   Your agent will need to skip certificate verification:"
echo ""
echo "   Python: requests.get(url, verify=False)"
echo "   Or set: REQUESTS_CA_BUNDLE=/path/to/server.crt"
echo ""
echo "📌 For PRODUCTION, use Let's Encrypt:"
echo "   certbot certonly --webroot -w /var/www/certbot -d api.quathera.com"
echo ""
