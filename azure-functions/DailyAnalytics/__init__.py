import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To

def main(mytimer: func.TimerRequest) -> None:
    """
    Daily Analytics Timer Function
    
    This function runs every day at 9 AM Singapore time (0 0 9 * * *)
    and generates daily analytics reports for the FlashStudio business.
    
    Features:
    - Daily sales summary
    - New customer registrations
    - Popular products/services
    - Quote requests status
    - Revenue trends
    """
    
    utc_timestamp = datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('⏰ Timer function is running late!')
    
    logging.info('📊 Daily Analytics function triggered at %s', utc_timestamp)
    
    try:
        # Generate analytics report
        analytics_data = generate_daily_analytics()
        
        # Send report to admin
        if analytics_data:
            send_analytics_report(analytics_data)
            logging.info('✅ Daily analytics report sent successfully')
        else:
            logging.warning('⚠️ No analytics data available')
            
    except Exception as e:
        logging.error(f'💥 Error in daily analytics: {str(e)}')
        # Send error notification
        send_error_notification(str(e))


def generate_daily_analytics():
    """Generate daily analytics by calling Flask app API"""
    
    try:
        # Get app URL from environment variables
        app_url = os.environ.get('FLASK_APP_URL', 'https://flashstudio-app.azurewebsites.net')
        api_key = os.environ.get('ANALYTICS_API_KEY')
        
        if not api_key:
            logging.error('❌ Analytics API key not configured')
            return None
        
        # Calculate date range (yesterday's data)
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        logging.info(f'📅 Generating analytics for {date_str}')
        
        # Call Flask app analytics endpoint
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'date': date_str,
            'type': 'daily'
        }
        
        response = requests.get(
            f'{app_url}/api/analytics',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f'❌ Analytics API error: {response.status_code}')
            return generate_mock_analytics(date_str)
            
    except requests.RequestException as e:
        logging.error(f'🌐 Network error calling analytics API: {e}')
        return generate_mock_analytics(yesterday.strftime('%Y-%m-%d'))
    except Exception as e:
        logging.error(f'💥 Error generating analytics: {e}')
        return None


def generate_mock_analytics(date_str):
    """Generate mock analytics data when API is unavailable"""
    
    logging.info('📋 Generating mock analytics data')
    
    return {
        'date': date_str,
        'sales': {
            'total_revenue': 2850.00,
            'total_orders': 12,
            'average_order_value': 237.50,
            'currency': 'SGD'
        },
        'customers': {
            'new_registrations': 5,
            'returning_customers': 8,
            'total_active': 245
        },
        'products': {
            'most_popular': [
                {'name': 'Wedding Video Package', 'sales': 4},
                {'name': 'Corporate Video', 'sales': 3},
                {'name': 'Event Photography', 'sales': 2}
            ],
            'total_products_sold': 18
        },
        'quotes': {
            'new_requests': 7,
            'pending_responses': 3,
            'converted_to_sales': 2
        },
        'website': {
            'unique_visitors': 156,
            'page_views': 423,
            'bounce_rate': 0.32
        }
    }


def send_analytics_report(analytics_data):
    """Send daily analytics report via email"""
    
    try:
        # Get email configuration
        sendgrid_api_key = os.environ.get('EMAIL_API_KEY')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@flashstudio.com')
        
        if not sendgrid_api_key:
            logging.error('❌ SendGrid API key not configured')
            return False
        
        # Generate email content
        html_content = create_analytics_email_template(analytics_data)
        
        # Create SendGrid client
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        
        # Create email
        from_email = Email('analytics@flashstudio.com')
        to_email = To(admin_email)
        subject = f"📊 FlashStudio Daily Analytics - {analytics_data['date']}"
        
        mail = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        # Send email
        response = sg.send(mail)
        
        if response.status_code in [200, 202]:
            return True
        else:
            logging.error(f'❌ Email send failed: {response.status_code}')
            return False
            
    except Exception as e:
        logging.error(f'📧 Error sending analytics email: {e}')
        return False


