from django import template

register = template.Library()


@register.filter
def filter_by_milestone(rewards, milestone_id):
    """Filter rewards by milestone ID."""
    for reward in rewards:
        if reward.milestone.id == milestone_id:
            return reward
    return None
