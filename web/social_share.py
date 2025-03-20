import logging
import random
import re
import uuid
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import requests

from .models import SocialShareDiscount

logger = logging.getLogger(__name__)


def create_social_share_discount(user, course, platform):
    """
    Create a new social share discount.
    
    Args:
        user: User who shared the course
        course: Course that was shared
        platform: Social media platform used for sharing
        
    Returns:
        dict: Info about created social share discount
    """
    # Check if user already has a valid discount for this course and platform
    existing_discount = SocialShareDiscount.objects.filter(
        user=user,
        course=course,
        platform=platform,
        status__in=["pending", "verified"]
    ).first()
    
    if existing_discount:
        if existing_discount.status == "verified":
            return {
                "status": "success",
                "message": "You already have a verified discount for this course.",
                "discount": existing_discount,
                "is_new": False
            }
        else:
            return {
                "status": "success",
                "message": "Your discount is pending verification.",
                "discount": existing_discount,
                "is_new": False
            }
    
    # Create new discount
    discount = SocialShareDiscount.objects.create(
        user=user,
        course=course,
        platform=platform,
        discount_amount=5.00,  # Default $5 discount
        status="pending"
    )
    
    return {
        "status": "success",
        "message": "Discount created! We'll verify your share and apply the discount.",
        "discount": discount,
        "is_new": True
    }


def verify_social_share(discount_obj):
    """
    Verify that a social media share actually exists.
    This is a simplified version - in a real implementation, 
    you would need to use the appropriate platform APIs.
    
    Args:
        discount_obj: SocialShareDiscount object to verify
        
    Returns:
        bool: Whether verification was successful
    """
    if not discount_obj.share_url:
        logger.warning(f"No share URL provided for discount {discount_obj.id}")
        return False
    
    platform = discount_obj.platform
    share_url = discount_obj.share_url
    
    # Different verification methods depending on platform
    # Note: This is a simplified example implementation
    try:
        if platform == "twitter":
            # In a real implementation, you would use the Twitter API
            # For now, we'll just check if the URL seems valid
            return verify_twitter_share(share_url, discount_obj.course)
        
        elif platform == "facebook":
            # In a real implementation, you would use the Facebook Graph API
            return verify_facebook_share(share_url, discount_obj.course)
        
        elif platform == "linkedin":
            # In a real implementation, you would use the LinkedIn API
            return verify_linkedin_share(share_url, discount_obj.course)
        
        else:
            logger.error(f"Unknown platform: {platform}")
            return False
    
    except Exception as e:
        logger.exception(f"Error verifying social share: {e}")
        return False


def verify_twitter_share(share_url, course):
    """
    Verify a Twitter share using the Twitter API.
    This is a simplified version that demonstrates the concept.
    
    In a real implementation, you would:
    1. Use Twitter's API with proper authentication
    2. Fetch the tweet and check its content
    3. Verify it contains a link to your course
    
    Args:
        share_url: URL of the Twitter share
        course: Course object that was shared
        
    Returns:
        bool: Whether verification was successful
    """
    # This simulates API verification
    # In reality, you would use the Twitter API client
    try:
        # Parse tweet ID from URL
        tweet_id_match = re.search(r'/status/(\d+)', share_url)
        if not tweet_id_match:
            logger.warning(f"Could not extract tweet ID from URL: {share_url}")
            return False
        
        # In a real implementation:
        # twitter_client = TwitterClient(api_key, api_secret)
        # tweet = twitter_client.get_tweet(tweet_id)
        # return course.slug in tweet.text or request.get_host() in tweet.text
        
        # For now, return True 80% of the time to simulate verification
        return random.random() < 0.8
    
    except Exception as e:
        logger.exception(f"Error verifying Twitter share: {e}")
        return False


def verify_facebook_share(share_url, course):
    """
    Verify a Facebook share using the Facebook Graph API.
    This is a simplified version that demonstrates the concept.
    
    Args:
        share_url: URL of the Facebook share
        course: Course object that was shared
        
    Returns:
        bool: Whether verification was successful
    """
    # This simulates API verification
    # In reality, you would use the Facebook Graph API client with proper permissions
    try:
        # For now, return True 80% of the time to simulate verification
        return random.random() < 0.8
    
    except Exception as e:
        logger.exception(f"Error verifying Facebook share: {e}")
        return False


def verify_linkedin_share(share_url, course):
    """
    Verify a LinkedIn share using the LinkedIn API.
    This is a simplified version that demonstrates the concept.
    
    Args:
        share_url: URL of the LinkedIn share
        course: Course object that was shared
        
    Returns:
        bool: Whether verification was successful
    """
    # This simulates API verification
    # In reality, you would use the LinkedIn API client with proper permissions
    try:
        # For now, return True 80% of the time to simulate verification
        return random.random() < 0.8
    
    except Exception as e:
        logger.exception(f"Error verifying LinkedIn share: {e}")
        return False


def notify_user_about_discount(discount_obj):
    """
    Send an email notification to the user about their discount.
    
    Args:
        discount_obj: SocialShareDiscount object
    """
    subject = f"Your ${discount_obj.discount_amount} discount for {discount_obj.course.title}"
    
    if discount_obj.status == "verified":
        message = (
            f"Congratulations! We've verified your share on {discount_obj.get_platform_display()} "
            f"and have applied a ${discount_obj.discount_amount} discount to {discount_obj.course.title}. "
            f"This discount will be automatically applied when you enroll in the course. "
            f"Your discount expires on {discount_obj.expires_at.strftime('%Y-%m-%d')}."
        )
    else:
        message = (
            f"Thank you for sharing {discount_obj.course.title} on {discount_obj.get_platform_display()}. "
            f"We're currently verifying your share. Once verified, you'll receive a "
            f"${discount_obj.discount_amount} discount on the course."
        )
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[discount_obj.user.email],
        fail_silently=True,
    )


def apply_social_share_discount(user, course):
    """
    Apply a social share discount if the user has one for the course.
    
    Args:
        user: User to check for discounts
        course: Course to apply discount to
        
    Returns:
        tuple: (original_price, discounted_price, discount_amount, discount_obj)
    """
    # Get valid discounts for this user and course
    discount = SocialShareDiscount.objects.filter(
        user=user,
        course=course,
        status="verified",
        expires_at__gt=timezone.now()
    ).first()
    
    if not discount:
        return course.price, course.price, 0, None
    
    # Apply the discount
    discount_amount = min(discount.discount_amount, course.price)
    discounted_price = max(course.price - discount_amount, 0)
    
    return course.price, discounted_price, discount_amount, discount 