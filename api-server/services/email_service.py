"""
Email Service using AWS SES
Handles sending invitation emails and other transactional emails
"""
import boto3
from botocore.exceptions import ClientError
import os
from typing import Optional

# AWS SES Configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "no-reply@quathera.com")
SES_SENDER_NAME = os.getenv("SES_SENDER_NAME", "Quathera")

# For testing in sandbox mode, use a verified email
SES_SANDBOX_MODE = os.getenv("SES_SANDBOX_MODE", "true").lower() == "true"
SES_TEST_SENDER = os.getenv("SES_TEST_SENDER", "ranlaser@gmail.com")

# App URLs
APP_URL = os.getenv("APP_URL", "https://localhost")


def get_ses_client():
    """Get AWS SES client"""
    return boto3.client(
        'ses',
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> dict:
    """
    Send an email using AWS SES
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML content of the email
        text_body: Plain text content (optional, will be derived from html if not provided)
    
    Returns:
        dict with success status and message_id or error
    """
    client = get_ses_client()
    
    # Use test sender in sandbox mode
    sender = SES_TEST_SENDER if SES_SANDBOX_MODE else SES_SENDER_EMAIL
    sender_formatted = f"{SES_SENDER_NAME} <{sender}>"
    
    # Default text body if not provided
    if not text_body:
        text_body = html_body.replace("<br>", "\n").replace("</p>", "\n\n")
        # Simple HTML tag removal
        import re
        text_body = re.sub('<[^<]+?>', '', text_body)
    
    try:
        response = client.send_email(
            Source=sender_formatted,
            Destination={
                'ToAddresses': [to_email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        return {
            "success": True,
            "message_id": response['MessageId']
        }
        
    except ClientError as e:
        error_message = e.response['Error']['Message']
        print(f"Failed to send email: {error_message}")
        return {
            "success": False,
            "error": error_message
        }


def send_invitation_email(
    to_email: str,
    to_name: str,
    inviter_name: str,
    company_name: str,
    invite_token: str
) -> dict:
    """
    Send an invitation email to a new user
    
    Args:
        to_email: New user's email
        to_name: New user's name
        inviter_name: Name of the admin sending the invitation
        company_name: Company name
        invite_token: Unique invitation token
    
    Returns:
        dict with success status
    """
    invite_url = f"{APP_URL}/accept-invite?token={invite_token}"
    
    subject = f"You've been invited to join {company_name} on Quathera"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f7;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">Quathera</h1>
                                <p style="margin: 10px 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">AI-Powered Form Testing Platform</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px; color: #1a1a2e; font-size: 24px; font-weight: 600;">
                                    Hi {to_name},
                                </h2>
                                
                                <p style="margin: 0 0 20px; color: #4a5568; font-size: 16px; line-height: 1.6;">
                                    <strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> on Quathera.
                                </p>
                                
                                <p style="margin: 0 0 30px; color: #4a5568; font-size: 16px; line-height: 1.6;">
                                    Click the button below to set up your account and get started.
                                </p>
                                
                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 10px 0 30px;">
                                            <a href="{invite_url}" style="display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);">
                                                Accept Invitation
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 0 0 10px; color: #718096; font-size: 14px;">
                                    Or copy and paste this link into your browser:
                                </p>
                                <p style="margin: 0 0 30px; color: #6366f1; font-size: 14px; word-break: break-all;">
                                    {invite_url}
                                </p>
                                
                                <!-- Warning Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #92400e; font-size: 14px;">
                                                ⏰ This invitation expires in <strong>7 days</strong>. If you didn't expect this invitation, you can safely ignore this email.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 10px; color: #718096; font-size: 14px;">
                                    — The Quathera Team
                                </p>
                                <p style="margin: 0; color: #a0aec0; font-size: 12px;">
                                    © 2025 Quathera. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {to_name},

{inviter_name} has invited you to join {company_name} on Quathera.

Click the link below to set up your account and get started:

{invite_url}

This invitation expires in 7 days.

If you didn't expect this invitation, you can safely ignore this email.

— The Quathera Team
    """
    
    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(
    to_email: str,
    to_name: str,
    reset_token: str
) -> dict:
    """
    Send a password reset email
    """
    reset_url = f"{APP_URL}/reset-password?token={reset_token}"
    
    subject = "Reset your Quathera password"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f7;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden;">
                        <tr>
                            <td style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px;">Quathera</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px; color: #1a1a2e;">Hi {to_name},</h2>
                                <p style="color: #4a5568; font-size: 16px; line-height: 1.6;">
                                    We received a request to reset your password. Click the button below to create a new password.
                                </p>
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 30px 0;">
                                            <a href="{reset_url}" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; font-weight: 600;">
                                                Reset Password
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                <p style="color: #718096; font-size: 14px;">
                                    This link expires in 1 hour. If you didn't request a password reset, you can ignore this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)
