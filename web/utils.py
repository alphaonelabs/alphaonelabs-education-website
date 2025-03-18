import requests
from django.conf import settings

from web.models import Cart


def send_slack_message(message):
    """Send message to Slack webhook"""
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return False

    try:
        response = requests.post(webhook_url, json={"text": message})
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:.2f}"


def get_or_create_cart(request):
    """Helper function to get or create a cart for both logged in and guest users."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def validate_quiz_has_questions(quiz):
    """
    Validate that a quiz has at least one question.
    
    Args:
        quiz: Quiz object to validate
        
    Returns:
        tuple: (is_valid, message)
    """
    question_count = quiz.questions.count()
    if question_count == 0:
        return False, "This quiz has no questions."
    
    # Check each question has at least one correct option
    invalid_questions = []
    for question in quiz.questions.all():
        if not question.options.filter(is_correct=True).exists():
            invalid_questions.append(question.question_text)
    
    if invalid_questions:
        return False, f"The following questions have no correct answer: {', '.join(invalid_questions)}"
    
    return True, "Quiz is valid"
 
