import boto3
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "quattera-screenshots-2026")
S3_REGION = os.getenv("AWS_REGION", "eu-west-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=S3_REGION
) if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY else None

def get_s3_client():
    """Get S3 client - allows for future BYOK per-customer clients."""
    return s3_client

def upload_screenshot_to_s3(
    image_bytes: bytes,
    company_id: int,
    project_id: int,
    session_id: int,
    filename: str,
    image_type: str = "screenshot",
    kms_key_arn: str = None
) -> dict:
    """
    Upload screenshot to S3 and return metadata
    
    Args:
        image_bytes: Image data as bytes
        company_id: Company ID
        session_id: Crawl session ID
        filename: Original filename
        image_type: Type of screenshot
    
    Returns:
        dict with s3_url, s3_key, s3_bucket, file_size, width, height
    """
    
    if not s3_client:
        raise Exception("S3 client not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    
    # Generate unique S3 key
    s3_key = f"{image_type}/{company_id}/{project_id}/{session_id}/{filename}"
    
    # Get image dimensions
    try:
        img = Image.open(BytesIO(image_bytes))
        width, height = img.size
    except:
        width, height = None, None
    
    # Upload to S3
    put_kwargs = {
        'Bucket': S3_BUCKET,
        'Key': s3_key,
        'Body': image_bytes,
        'ContentType': 'image/png',
        'Metadata': {
            'company-id': str(company_id),
            'project-id': str(project_id),
            'session-id': str(session_id),
            'image-type': image_type
        }
    }

    # BYOK support - use customer's KMS key if provided
    if kms_key_arn:
        put_kwargs['ServerSideEncryption'] = 'aws:kms'
        put_kwargs['SSEKMSKeyId'] = kms_key_arn

    s3_client.put_object(**put_kwargs)
    
    # Generate public URL
    s3_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
    
    return {
        "s3_url": s3_url,
        "s3_key": s3_key,
        "s3_bucket": S3_BUCKET,
        "file_size_bytes": len(image_bytes),
        "width_px": width,
        "height_px": height
    }


def delete_screenshot_from_s3(s3_key: str) -> bool:
    """
    Delete screenshot from S3
    
    Args:
        s3_key: S3 object key
    
    Returns:
        True if successful
    """
    if not s3_client:
        raise Exception("S3 client not configured")
    
    try:
        s3_client.delete_object(
            Bucket=S3_BUCKET,
            Key=s3_key
        )
        return True
    except Exception as e:
        print(f"Error deleting from S3: {e}")
        return False


def get_screenshot_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """
    Generate presigned URL for private screenshot access
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration in seconds (default 1 hour)
    
    Returns:
        Presigned URL
    """
    if not s3_client:
        raise Exception("S3 client not configured")
    
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_key
        },
        ExpiresIn=expiration
    )
    
    return url


def generate_presigned_put_url(
        s3_key: str,
        content_type: str = 'image/png',
        expiration: int = 900,
        kms_key_arn: str = None
) -> str:
    """
    Generate pre-signed URL for uploading (PUT) to S3.
    Agent uses this to upload directly to S3 without credentials.

    Args:
        s3_key: S3 object key (path)
        content_type: File content type
        expiration: URL expiration in seconds (default 15 minutes)
        kms_key_arn: Optional KMS key for BYOK encryption

    Returns:
        Pre-signed PUT URL
    """
    if not s3_client:
        raise Exception("S3 client not configured")

    params = {
        'Bucket': S3_BUCKET,
        'Key': s3_key,
        'ContentType': content_type
    }

    # BYOK support
    if kms_key_arn:
        params['ServerSideEncryption'] = 'aws:kms'
        params['SSEKMSKeyId'] = kms_key_arn

    url = s3_client.generate_presigned_url(
        'put_object',
        Params=params,
        ExpiresIn=expiration
    )

    return url


