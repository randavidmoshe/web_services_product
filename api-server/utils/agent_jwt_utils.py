# JWT Utilities for Agent Authentication
# Location: api-server/utils/agent_jwt_utils.py
#
# Level 3 Security: Short-lived JWT tokens with session enforcement
# - Tokens expire after 30 minutes
# - Session ID ensures only one agent per user is active

from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_MINUTES = 30


def create_jwt_token(api_key: str, user_id: int, agent_id: str, session_id: str) -> str:
    """
    Create a JWT token for agent authentication.
    
    The token contains:
    - api_key: Agent's permanent API key (Level 2)
    - user_id: Owner of the agent
    - agent_id: Agent identifier
    - session_id: Unique session - used to enforce single agent per user
    - exp: Expiration time (30 minutes from now)
    """
    payload = {
        'api_key': api_key,
        'user_id': user_id,
        'agent_id': agent_id,
        'session_id': session_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_token_expiry_seconds() -> int:
    """Get the JWT token expiry time in seconds (1800 = 30 minutes)"""
    return JWT_EXPIRY_MINUTES * 60
