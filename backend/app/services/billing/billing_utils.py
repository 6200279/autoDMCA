import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from calendar import monthrange

from app.db.models.subscription import SubscriptionPlan, BillingInterval

logger = logging.getLogger(__name__)


class BillingCalculator:
    """Utility class for billing calculations."""
    
    @staticmethod
    def calculate_proration(
        old_amount: Decimal,
        new_amount: Decimal,
        current_period_start: datetime,
        current_period_end: datetime,
        change_date: Optional[datetime] = None
    ) -> Decimal:
        """Calculate proration amount for plan changes."""
        if change_date is None:
            change_date = datetime.now(timezone.utc)
        
        # Calculate total period duration
        total_period = (current_period_end - current_period_start).total_seconds()
        
        # Calculate remaining period
        remaining_period = (current_period_end - change_date).total_seconds()
        
        if total_period <= 0 or remaining_period <= 0:
            return Decimal('0.00')
        
        # Calculate proration factor
        proration_factor = Decimal(remaining_period / total_period)
        
        # Calculate unused amount from old plan
        unused_old = old_amount * proration_factor
        
        # Calculate prorated amount for new plan
        prorated_new = new_amount * proration_factor
        
        # Return the difference (positive = credit, negative = charge)
        return prorated_new - unused_old
    
    @staticmethod
    def calculate_yearly_discount(monthly_price: Decimal, yearly_price: Decimal) -> Decimal:
        """Calculate yearly discount percentage."""
        if monthly_price <= 0:
            return Decimal('0.00')
        
        annual_monthly_price = monthly_price * 12
        savings = annual_monthly_price - yearly_price
        discount_percentage = (savings / annual_monthly_price) * 100
        
        return discount_percentage.quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_next_billing_date(
        current_date: datetime,
        interval: BillingInterval,
        day_of_month: Optional[int] = None
    ) -> datetime:
        """Calculate next billing date based on interval."""
        if day_of_month is None:
            day_of_month = current_date.day
        
        if interval == BillingInterval.MONTH:
            # Calculate next month
            if current_date.month == 12:
                next_year = current_date.year + 1
                next_month = 1
            else:
                next_year = current_date.year
                next_month = current_date.month + 1
            
            # Handle end of month cases
            _, days_in_next_month = monthrange(next_year, next_month)
            next_day = min(day_of_month, days_in_next_month)
            
            return current_date.replace(
                year=next_year,
                month=next_month,
                day=next_day
            )
        
        elif interval == BillingInterval.YEAR:
            # Add one year
            try:
                return current_date.replace(year=current_date.year + 1)
            except ValueError:
                # Handle leap year case (Feb 29 -> Feb 28)
                return current_date.replace(
                    year=current_date.year + 1,
                    month=2,
                    day=28
                )
        
        return current_date
    
    @staticmethod
    def calculate_usage_overage(
        current_usage: int,
        plan_limit: int,
        overage_price: Decimal = Decimal('0.00')
    ) -> Tuple[int, Decimal]:
        """Calculate usage overage and cost."""
        if current_usage <= plan_limit:
            return 0, Decimal('0.00')
        
        overage_quantity = current_usage - plan_limit
        overage_cost = overage_quantity * overage_price
        
        return overage_quantity, overage_cost
    
    @staticmethod
    def format_currency(amount: Decimal, currency: str = "USD") -> str:
        """Format currency amount for display."""
        if currency.upper() == "USD":
            return f"${amount:.2f}"
        elif currency.upper() == "EUR":
            return f"€{amount:.2f}"
        elif currency.upper() == "GBP":
            return f"£{amount:.2f}"
        else:
            return f"{amount:.2f} {currency.upper()}"


