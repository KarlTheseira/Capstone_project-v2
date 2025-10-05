import azure.functions as func
import logging
import json
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to send email notifications
    
    This function handles various types of emails:
    - Order confirmations
    - Quote responses  
    - Welcome emails
    - Password resets
    - Custom notifications
    """
    
    logging.info('📧 Email notification function triggered')
    
    try:
        # Parse request data
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON payload"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Extract email parameters
        email_type = req_body.get('type')
        recipient_email = req_body.get('to')
        recipient_name = req_body.get('name', '')
        
        if not email_type or not recipient_email:
            return func.HttpResponse(
                json.dumps({"error": "email type and recipient are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logging.info(f"📤 Sending {email_type} email to {recipient_email}")
        
        # Route to appropriate email handler
        if email_type == 'order_confirmation':
            result = send_order_confirmation(req_body)
        elif email_type == 'quote_response':
            result = send_quote_response(req_body)
        elif email_type == 'welcome':
            result = send_welcome_email(req_body)
        elif email_type == 'password_reset':
            result = send_password_reset(req_body)
        elif email_type == 'custom':
            result = send_custom_email(req_body)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unsupported email type: {email_type}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if result['success']:
            logging.info(f"✅ Email sent successfully to {recipient_email}")
            return func.HttpResponse(
                json.dumps(result),
                status_code=200,
                mimetype="application/json"
            )
        else:
            logging.error(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
            return func.HttpResponse(
                json.dumps(result),
                status_code=500,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"💥 Error in email function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def send_order_confirmation(data):
    """Send order confirmation email"""
    
    try:
        order_id = data.get('order_id')
        total_amount = data.get('total_amount', '0.00')
        currency = data.get('currency', 'SGD')
        items = data.get('items', [])
        
        subject = f"Order Confirmation #{order_id} - FlashStudio"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">FlashStudio</h1>
                <h2 style="color: white; margin: 10px 0 0 0;">Order Confirmed!</h2>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h3 style="color: #333;">Thank you for your order!</h3>
                <p>Hi {data.get('name', 'Valued Customer')},</p>
                
                <p>Your order has been confirmed and is being processed. Here are the details:</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #667eea;">Order #{order_id}</h4>
                    <p><strong>Total:</strong> {currency} {total_amount}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                    
                    <h5>Items:</h5>
                    <ul>
        """
        
        for item in items:
            html_content += f"<li>{item.get('name', 'Item')} - {currency} {item.get('price', '0.00')}</li>"
        
        html_content += f"""
                    </ul>
                </div>
                
                <p>We'll send you another email when your order ships.</p>
                
                <p>Thank you for choosing FlashStudio!</p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://flashstudio-app.azurewebsites.net/orders" 
                       style="background: #667eea; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Order Status
                    </a>
                </div>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center;">
                <p style="margin: 0;">FlashStudio - Professional Video Production</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;">
                    Need help? Contact us at support@flashstudio.com
                </p>
            </div>
        </div>
        """
        
        return send_email(
            to_email=data.get('to'),
            to_name=data.get('name', ''),
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        return {"success": False, "error": f"Failed to create order confirmation: {e}"}


def send_quote_response(data):
    """Send quote response email"""
    
    try:
        quote_id = data.get('quote_id')
        service_type = data.get('service_type', 'Video Production')
        quote_amount = data.get('quote_amount')
        
        subject = f"Your FlashStudio Quote #{quote_id}"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">FlashStudio</h1>
                <h2 style="color: white; margin: 10px 0 0 0;">Your Quote is Ready!</h2>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h3 style="color: #333;">Quote #{quote_id}</h3>
                <p>Hi {data.get('name', 'Valued Customer')},</p>
                
                <p>Thank you for your interest in our {service_type} services. We've prepared a custom quote for you:</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <h4 style="color: #667eea; margin-top: 0;">Service: {service_type}</h4>
                    {f'<p style="font-size: 24px; font-weight: bold; color: #333; margin: 10px 0;">SGD {quote_amount}</p>' if quote_amount else '<p>Custom pricing - we\'ll contact you soon!</p>'}
                </div>
                
                <p>This quote is valid for 30 days. We're excited to work with you on your project!</p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://flashstudio-app.azurewebsites.net/contact" 
                       style="background: #667eea; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Contact Us
                    </a>
                </div>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center;">
                <p style="margin: 0;">FlashStudio - Professional Video Production</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;">
                    Reply to this email or call us at +65 1234 5678
                </p>
            </div>
        </div>
        """
        
        return send_email(
            to_email=data.get('to'),
            to_name=data.get('name', ''),
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        return {"success": False, "error": f"Failed to create quote response: {e}"}


def send_welcome_email(data):
    """Send welcome email for new users"""
    
    try:
        subject = "Welcome to FlashStudio!"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Welcome to FlashStudio!</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h3 style="color: #333;">Hi {data.get('name', 'there')}!</h3>
                
                <p>Welcome to FlashStudio - your premier destination for professional video production services.</p>
                
                <p>Here's what you can do with your new account:</p>
                
                <ul>
                    <li>📹 Browse our portfolio of work</li>
                    <li>💼 Request custom quotes for your projects</li>
                    <li>📅 Book consultations with our team</li>
                    <li>🛒 Shop our video packages and products</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://flashstudio-app.azurewebsites.net/services" 
                       style="background: #667eea; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Explore Our Services
                    </a>
                </div>
                
                <p>If you have any questions, don't hesitate to reach out. We're here to help bring your vision to life!</p>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center;">
                <p style="margin: 0;">FlashStudio - Professional Video Production</p>
            </div>
        </div>
        """
        
        return send_email(
            to_email=data.get('to'),
            to_name=data.get('name', ''),
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        return {"success": False, "error": f"Failed to create welcome email: {e}"}


def send_custom_email(data):
    """Send custom email with provided content"""
    
    try:
        subject = data.get('subject', 'Notification from FlashStudio')
        message = data.get('message', '')
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">FlashStudio</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <p>Hi {data.get('name', 'there')},</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    {message}
                </div>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center;">
                <p style="margin: 0;">FlashStudio - Professional Video Production</p>
            </div>
        </div>
        """
        
        return send_email(
            to_email=data.get('to'),
            to_name=data.get('name', ''),
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        return {"success": False, "error": f"Failed to send custom email: {e}"}


def send_email(to_email, to_name, subject, html_content):
    """Send email using SendGrid"""
    
    try:
        # Get SendGrid API key
        sendgrid_api_key = os.environ.get('EMAIL_API_KEY')
        if not sendgrid_api_key:
            return {"success": False, "error": "SendGrid API key not configured"}
        
        # Create SendGrid client
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        
        # Create email
        from_email = Email(os.environ.get('EMAIL_FROM', 'noreply@flashstudio.com'))
        to_email_obj = To(email=to_email, name=to_name)
        
        mail = Mail(
            from_email=from_email,
            to_emails=to_email_obj,
            subject=subject,
            html_content=html_content
        )
        
        # Send email
        response = sg.send(mail)
        
        return {
            "success": True,
            "message": f"Email sent to {to_email}",
            "status_code": response.status_code
        }
        
    except Exception as e:
        return {"success": False, "error": f"SendGrid error: {str(e)}"}


def send_password_reset(data):
    """Send password reset email"""
    
    try:
        reset_token = data.get('reset_token')
        reset_url = f"https://flashstudio-app.azurewebsites.net/reset-password?token={reset_token}"
        
        subject = "Reset Your FlashStudio Password"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">FlashStudio</h1>
                <h2 style="color: white; margin: 10px 0 0 0;">Password Reset</h2>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h3 style="color: #333;">Reset Your Password</h3>
                <p>Hi {data.get('name', 'there')},</p>
                
                <p>You requested a password reset for your FlashStudio account. Click the button below to create a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background: #667eea; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>This link will expire in 24 hours. If you didn't request this reset, please ignore this email.</p>
                
                <p style="font-size: 14px; color: #666;">
                    If the button doesn't work, copy and paste this link:<br>
                    {reset_url}
                </p>
            </div>
            
            <div style="background: #333; color: white; padding: 20px; text-align: center;">
                <p style="margin: 0;">FlashStudio - Professional Video Production</p>
            </div>
        </div>
        """
        
        return send_email(
            to_email=data.get('to'),
            to_name=data.get('name', ''),
            subject=subject,
            html_content=html_content
        )
        
    except Exception as e:
        return {"success": False, "error": f"Failed to create password reset email: {e}"}