"""
Email Service using AWS SES
Handles sending invitation emails and other transactional emails
"""
import boto3
from botocore.exceptions import ClientError
import os
from typing import Optional
from datetime import datetime

# AWS SES Configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "no-reply@quattera.ai")
SES_SENDER_NAME = os.getenv("SES_SENDER_NAME", "Quattera")

# For testing in sandbox mode, use a verified email
SES_SANDBOX_MODE = os.getenv("SES_SANDBOX_MODE", "true").lower() == "true"
SES_TEST_SENDER = os.getenv("SES_TEST_SENDER", "ranlaser@gmail.com")
PRODUCT_OWNER_EMAIL = os.getenv("PRODUCT_OWNER_EMAIL", "ranlaser@gmail.com")

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
    
    subject = f"You've been invited to join {company_name} on Quattera"
    
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
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">Quattera</h1>
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
                                    <strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> on Quattera.
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
                                    — The Quattera Team
                                </p>
                                <p style="margin: 0; color: #a0aec0; font-size: 12px;">
                                    © 2025 Quattera. All rights reserved.
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

{inviter_name} has invited you to join {company_name} on Quattera.

Click the link below to set up your account and get started:

{invite_url}

This invitation expires in 7 days.

If you didn't expect this invitation, you can safely ignore this email.

— The Quattera Team
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
    
    subject = "Reset your Quattera password"
    
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
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px;">Quattera</h1>
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


def send_verification_email(
        to_email: str,
        to_name: str,
        verification_token: str
) -> dict:
    """
    Send an email verification email for new signups

    Args:
        to_email: User's email
        to_name: User's name
        verification_token: Unique verification token (unhashed)

    Returns:
        dict with success status
    """
    verify_url = f"{APP_URL}/verify-email?token={verification_token}"

    subject = "Verify your Quattera account"

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
                            <td style="background: linear-gradient(135deg, #00F5D4, #00BBF9); padding: 40px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #0A0E17; font-size: 28px; font-weight: 700;">Quattera</h1>
                                <p style="margin: 10px 0 0; color: rgba(10,14,23,0.8); font-size: 14px;">AI-Powered Form Testing Platform</p>
                            </td>
                        </tr>

                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px; color: #1a1a2e; font-size: 24px; font-weight: 600;">
                                    Hi {to_name},
                                </h2>

                                <p style="margin: 0 0 20px; color: #4a5568; font-size: 16px; line-height: 1.6;">
                                    Thank you for signing up for Quattera! Please verify your email address to complete your registration.
                                </p>

                                <p style="margin: 0 0 30px; color: #4a5568; font-size: 16px; line-height: 1.6;">
                                    Click the button below to verify your email and get started.
                                </p>

                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 10px 0 30px;">
                                            <a href="{verify_url}" style="display: inline-block; background: linear-gradient(135deg, #00F5D4, #00BBF9); color: #0A0E17; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 15px rgba(0, 245, 212, 0.4);">
                                                Verify Email Address
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <p style="margin: 0 0 10px; color: #718096; font-size: 14px;">
                                    Or copy and paste this link into your browser:
                                </p>
                                <p style="margin: 0 0 30px; color: #00BBF9; font-size: 14px; word-break: break-all;">
                                    {verify_url}
                                </p>

                                <!-- Warning Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #92400e; font-size: 14px;">
                                                ⏰ This link expires in <strong>24 hours</strong>. If you didn't create an account, you can safely ignore this email.
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
                                    — The Quattera Team
                                </p>
                                <p style="margin: 0; color: #a0aec0; font-size: 12px;">
                                    © 2025 Quattera. All rights reserved.
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

Thank you for signing up for Quattera! Please verify your email address to complete your registration.

Click the link below to verify your email:

{verify_url}

This link expires in 24 hours.

If you didn't create an account, you can safely ignore this email.