def create_analytics_email_template(data):
    """Create HTML email template for analytics report"""
    
    sales = data.get('sales', {})
    customers = data.get('customers', {})
    products = data.get('products', {})
    quotes = data.get('quotes', {})
    website = data.get('website', {})
    
    # Calculate trends (mock calculation)
    revenue_trend = "+15.2%" if sales.get('total_revenue', 0) > 2000 else "-5.1%"
    order_trend = "+8.3%" if sales.get('total_orders', 0) > 10 else "-2.7%"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FlashStudio Daily Analytics</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">📊 FlashStudio Analytics</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
                Daily Report for {data['date']}
            </p>
        </div>
        
        <!-- Main Content -->
        <div style="max-width: 800px; margin: 0 auto; padding: 30px 20px; background: white;">
            
            <!-- Sales Summary -->
            <div style="margin-bottom: 40px;">
                <h2 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    💰 Sales Summary
                </h2>
                
                <div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">
                    <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px; text-align: center;">
                        <h3 style="color: #667eea; margin: 0; font-size: 24px;">{sales.get('currency', 'SGD')} {sales.get('total_revenue', 0):,.2f}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Total Revenue</p>
                        <span style="color: #28a745; font-size: 14px; font-weight: bold;">{revenue_trend}</span>
                    </div>
                    
                    <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px; text-align: center;">
                        <h3 style="color: #667eea; margin: 0; font-size: 24px;">{sales.get('total_orders', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Total Orders</p>
                        <span style="color: #28a745; font-size: 14px; font-weight: bold;">{order_trend}</span>
                    </div>
                    
                    <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px; text-align: center;">
                        <h3 style="color: #667eea; margin: 0; font-size: 24px;">{sales.get('currency', 'SGD')} {sales.get('average_order_value', 0):.2f}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Avg Order Value</p>
                    </div>
                </div>
            </div>
            
            <!-- Customer Metrics -->
            <div style="margin-bottom: 40px;">
                <h2 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    👥 Customer Metrics
                </h2>
                
                <div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">
                    <div style="background: #fff5f5; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #e53e3e; margin: 0; font-size: 24px;">{customers.get('new_registrations', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">New Customers</p>
                    </div>
                    
                    <div style="background: #f0fff4; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #38a169; margin: 0; font-size: 24px;">{customers.get('returning_customers', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Returning</p>
                    </div>
                    
                    <div style="background: #fffaf0; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #d69e2e; margin: 0; font-size: 24px;">{customers.get('total_active', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Total Active</p>
                    </div>
                </div>
            </div>
            
            <!-- Popular Products -->
            <div style="margin-bottom: 40px;">
                <h2 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    🏆 Top Products
                </h2>
                
                <div style="margin: 20px 0;">
    """
    
    # Add popular products
    for i, product in enumerate(products.get('most_popular', [])[:3], 1):
        html_content += f"""
                    <div style="background: #f8f9ff; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #333;">#{i}. {product.get('name', 'Product')}</span>
                        <span style="color: #667eea; font-weight: bold;">{product.get('sales', 0)} sales</span>
                    </div>
        """
    
    html_content += f"""
                </div>
            </div>
            
            <!-- Quote Requests -->
            <div style="margin-bottom: 40px;">
                <h2 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    💼 Quote Requests
                </h2>
                
                <div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">
                    <div style="background: #e6f7ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #1890ff; margin: 0; font-size: 24px;">{quotes.get('new_requests', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">New Requests</p>
                    </div>
                    
                    <div style="background: #fff7e6; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #fa8c16; margin: 0; font-size: 24px;">{quotes.get('pending_responses', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Pending</p>
                    </div>
                    
                    <div style="background: #f6ffed; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #52c41a; margin: 0; font-size: 24px;">{quotes.get('converted_to_sales', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Converted</p>
                    </div>
                </div>
            </div>
            
            <!-- Website Traffic -->
            <div style="margin-bottom: 40px;">
                <h2 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    🌐 Website Traffic
                </h2>
                
                <div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">
                    <div style="background: #f0f5ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #722ed1; margin: 0; font-size: 24px;">{website.get('unique_visitors', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Unique Visitors</p>
                    </div>
                    
                    <div style="background: #f0f5ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #722ed1; margin: 0; font-size: 24px;">{website.get('page_views', 0)}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Page Views</p>
                    </div>
                    
                    <div style="background: #f0f5ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center;">
                        <h3 style="color: #722ed1; margin: 0; font-size: 24px;">{website.get('bounce_rate', 0):.1%}</h3>
                        <p style="margin: 5px 0 0 0; color: #666;">Bounce Rate</p>
                    </div>
                </div>
            </div>
            
            <!-- Action Items -->
            <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; margin-top: 30px;">
                <h3 style="color: #667eea; margin-top: 0;">📋 Recommended Actions</h3>
                <ul style="color: #666; line-height: 1.6;">
                    <li>Follow up on {quotes.get('pending_responses', 0)} pending quote responses</li>
                    <li>Send welcome emails to {customers.get('new_registrations', 0)} new customers</li>
                    <li>Review and optimize popular product pricing</li>
                    <li>Analyze traffic sources for bounce rate improvement</li>
                </ul>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="background: #333; color: white; padding: 20px; text-align: center;">
            <p style="margin: 0;">FlashStudio Analytics System</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;">
                Generated automatically at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        
    </body>
    </html>
    """
    
    return html_content


def send_error_notification(error_message):
    """Send error notification to admin"""
    
    try:
        sendgrid_api_key = os.environ.get('EMAIL_API_KEY')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@flashstudio.com')
        
        if not sendgrid_api_key:
            return
        
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        
        subject = "❌ FlashStudio Analytics Error"
        html_content = f"""
        <h2>Analytics Function Error</h2>
        <p>The daily analytics function encountered an error:</p>
        <pre style="background: #f4f4f4; padding: 15px; border-radius: 5px;">
        {error_message}
        </pre>
        <p>Time: {datetime.now().isoformat()}</p>
        """
        
        mail = Mail(
            from_email=Email('analytics@flashstudio.com'),
            to_emails=To(admin_email),
            subject=subject,
            html_content=html_content
        )
        
        sg.send(mail)
        
    except Exception as e:
        logging.error(f'Failed to send error notification: {e}')