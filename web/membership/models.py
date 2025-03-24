from django.db import models
from django.conf import settings
from django.utils import timezone

class MembershipPlan(models.Model):
    """
    Model representing different membership plans available in the system.
    """
    BILLING_PERIOD_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('both', 'Both'),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')
    features = models.JSONField(default=list, help_text="List of features included in this plan")
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, help_text="Order in which to display the plan")
    
    # Stripe IDs for the price objects
    stripe_monthly_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_yearly_price_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'price']
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        # Set price based on the billing period for display purposes
        if self.billing_period == 'monthly' and self.monthly_price:
            self.price = self.monthly_price
        elif self.billing_period == 'yearly' and self.yearly_price:
            self.price = self.yearly_price
        elif self.billing_period == 'both':
            # Default to monthly for display
            if self.monthly_price:
                self.price = self.monthly_price
        
        super().save(*args, **kwargs)
    
    @property
    def yearly_savings(self):
        """Calculate the savings percentage when paying yearly."""
        if not self.monthly_price or not self.yearly_price:
            return 0
        
        monthly_yearly_cost = self.monthly_price * 12
        yearly_cost = self.yearly_price
        
        if monthly_yearly_cost <= 0:
            return 0
            
        savings = (monthly_yearly_cost - yearly_cost) / monthly_yearly_cost * 100
        return round(savings)


class UserMembership(models.Model):
    """
    Model representing a user's membership status.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('trialing', 'Trial'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('unpaid', 'Unpaid'),
        ('inactive', 'Inactive'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='membership'
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='memberships'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    # Stripe specific fields
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s membership"
    
    @property
    def is_active(self):
        """Check if the membership is active."""
        return self.status in ('active', 'trialing')
    
    @property
    def is_canceled(self):
        """Check if the membership has been canceled."""
        return self.status == 'canceled' or self.cancel_at_period_end
    
    @property
    def days_until_expiration(self):
        """Calculate the number of days until the membership expires."""
        if not self.end_date:
            return None
        
        now = timezone.now()
        if now > self.end_date:
            return 0
            
        delta = self.end_date - now
        return delta.days
    
    def get_next_billing_date(self):
        """Get the next billing date for display."""
        if self.end_date:
            return self.end_date
        return None


class MembershipSubscriptionEvent(models.Model):
    """
    Model to track membership subscription events.
    """
    EVENT_TYPES = (
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('canceled', 'Canceled'),
        ('reactivated', 'Reactivated'),
        ('payment_succeeded', 'Payment Succeeded'),
        ('payment_failed', 'Payment Failed'),
        ('past_due', 'Past Due'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='membership_events'
    )
    membership = models.ForeignKey(
        UserMembership,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    stripe_event_id = models.CharField(max_length=100, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.event_type} event for {self.user.username}" 