— The Quattera Team
    """

    return send_email(to_email, subject, html_body, text_body)


def send_password_reset_email(to_email: str, to_name: str, reset_token: str) -> dict:
    """Send password reset email"""
    try:
        reset_url = f"{os.getenv('FRONTEND_URL', 'https://localhost')}/reset-password?token={reset_token}"

        subject = "Reset Your Quattera Password"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px 20px;">
            <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #0ea5e9, #6366f1); padding: 32px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">Quattera</h1>
                </div>
                <div style="padding: 40px 32px;">
                    <h2 style="color: #1e293b; margin: 0 0 16px; font-size: 22px;">Reset Your Password</h2>
                    <p style="color: #64748b; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                        Hi {to_name},<br><br>
                        We received a request to reset your password. Click the button below to create a new password:
                    </p>
                    <a href="{reset_url}" style="display: block; background: linear-gradient(135deg, #0ea5e9, #6366f1); color: white; text-decoration: none; padding: 16px 32px; border-radius: 10px; font-weight: 600; font-size: 16px; text-align: center; margin: 0 0 24px;">
                        Reset Password
                    </a>
                    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                        This link expires in 1 hour. If you didn't request this, you can safely ignore this email.
                    </p>
                </div>
                <div style="padding: 24px 32px; background: #f8fafc; text-align: center;">
                    <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                        © 2026 Quattera. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
Reset Your Password

Hi {to_name},

We received a request to reset your password. Click the link below:
{reset_url}

This link expires in 1 hour.

If you didn't request this, you can safely ignore this email.
        """

        return send_email(to_email, subject, html_body, text_body)

    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
        return {"success": False, "error": str(e)}


def send_early_access_approved_email(
        to_email: str,
        to_name: str,
        company_name: str,
        daily_budget: float,
        trial_days: int
) -> dict:
    """Send Early Access approval notification email"""
    try:
        login_url = f"{os.getenv('FRONTEND_URL', 'https://localhost')}/login"

        subject = "Your Quattera Early Access Has Been Approved! 🎉"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px 20px;">
            <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 32px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">🎉 You're In!</h1>
                </div>
                <div style="padding: 40px 32px;">
                    <h2 style="color: #1e293b; margin: 0 0 16px; font-size: 22px;">Welcome to Quattera, {to_name}!</h2>
                    <p style="color: #64748b; font-size: 16px; line-height: 1.6; margin: 0 0 24px;">
                        Great news! Your Early Access request for <strong>{company_name}</strong> has been approved. You can now start using Quattera's AI-powered testing features.
                    </p>

                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                        <p style="color: #166534; margin: 0 0 12px; font-weight: 600;">Your Trial Details:</p>
                        <ul style="color: #166534; margin: 0; padding-left: 20px; line-height: 1.8;">
                            <li>Daily AI Budget: <strong>${daily_budget:.2f}/day</strong></li>
                            <li>Trial Duration: <strong>{trial_days} days</strong></li>
                        </ul>
                    </div>

                    <a href="{login_url}" style="display: block; background: linear-gradient(135deg, #10b981, #059669); color: white; text-decoration: none; padding: 16px 32px; border-radius: 10px; font-weight: 600; font-size: 16px; text-align: center; margin: 0 0 24px;">
                        Start Testing Now
                    </a>

                    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                        Need more capacity? You can upgrade to BYOK (Bring Your Own Key) anytime for unlimited usage.
                    </p>
                </div>
                <div style="padding: 24px 32px; background: #f8fafc; text-align: center;">
                    <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                        © 2026 Quattera. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
Welcome to Quattera, {to_name}!

Great news! Your Early Access request for {company_name} has been approved.

Your Trial Details:
- Daily AI Budget: ${daily_budget:.2f}/day
- Trial Duration: {trial_days} days

Login now to start testing: {login_url}

