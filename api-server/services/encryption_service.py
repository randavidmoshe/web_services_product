# services/encryption_service.py
# KMS Encryption Service with Redis Caching
# Secure, scalable encryption for customer API keys and credentials

import os
import base64
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
SECRET_CACHE_TTL = 300

# KMS Key ID from environment
KMS_KEY_ID = os.getenv("KMS_KEY_ID")


def _get_kms_client():
    """Get boto3 KMS client"""
    import boto3
    return boto3.client(
        'kms',
        region_name=os.getenv("AWS_REGION", "eu-west-1")
    )


def _get_redis_client():
    """Get Redis client for caching"""
    import redis
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=False
    )


def encrypt_secret(plaintext: str, company_id: int) -> str:
    """
    Encrypt a secret using KMS with company_id as encryption context.

    Args:
        plaintext: The secret to encrypt
        company_id: Company ID for encryption context (prevents blob swapping)

    Returns:
        Base64-encoded encrypted blob
    """
    if not KMS_KEY_ID:
        logger.error("[EncryptionService] KMS_KEY_ID not configured")
        raise ValueError("KMS_KEY_ID not configured")

    if not plaintext:
        return ""

    try:
        kms = _get_kms_client()
        response = kms.encrypt(
            KeyId=KMS_KEY_ID,
            Plaintext=plaintext.encode('utf-8'),
            EncryptionContext={'company_id': str(company_id)}
        )
        encrypted_blob = response['CiphertextBlob']
        return base64.b64encode(encrypted_blob).decode('utf-8')
    except Exception as e:
        logger.error(f"[EncryptionService] Encryption failed for company {company_id}: {e}")
        raise


def decrypt_secret(ciphertext: str, company_id: int) -> str:
    """
    Decrypt a secret using KMS with company_id as encryption context.

    Args:
        ciphertext: Base64-encoded encrypted blob
        company_id: Company ID for encryption context (must match encryption)

    Returns:
        Decrypted plaintext
    """
    if not ciphertext:
        return ""

    try:
        kms = _get_kms_client()
        encrypted_blob = base64.b64decode(ciphertext)
        response = kms.decrypt(
            CiphertextBlob=encrypted_blob,
            EncryptionContext={'company_id': str(company_id)}
        )
        return response['Plaintext'].decode('utf-8')
    except Exception as e:
        logger.error(f"[EncryptionService] Decryption failed for company {company_id}: {e}")
        raise


def get_cached_secret(company_id: int, secret_type: str) -> Optional[str]:
    """
    Get a secret from Redis cache.

    Args:
        company_id: Company ID
        secret_type: Type of secret (e.g., 'api_key', 'password')

    Returns:
        Cached plaintext or None if not cached
    """
    try:
        redis_client = _get_redis_client()
        cache_key = f"secret:{company_id}:{secret_type}"
        cached = redis_client.get(cache_key)
        if cached:
            return cached.decode('utf-8')
        return None
    except Exception as e:
        logger.warning(f"[EncryptionService] Cache read failed: {e}")
        return None


def cache_secret(company_id: int, secret_type: str, plaintext: str, ttl: int = SECRET_CACHE_TTL) -> None:
    """
    Cache a decrypted secret in Redis.

    Args:
        company_id: Company ID
        secret_type: Type of secret (e.g., 'api_key', 'password')
        plaintext: Decrypted secret to cache
        ttl: Time to live in seconds (default 5 minutes)
    """
    try:
        redis_client = _get_redis_client()
        cache_key = f"secret:{company_id}:{secret_type}"
        redis_client.set(cache_key, plaintext.encode('utf-8'), ex=ttl)
    except Exception as e:
        logger.warning(f"[EncryptionService] Cache write failed: {e}")


def invalidate_cached_secret(company_id: int, secret_type: str) -> None:
    """
    Invalidate a cached secret (call when secret is updated or deleted).

    Args:
        company_id: Company ID
        secret_type: Type of secret (e.g., 'api_key', 'password')
    """
    try:
        redis_client = _get_redis_client()
        cache_key = f"secret:{company_id}:{secret_type}"
        redis_client.delete(cache_key)
        logger.info(f"[EncryptionService] Invalidated cache for company {company_id} {secret_type}")
    except Exception as e:
        logger.warning(f"[EncryptionService] Cache invalidation failed: {e}")