def generate_presigned_put_urls_batch(
        s3_keys: list,
        content_type: str = 'image/png',
        expiration: int = 900,
        kms_key_arn: str = None
) -> list:
    """
    Generate multiple pre-signed PUT URLs.

    Args:
        s3_keys: List of S3 object keys
        content_type: File content type
        expiration: URL expiration in seconds
        kms_key_arn: Optional KMS key for BYOK

    Returns:
        List of {s3_key, url} dicts
    """
    if not s3_client:
        raise Exception("S3 client not configured")

    results = []
    for s3_key in s3_keys:
        params = {
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'ContentType': content_type
        }

        if kms_key_arn:
            params['ServerSideEncryption'] = 'aws:kms'
            params['SSEKMSKeyId'] = kms_key_arn

        url = s3_client.generate_presigned_url(
            'put_object',
            Params=params,
            ExpiresIn=expiration
        )

        results.append({
            's3_key': s3_key,
            'url': url
        })

    return results


def get_s3_file_content(s3_key: str) -> bytes:
    """
    Download file content from S3.
    Used by Celery to read large logs uploaded by agent.

    Args:
        s3_key: S3 object key

    Returns:
        File content as bytes
    """
    if not s3_client:
        raise Exception("S3 client not configured")

    response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    return response['Body'].read()

def delete_s3_folder(prefix: str) -> int:
    """
    Delete all objects with given prefix (folder).
    Used for cleanup on remap/delete.

    Args:
        prefix: S3 key prefix, e.g., "form_files/1/5/182/"

    Returns:
        Number of deleted objects
    """
    if not s3_client:
        raise Exception("S3 client not configured")

    deleted_count = 0

    try:
        # List all objects with prefix
        paginator = s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            if 'Contents' not in page:
                continue

            # Delete in batches of 1000 (S3 limit)
            objects = [{'Key': obj['Key']} for obj in page['Contents']]

            if objects:
                s3_client.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={'Objects': objects}
                )
                deleted_count += len(objects)

        return deleted_count

    except Exception as e:
        print(f"Error deleting S3 folder {prefix}: {e}")
        return deleted_count


def check_s3_connection() -> dict:
    """
    Check if S3 is properly configured and accessible.
    """
    if not s3_client:
        return {
            "status": "error",
            "message": "S3 client not configured. Missing AWS credentials."
        }

    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        return {
            "status": "ok",
            "message": f"S3 bucket '{S3_BUCKET}' is accessible",
            "bucket": S3_BUCKET,
            "region": S3_REGION
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Cannot access S3 bucket '{S3_BUCKET}': {str(e)}"
        }

def create_s3_bucket_if_not_exists():
    """
    Create S3 bucket if it doesn't exist
    Call this on application startup
    """
    if not s3_client:
        print("S3 client not configured. Skipping bucket creation.")
        return
    
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        print(f"S3 bucket '{S3_BUCKET}' already exists")
    except:
        try:
            if S3_REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=S3_BUCKET)
            else:
                s3_client.create_bucket(
                    Bucket=S3_BUCKET,
                    CreateBucketConfiguration={'LocationConstraint': S3_REGION}
                )
            print(f"Created S3 bucket '{S3_BUCKET}'")
        except Exception as e:
            print(f"Error creating S3 bucket: {e}")

def get_screenshot_download_url(s3_key: str, filename: str, expiration: int = 3600) -> str:
    """
    Generate pre-signed URL with Content-Disposition: attachment header.
    This forces browser to download instead of display.
    """
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'ResponseContentDisposition': f'attachment; filename="{filename}"'
        },
        ExpiresIn=expiration
    )
    return url

# ============================================================================
# Generic S3 Utilities
# ============================================================================

def get_s3_file_as_base64(s3_key: str) -> str:
    """Download file from S3 and return as base64 string."""
    if not s3_client:
        raise Exception("S3 client not configured")

    import base64

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_bytes = response['Body'].read()
        return base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error fetching {s3_key} from S3: {e}")
        return None


def get_s3_files_as_base64_parallel(s3_keys: list) -> list:
    """Download multiple files from S3 in parallel and return as base64 strings."""
    if not s3_client:
        raise Exception("S3 client not configured")

    import base64
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def fetch_one(s3_key):
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
            file_bytes = response['Body'].read()
            return {"s3_key": s3_key, "base64": base64.b64encode(file_bytes).decode('utf-8')}
        except Exception as e:
            print(f"Error fetching {s3_key}: {e}")
            return {"s3_key": s3_key, "base64": None}

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_one, key): key for key in s3_keys}
        for future in as_completed(futures):
            results.append(future.result())

    key_to_result = {r["s3_key"]: r["base64"] for r in results}
    return [key_to_result.get(key) for key in s3_keys]