class PlanComparator:
    """Utility class for comparing subscription plans."""
    
    # Plan hierarchy for upgrade/downgrade logic
    PLAN_HIERARCHY = {
        SubscriptionPlan.FREE: 0,
        SubscriptionPlan.BASIC: 1,
        SubscriptionPlan.PROFESSIONAL: 2,
        SubscriptionPlan.ENTERPRISE: 3
    }
    
    @classmethod
    def is_upgrade(cls, from_plan: SubscriptionPlan, to_plan: SubscriptionPlan) -> bool:
        """Check if plan change is an upgrade."""
        from_level = cls.PLAN_HIERARCHY.get(from_plan, 0)
        to_level = cls.PLAN_HIERARCHY.get(to_plan, 0)
        return to_level > from_level
    
    @classmethod
    def is_downgrade(cls, from_plan: SubscriptionPlan, to_plan: SubscriptionPlan) -> bool:
        """Check if plan change is a downgrade."""
        from_level = cls.PLAN_HIERARCHY.get(from_plan, 0)
        to_level = cls.PLAN_HIERARCHY.get(to_plan, 0)
        return to_level < from_level
    
    @classmethod
    def get_plan_change_type(cls, from_plan: SubscriptionPlan, to_plan: SubscriptionPlan) -> str:
        """Get the type of plan change."""
        if cls.is_upgrade(from_plan, to_plan):
            return "upgrade"
        elif cls.is_downgrade(from_plan, to_plan):
            return "downgrade"
        else:
            return "lateral"


class UsageCalculator:
    """Utility class for usage calculations."""
    
    @staticmethod
    def calculate_usage_percentage(current: int, limit: int) -> float:
        """Calculate usage as a percentage of limit."""
        if limit <= 0:
            return 0.0
        return min(100.0, (current / limit) * 100)
    
    @staticmethod
    def get_usage_status(current: int, limit: int) -> str:
        """Get usage status based on current usage."""
        percentage = UsageCalculator.calculate_usage_percentage(current, limit)
        
        if percentage >= 100:
            return "exceeded"
        elif percentage >= 90:
            return "critical"
        elif percentage >= 75:
            return "warning"
        elif percentage >= 50:
            return "moderate"
        else:
            return "low"
    
    @staticmethod
    def days_until_reset() -> int:
        """Calculate days until monthly usage reset."""
        now = datetime.now(timezone.utc)
        
        # Calculate first day of next month
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        
        # Calculate difference
        delta = next_month - now
        return delta.days
    
    @staticmethod
    def get_current_billing_period() -> Tuple[datetime, datetime]:
        """Get current monthly billing period."""
        now = datetime.now(timezone.utc)
        
        # Start of current month
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # End of current month
        _, days_in_month = monthrange(now.year, now.month)
        period_end = period_start.replace(
            day=days_in_month, 
            hour=23, 
            minute=59, 
            second=59, 
            microsecond=999999
        )
        
        return period_start, period_end


class SubscriptionValidator:
    """Utility class for subscription validation."""
    
    @staticmethod
    def validate_plan_change(
        current_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan,
        current_usage: Dict[str, int]
    ) -> Tuple[bool, Optional[str]]:
        """Validate if plan change is allowed based on current usage."""
        if current_plan == new_plan:
            return False, "Cannot change to the same plan"
        
        # If downgrading, check if current usage exceeds new plan limits
        if PlanComparator.is_downgrade(current_plan, new_plan):
            from app.services.billing.stripe_service import SUBSCRIPTION_PLANS
            
            if new_plan not in SUBSCRIPTION_PLANS:
                return False, f"Invalid plan: {new_plan}"
            
            new_limits = SUBSCRIPTION_PLANS[new_plan]["limits"]
            
            # Check each usage metric
            if current_usage.get("protected_profiles", 0) > new_limits["max_protected_profiles"]:
                return False, f"Current protected profiles ({current_usage['protected_profiles']}) exceed new plan limit ({new_limits['max_protected_profiles']})"
            
            # Note: Monthly scans and takedown requests reset each month, so we allow these to exceed temporarily
        
        return True, None
    
    @staticmethod
    def validate_billing_interval(interval: BillingInterval) -> bool:
        """Validate billing interval."""
        return interval in [BillingInterval.MONTH, BillingInterval.YEAR]
    
    @staticmethod
    def validate_trial_period(days: Optional[int]) -> Tuple[bool, Optional[str]]:
        """Validate trial period."""
        if days is None:
            return True, None
        
        if not isinstance(days, int):
            return False, "Trial days must be an integer"
        
        if days < 0:
            return False, "Trial days cannot be negative"
        
        if days > 30:
            return False, "Trial period cannot exceed 30 days"
        
        return True, None


