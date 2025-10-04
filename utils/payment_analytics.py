"""
Payment Analytics Service         try:
            # Calculate revenue metrics
            total_revenue = db.session.query(func.sum(Order.amount_cents)).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status == 'paid'
            ).scalar() or 0
            total_revenue = total_revenue / 100  # Convert cents to dollarsudio
Provides comprehensive payment metrics, KPIs, and business intelligence
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, text
from models import db, Order, OrderItem, Product, User
from utils.stripe_service import stripe_service
import logging

logger = logging.getLogger(__name__)

class PaymentAnalytics:
    """Comprehensive payment analytics and business intelligence service"""
    
    @staticmethod
    def get_revenue_summary(days: int = 30) -> Dict[str, Any]:
        """
        Get revenue summary for specified period
        
        Args:
            days: Number of days to analyze (default 30)
            
        Returns:
            Dict with revenue metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Current period revenue
            current_revenue = db.session.query(
                func.sum(Order.amount_cents)
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            current_revenue = current_revenue / 100  # Convert cents to dollars
            
            # Previous period revenue (for comparison)
            prev_start = start_date - timedelta(days=days)
            prev_revenue = db.session.query(
                func.sum(Order.amount_cents)
            ).filter(
                and_(
                    Order.created_at >= prev_start,
                    Order.created_at < start_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            prev_revenue = prev_revenue / 100  # Convert cents to dollars
            
            # Calculate growth
            growth_rate = 0
            if prev_revenue > 0:
                growth_rate = ((current_revenue - prev_revenue) / prev_revenue) * 100
            
            # Order count
            order_count = db.session.query(func.count(Order.id)).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            
            # Get average order value
            avg_order_value = db.session.query(func.avg(Order.amount_cents)).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status == 'paid'
            ).scalar() or 0
            avg_order_value = avg_order_value / 100 if avg_order_value else 0  # Convert cents to dollars
            
            return {
                'current_revenue': float(current_revenue),
                'previous_revenue': float(prev_revenue),
                'growth_rate': round(growth_rate, 2),
                'order_count': order_count,
                'average_order_value': round(avg_order_value, 2),
                'period_days': days,
                'currency': 'USD'
            }
            
        except Exception as e:
            logger.error(f"Error calculating revenue summary: {e}")
            return {
                'current_revenue': 0,
                'previous_revenue': 0,
                'growth_rate': 0,
                'order_count': 0,
                'average_order_value': 0,
                'period_days': days,
                'currency': 'USD',
                'error': str(e)
            }
    
    @staticmethod
    def get_payment_success_rate(days: int = 30) -> Dict[str, Any]:
        """
        Calculate payment success rate and failure analysis
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with success rate metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Total payment attempts
            total_orders = db.session.query(func.count(Order.id)).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            ).scalar() or 0
            
            # Successful payments
            successful_orders = db.session.query(func.count(Order.id)).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            
            # Failed payments
            failed_orders = db.session.query(func.count(Order.id)).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['failed', 'cancelled'])
                )
            ).scalar() or 0
            
            # Pending payments
            pending_orders = total_orders - successful_orders - failed_orders
            
            # Calculate success rate
            success_rate = (successful_orders / total_orders * 100) if total_orders > 0 else 0
            failure_rate = (failed_orders / total_orders * 100) if total_orders > 0 else 0
            
            return {
                'total_attempts': total_orders,
                'successful_payments': successful_orders,
                'failed_payments': failed_orders,
                'pending_payments': pending_orders,
                'success_rate': round(success_rate, 2),
                'failure_rate': round(failure_rate, 2),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error calculating payment success rate: {e}")
            return {
                'total_attempts': 0,
                'successful_payments': 0,
                'failed_payments': 0,
                'pending_payments': 0,
                'success_rate': 0,
                'failure_rate': 0,
                'period_days': days,
                'error': str(e)
            }
    
    @staticmethod
    def get_daily_revenue_chart(days: int = 30) -> Dict[str, Any]:
        """
        Get daily revenue data for chart visualization
        
        Args:
            days: Number of days to include
            
        Returns:
            Dict with chart data
        """
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # Query daily revenue
            daily_revenue = db.session.query(
                func.date(Order.created_at).label('date'),
                func.sum(Order.amount_cents).label('revenue'),
                func.count(Order.id).label('orders')
            ).filter(
                and_(
                    func.date(Order.created_at) >= start_date,
                    func.date(Order.created_at) <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).group_by(
                func.date(Order.created_at)
            ).order_by(
                func.date(Order.created_at)
            ).all()
            
            # Create complete date range with zero values for missing days
            chart_data = []
            current_date = start_date
            
            # Convert query results to dict for easy lookup
            revenue_dict = {row.date: {'revenue': float(row.revenue) / 100, 'orders': row.orders} 
                          for row in daily_revenue}
            
            while current_date <= end_date:
                data = revenue_dict.get(current_date, {'revenue': 0, 'orders': 0})
                chart_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'revenue': data['revenue'],
                    'orders': data['orders']
                })
                current_date += timedelta(days=1)
            
            return {
                'chart_data': chart_data,
                'period_days': days,
                'total_points': len(chart_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating daily revenue chart: {e}")
            return {
                'chart_data': [],
                'period_days': days,
                'total_points': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_top_products(days: int = 30, limit: int = 10) -> Dict[str, Any]:
        """
        Get top-selling products by revenue and quantity
        
        Args:
            days: Number of days to analyze
            limit: Maximum number of products to return
            
        Returns:
            Dict with top products data
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Top products by revenue
            top_by_revenue = db.session.query(
                Product.title,
                Product.id,
                func.sum(OrderItem.unit_price_cents * OrderItem.quantity).label('revenue'),
                func.sum(OrderItem.quantity).label('total_quantity')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).group_by(
                Product.id, Product.title
            ).order_by(
                func.sum(OrderItem.unit_price_cents * OrderItem.quantity).desc()
            ).limit(limit).all()
            
            # Top products by quantity
            top_by_quantity = db.session.query(
                Product.title,
                Product.id,
                func.sum(OrderItem.quantity).label('total_quantity'),
                func.sum(OrderItem.unit_price_cents * OrderItem.quantity).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).group_by(
                Product.id, Product.title
            ).order_by(
                func.sum(OrderItem.quantity).desc()
            ).limit(limit).all()
            
            # Format results
            revenue_list = [
                {
                    'product_name': row.title,
                    'product_id': row.id,
                    'revenue': float(row.revenue) / 100,  # Convert cents to dollars
                    'quantity': row.total_quantity
                }
                for row in top_by_revenue
            ]
            
            quantity_list = [
                {
                    'product_name': row.title,
                    'product_id': row.id,
                    'quantity': row.total_quantity,
                    'revenue': float(row.revenue) / 100  # Convert cents to dollars
                }
                for row in top_by_quantity
            ]
            
            return {
                'top_by_revenue': revenue_list,
                'top_by_quantity': quantity_list,
                'period_days': days,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Error getting top products: {e}")
            return {
                'top_by_revenue': [],
                'top_by_quantity': [],
                'period_days': days,
                'limit': limit,
                'error': str(e)
            }
    
    @staticmethod
    def get_customer_metrics(days: int = 30) -> Dict[str, Any]:
        """
        Get customer acquisition and behavior metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with customer metrics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # New customers (users who made their first order in this period)
            new_customers = db.session.query(
                func.count(func.distinct(Order.user_id))
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            
            # Returning customers (users who made multiple orders)
            returning_customers = db.session.query(
                func.count(Order.user_id)
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).having(
                func.count(Order.id) > 1
            ).scalar() or 0
            
            # Customer lifetime value (average)
            customer_ltv = db.session.query(
                func.avg(func.sum(Order.amount_cents))
            ).filter(
                Order.status.in_(['completed', 'paid'])
            ).group_by(Order.user_id).scalar() or 0
            
            # Total unique customers
            total_customers = db.session.query(
                func.count(func.distinct(Order.user_id))
            ).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['completed', 'paid'])
                )
            ).scalar() or 0
            
            return {
                'new_customers': new_customers,
                'returning_customers': returning_customers,
                'total_customers': total_customers,
                'customer_lifetime_value': round(float(customer_ltv), 2),
                'retention_rate': round((returning_customers / total_customers * 100) if total_customers > 0 else 0, 2),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error calculating customer metrics: {e}")
            return {
                'new_customers': 0,
                'returning_customers': 0,
                'total_customers': 0,
                'customer_lifetime_value': 0,
                'retention_rate': 0,
                'period_days': days,
                'error': str(e)
            }
    
    @staticmethod
    def get_comprehensive_dashboard(days: int = 30) -> Dict[str, Any]:
        """
        Get complete dashboard data in a single call
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with all dashboard metrics
        """
        return {
            'revenue_summary': PaymentAnalytics.get_revenue_summary(days),
            'payment_success': PaymentAnalytics.get_payment_success_rate(days),
            'daily_revenue_chart': PaymentAnalytics.get_daily_revenue_chart(days),
            'top_products': PaymentAnalytics.get_top_products(days),
            'customer_metrics': PaymentAnalytics.get_customer_metrics(days),
            'generated_at': datetime.utcnow().isoformat(),
            'period_days': days
        }

# Initialize analytics service
payment_analytics = PaymentAnalytics()