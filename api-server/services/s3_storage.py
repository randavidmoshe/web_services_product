import boto3
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "form-discoverer-screenshots")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=S3_REGION
) if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY else None


def upload_screenshot_to_s3(
    image_bytes: bytes,
    company_id: int,
    session_id: int,
    filename: str,
    image_type: str = "screenshot"
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
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"screenshots/{company_id}/{session_id}/{image_type}_{timestamp}_{filename}"
    
    # Get image dimensions
    try:
        img = Image.open(BytesIO(image_bytes))
        width, height = img.size
    except:
        width, height = None, None
    
    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=image_bytes,
        ContentType='image/png',
        Metadata={
            'company-id': str(company_id),
            'session-id': str(session_id),
            'image-type': image_type
        }
    )
    
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