def get_decrypted_api_key(company_id: int, encrypted_key: str) -> str:
    """
    Get decrypted API key with Redis caching.
    This is the main function for AI operations.

    Flow:
    1. Check Redis cache
    2. If miss, decrypt with KMS
    3. Cache result for 5 minutes
    4. Return plaintext

    Args:
        company_id: Company ID
        encrypted_key: Base64-encoded encrypted API key from DB

    Returns:
        Decrypted API key
    """
    if not encrypted_key:
        return ""

    # Check cache first
    cached = get_cached_secret(company_id, "api_key")
    if cached:
        logger.debug(f"[EncryptionService] Cache hit for company {company_id} api_key")
        return cached

    # Cache miss - decrypt from KMS
    logger.debug(f"[EncryptionService] Cache miss for company {company_id} api_key, decrypting...")
    plaintext = decrypt_secret(encrypted_key, company_id)

    # Cache for next time
    cache_secret(company_id, "api_key", plaintext)

    return plaintext


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display (never show full key to frontend).

    Args:
        api_key: Full API key

    Returns:
        Masked key like 'sk-ant-...xxxx'
    """
    if not api_key:
        return ""
    if len(api_key) > 12:
        return f"{api_key[:8]}...{api_key[-4:]}"
    return "****"


def encrypt_credential(plaintext: str, company_id: int) -> str:
    """
    Encrypt a test site credential (username, password, totp_secret).

    Args:
        plaintext: The credential to encrypt
        company_id: Company ID for encryption context

    Returns:
        Base64-encoded encrypted blob, or empty string if plaintext is empty
    """
    if not plaintext:
        return ""
    return encrypt_secret(plaintext, company_id)


def decrypt_credential(ciphertext: str, company_id: int, network_id: int, credential_type: str) -> str:
    """
    Decrypt a test site credential with caching.

    Args:
        ciphertext: Base64-encoded encrypted blob
        company_id: Company ID for encryption context
        network_id: Network ID for cache key isolation
        credential_type: Type of credential ('username', 'password', 'totp_secret')

    Returns:
        Decrypted plaintext, or empty string if ciphertext is empty
    """
    if not ciphertext:
        return ""

    # Check cache first (keyed by company + network + type)
    cache_key = f"cred_{credential_type}_{network_id}"
    cached = get_cached_secret(company_id, cache_key)
    if cached:
        return cached

    # Decrypt and cache
    plaintext = decrypt_secret(ciphertext, company_id)
    cache_secret(company_id, cache_key, plaintext)
    return plaintext


def mask_credential(value: str, credential_type: str) -> str:
    """
    Mask a credential for frontend display.

    Args:
        value: The credential value (may be encrypted or plaintext)
        credential_type: Type of credential

    Returns:
        Masked string for display
    """
    if not value:
        return ""

    if credential_type == "username":
        # Show first 2 chars for username
        if len(value) > 4:
            return f"{value[:2]}{'*' * (len(value) - 2)}"
        return "*" * len(value)
    else:
        # Password/secrets: just show dots
        return "********"


def invalidate_credential_cache(company_id: int, network_id: int) -> None:
    """
    Invalidate cached credentials for a network (call when credentials are updated).

    Args:
        company_id: Company ID
        network_id: Network ID
    """
    try:
        redis_client = _get_redis_client()
        # Invalidate all credential types for this company/network
        for cred_type in ['username', 'password', 'totp_secret']:
            cache_key = f"secret:{company_id}:cred_{cred_type}_{network_id}"
            redis_client.delete(cache_key)
        logger.info(f"[EncryptionService] Invalidated credential cache for network {network_id}")
    except Exception as e:
        logger.warning(f"[EncryptionService] Cache invalidation failed: {e}")