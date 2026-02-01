"""
Two-Factor Authentication Service
TOTP-based 2FA using pyotp
"""
import pyotp
import qrcode
import io
import base64


class TwoFactorAuth:
    """Handle TOTP-based two-factor authentication"""
    
    ISSUER_NAME = "Quattera"  # Your app name - shows in authenticator app
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret for a user"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer: str = None) -> str:
        """Generate the provisioning URI for authenticator apps"""
        issuer = issuer or TwoFactorAuth.ISSUER_NAME
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code(secret: str, email: str, issuer: str = None) -> str:
        """
        Generate a QR code for the TOTP secret.
        Returns base64-encoded PNG image.
        """
        uri = TwoFactorAuth.get_totp_uri(secret, email, issuer)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        Allows 1 period tolerance for clock drift.
        """
        if not secret or not code:
            return False
        
        # Remove any spaces or dashes from code
        code = code.replace(" ", "").replace("-", "")
        
        # Validate code format (should be 6 digits)
        if not code.isdigit() or len(code) != 6:
            return False
        
        totp = pyotp.TOTP(secret)
        # valid_window=1 allows codes from 30 seconds before/after
        return totp.verify(code, valid_window=1)
    
    @staticmethod
    def get_current_code(secret: str) -> str:
        """Get the current TOTP code (for testing only)"""
        totp = pyotp.TOTP(secret)
        return totp.now()