class BillingNotificationHelper:
    """Utility class for billing notification helpers."""
    
    @staticmethod
    def should_send_trial_ending_notification(trial_end: datetime, days_before: int = 3) -> bool:
        """Check if trial ending notification should be sent."""
        now = datetime.now(timezone.utc)
        notification_date = trial_end - timedelta(days=days_before)
        
        return now >= notification_date and now < trial_end
    
    @staticmethod
    def should_send_payment_failed_notification(failure_count: int, max_retries: int = 3) -> bool:
        """Check if payment failure notification should be sent."""
        return failure_count >= max_retries
    
    @staticmethod
    def should_send_usage_warning(usage_percentage: float, warning_threshold: float = 80.0) -> bool:
        """Check if usage warning notification should be sent."""
        return usage_percentage >= warning_threshold
    
    @staticmethod
    def get_renewal_reminder_dates(current_period_end: datetime) -> list[datetime]:
        """Get dates when renewal reminders should be sent."""
        reminder_dates = []
        
        # 7 days before
        reminder_dates.append(current_period_end - timedelta(days=7))
        
        # 3 days before
        reminder_dates.append(current_period_end - timedelta(days=3))
        
        # 1 day before
        reminder_dates.append(current_period_end - timedelta(days=1))
        
        return reminder_dates


class InvoiceFormatter:
    """Utility class for invoice formatting."""
    
    @staticmethod
    def generate_invoice_number(
        user_id: int,
        created_date: datetime,
        sequence: Optional[int] = None
    ) -> str:
        """Generate a formatted invoice number."""
        year = created_date.year
        month = created_date.month
        
        if sequence is None:
            # Use timestamp-based sequence
            sequence = int(created_date.timestamp()) % 10000
        
        return f"INV-{year}-{month:02d}-{user_id:06d}-{sequence:04d}"
    
    @staticmethod
    def format_line_item_description(
        plan: SubscriptionPlan,
        interval: BillingInterval,
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """Format line item description for subscription."""
        plan_name = plan.value.title()
        interval_text = "Monthly" if interval == BillingInterval.MONTH else "Annual"
        
        start_str = period_start.strftime("%b %d, %Y")
        end_str = period_end.strftime("%b %d, %Y")
        
        return f"{plan_name} Plan ({interval_text}) - {start_str} to {end_str}"
    
    @staticmethod
    def calculate_invoice_totals(line_items: list[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Calculate invoice totals from line items."""
        subtotal = sum(Decimal(str(item.get('amount', 0))) for item in line_items)
        tax = Decimal('0.00')  # Tax calculation would be implemented based on requirements
        discount = Decimal('0.00')  # Discount would come from promotional codes, etc.
        total = subtotal + tax - discount
        
        return {
            'subtotal': subtotal,
            'tax': tax,
            'discount': discount,
            'total': total
        }


class SubscriptionMetrics:
    """Utility class for subscription metrics and analytics."""
    
    @staticmethod
    def calculate_monthly_recurring_revenue(subscriptions: list[Dict[str, Any]]) -> Decimal:
        """Calculate total MRR from active subscriptions."""
        mrr = Decimal('0.00')
        
        for subscription in subscriptions:
            if subscription.get('status') == 'active':
                amount = Decimal(str(subscription.get('amount', 0)))
                interval = subscription.get('interval', 'month')
                
                if interval == 'month':
                    mrr += amount
                elif interval == 'year':
                    mrr += amount / 12
        
        return mrr.quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_customer_lifetime_value(
        monthly_revenue: Decimal,
        churn_rate: float,
        gross_margin: float = 0.8
    ) -> Decimal:
        """Calculate customer lifetime value."""
        if churn_rate <= 0:
            return Decimal('0.00')
        
        # CLV = (Monthly Revenue * Gross Margin) / Churn Rate
        clv = (monthly_revenue * Decimal(str(gross_margin))) / Decimal(str(churn_rate))
        return clv.quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_churn_rate(
        customers_start: int,
        customers_lost: int,
        period_days: int = 30
    ) -> float:
        """Calculate churn rate for a given period."""
        if customers_start <= 0:
            return 0.0
        
        monthly_churn = (customers_lost / customers_start)
        
        # Convert to monthly rate if needed
        if period_days != 30:
            monthly_churn = monthly_churn * (30 / period_days)
        
        return round(monthly_churn * 100, 2)  # Return as percentage