Need more capacity? You can upgrade to BYOK anytime for unlimited usage.
        """

        return send_email(to_email, subject, html_body, text_body)

    except Exception as e:
        print(f"Failed to send Early Access approval email: {str(e)}")
        return {"success": False, "error": str(e)}


# ==================== PRODUCT OWNER NOTIFICATIONS ====================

def notify_product_owner(
        action: str,
        details: dict = None,
        ip_address: str = None
) -> dict:
    """
    Send email notification to product owner about super admin actions.
    """
    if not PRODUCT_OWNER_EMAIL:
        print("PRODUCT_OWNER_EMAIL not configured, skipping notification")
        return {"success": False, "error": "No product owner email configured"}

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Format details for display
    details_html = ""
    details_text = ""
    if details:
        details_html = "<ul style='margin: 0; padding-left: 20px;'>"
        for key, value in details.items():
            details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_text += f"  - {key}: {value}\n"
        details_html += "</ul>"

    # Action-specific colors and icons
    action_styles = {
        'approve_access': {'color': '#10b981', 'icon': '✅', 'label': 'Access Approved'},
        'reject_access': {'color': '#ef4444', 'icon': '❌', 'label': 'Access Rejected'},
        'disable_company': {'color': '#f59e0b', 'icon': '⚠️', 'label': 'Company Disabled'},
        'enable_company': {'color': '#10b981', 'icon': '✅', 'label': 'Company Enabled'},
        'update_limits': {'color': '#6366f1', 'icon': '📝', 'label': 'Limits Updated'},
        'login': {'color': '#0ea5e9', 'icon': '🔐', 'label': 'Super Admin Login'},
    }

    style = action_styles.get(action, {'color': '#6366f1', 'icon': '📋', 'label': action})

    subject = f"[Quattera Admin] {style['icon']} {style['label']}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px 20px;">
        <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            <div style="background: {style['color']}; padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">{style['icon']} {style['label']}</h1>
            </div>
            <div style="padding: 32px;">
                <p style="color: #64748b; font-size: 14px; margin: 0 0 8px;"><strong>Time:</strong> {timestamp}</p>
                <p style="color: #64748b; font-size: 14px; margin: 0 0 8px;"><strong>Action:</strong> {action}</p>
                <p style="color: #64748b; font-size: 14px; margin: 0 0 16px;"><strong>IP Address:</strong> {ip_address or 'Unknown'}</p>
                {f'<div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin-top: 16px;"><p style="color: #1e293b; margin: 0 0 8px; font-weight: 600;">Details:</p>{details_html}</div>' if details else ''}
            </div>
            <div style="padding: 20px 32px; background: #f8fafc; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">Automated notification from Quattera Super Admin system.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"[Quattera Admin] {style['label']}\n\nTime: {timestamp}\nAction: {action}\nIP: {ip_address or 'Unknown'}\n\nDetails:\n{details_text}"

    return send_email(PRODUCT_OWNER_EMAIL, subject, html_body, text_body)


def notify_super_admin_login(ip_address: str = None) -> dict:
    """Send notification when super admin logs in."""
    return notify_product_owner(
        action='login',
        details={'event': 'Super admin login detected'},
        ip_address=ip_address
    )

# ==================== ASYNC EMAIL FUNCTIONS (Celery) ====================

def send_verification_email_queued(to_email: str, to_name: str, verification_token: str):
    """Queue verification email for async sending"""
    from tasks.email_tasks import send_verification_email_async
    send_verification_email_async.delay(to_email, to_name, verification_token)
    return {"success": True, "queued": True}


def send_invitation_email_queued(to_email: str, to_name: str, inviter_name: str, company_name: str, invite_token: str):
    """Queue invitation email for async sending"""
    from tasks.email_tasks import send_invitation_email_async
    send_invitation_email_async.delay(to_email, to_name, inviter_name, company_name, invite_token)
    return {"success": True, "queued": True}


def send_password_reset_email_queued(to_email: str, to_name: str, reset_token: str):
    """Queue password reset email for async sending"""
    from tasks.email_tasks import send_password_reset_email_async
    send_password_reset_email_async.delay(to_email, to_name, reset_token)
    return {"success": True, "queued": True}


def send_early_access_approved_email_queued(to_email: str, to_name: str, company_name: str, daily_budget: float, trial_days: int):
    """Queue early access approval email for async sending"""
    from tasks.email_tasks import send_early_access_approved_email_async
    send_early_access_approved_email_async.delay(to_email, to_name, company_name, daily_budget, trial_days)
    return {"success": True, "queued": True}