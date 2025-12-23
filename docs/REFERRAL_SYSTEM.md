# Referral and Rewards System Documentation

## Overview

The Alpha One Labs referral and rewards system is designed to incentivize users to invite friends and grow the community. The system features:

- **Tiered Milestones**: Progressive rewards as users refer more people
- **Dual Rewards**: Both monetary earnings and points for each milestone
- **Referral Dashboard**: Comprehensive view of referrals, earnings, and progress
- **Social Sharing**: Easy sharing via social media, email, and direct link
- **Automated Notifications**: Email alerts when milestones are reached

## Key Features

### 1. Referral Codes

Every user automatically receives a unique referral code upon registration. This code can be shared in two formats:

- **Standard URL**: `https://example.com/ref/ABC123/`
- **Legacy Query Parameter**: `https://example.com/?ref=ABC123`

### 2. Referral Milestones

The system includes pre-configured milestones:

| Milestone | Referrals | Cash Reward | Points | Badge Icon |
|-----------|-----------|-------------|--------|------------|
| First Referral | 1 | $5.00 | 100 | ⭐ Star |
| Bronze Referrer | 5 | $10.00 | 250 | 🥉 Medal |
| Silver Referrer | 10 | $25.00 | 500 | 🏆 Trophy |
| Gold Referrer | 25 | $75.00 | 1000 | 👑 Crown |
| Platinum Referrer | 50 | $200.00 | 2500 | 💎 Gem |
| Diamond Referrer | 100 | $500.00 | 5000 | 💎 Diamond |

Administrators can create, modify, or deactivate milestones through the Django admin panel.

### 3. Reward Distribution

**When a referral occurs:**
1. A new user signs up using a referral link
2. The `referred_by` relationship is established
3. When the referred user enrolls in their first course:
   - The referrer's milestone progress is checked
   - Any newly reached milestones are awarded
   - Cash rewards are added to `referral_earnings`
   - Points are added to the user's points balance
   - Email notifications are sent

**For Teachers:**
- Additional $5 bonus for the first student referral
- Standard milestone rewards also apply

### 4. Referral Dashboard

Users can access their personalized dashboard at `/referrals/dashboard/` which shows:

- **Stats Overview**: Total referrals, enrollments, earnings, and points
- **Referral Link**: Copy and share functionality
- **Social Sharing**: One-click sharing to Twitter, Facebook, LinkedIn, and email
- **Progress Tracker**: Visual progress bar to next milestone
- **Milestone List**: All available milestones with achievement status
- **Rewards History**: List of earned rewards and their claim status
- **Referrals Table**: List of all referred users with their status

## Technical Implementation

### Models

#### ReferralMilestone
```python
class ReferralMilestone(models.Model):
    referral_count = models.PositiveIntegerField(unique=True)
    monetary_reward = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    points_reward = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    badge_icon = models.CharField(max_length=100, default="fas fa-trophy")
    is_active = models.BooleanField(default=True)
```

#### ReferralReward
```python
class ReferralReward(models.Model):
    user = models.ForeignKey(User, related_name="referral_rewards")
    milestone = models.ForeignKey(ReferralMilestone, related_name="rewards")
    earned_at = models.DateTimeField(auto_now_add=True)
    monetary_amount = models.DecimalField(max_digits=10, decimal_places=2)
    points_amount = models.PositiveIntegerField()
    is_claimed = models.BooleanField(default=False)
```

### Profile Methods

#### `check_referral_milestones()`
Checks if the user has reached any new milestones and awards rewards:
- Returns a list of newly earned `ReferralReward` objects
- Adds monetary earnings to profile
- Creates point records
- Does not award duplicate rewards

#### `next_referral_milestone`
Property that returns the next milestone the user can reach.

#### `referral_progress_percentage`
Property that calculates percentage progress to the next milestone.

### Views

#### `referral_dashboard(request)`
Displays the user's referral dashboard with:
- Referral statistics
- Earned rewards
- Available milestones
- Progress tracking
- Referral list

### Email Notifications

The system sends two types of emails:

1. **Standard Referral Reward Email**: Sent for legacy $5 rewards
2. **Milestone Reward Email**: Sent when a milestone is achieved, includes:
   - Milestone title and description
   - Monetary reward amount
   - Points earned
   - Total referral statistics

## Admin Configuration

### Managing Milestones

1. Navigate to **Django Admin** → **Web** → **Referral Milestones**
2. Create/Edit milestones:
   - Set referral count threshold
   - Define monetary and points rewards
   - Add descriptive title and description
   - Choose badge icon (FontAwesome class)
   - Toggle active status

### Viewing Rewards

1. Navigate to **Django Admin** → **Web** → **Referral Rewards**
2. Filter by:
   - User
   - Milestone
   - Claim status
   - Date earned

## Integration Points

### User Signup Flow
1. User clicks referral link (e.g., `/ref/ABC123/`)
2. Referral code is stored in session
3. User completes signup
4. `handle_referral()` is called with the referral code
5. Referrer relationship is established
6. Milestone check is performed

### Course Enrollment Flow
1. Referred user enrolls in their first course
2. `enroll_course()` view checks for referral relationship
3. Milestones are checked and rewards awarded
4. Notifications are sent

### Signals
The system uses the existing referral handling in:
- `web/referrals.py` - `handle_referral()` and email functions
- `web/views.py` - `enroll_course()` - milestone checking

## API Endpoints

While there are no dedicated API endpoints, the referral system integrates with:

- `GET /ref/<code>/` - Handle referral link and redirect to homepage
- `GET /referrals/dashboard/` - Referral dashboard (requires login)

## Template Tags

### referral_filters.py
```python
@register.filter
def filter_by_milestone(rewards, milestone_id):
    """Filter rewards by milestone ID."""
```

Usage in templates:
```django
{% load referral_filters %}
{% with earned=earned_rewards|filter_by_milestone:milestone.id %}
  {% if earned %}
    <!-- Show earned badge -->
  {% endif %}
{% endwith %}
```

## Testing

The system includes comprehensive tests in `web/tests/test_referral_rewards.py`:

- Milestone creation and validation
- First referral milestone triggering
- Multiple milestone progression
- No duplicate reward prevention
- Progress calculation
- Dashboard view rendering
- Inactive milestone handling

Run tests with:
```bash
python manage.py test web.tests.test_referral_rewards
```

## Future Enhancements

Potential improvements to consider:

1. **Referral Analytics**: Track click-through rates, conversion rates
2. **Custom Milestones**: Allow users to create personal goals
3. **Referral Competitions**: Time-limited contests with special prizes
4. **Referral Tiers**: Different reward structures for different user types
5. **Withdrawal System**: Allow users to withdraw referral earnings
6. **Referral Bonuses**: Special events with increased rewards
7. **Team Referrals**: Group-based referral challenges

## Troubleshooting

### Common Issues

**Issue**: Milestone not triggering
- **Solution**: Check that milestone is active (`is_active=True`)
- **Solution**: Verify referral count threshold is correct
- **Solution**: Ensure user has actual referrals (check `Profile.referrals.count()`)

**Issue**: Duplicate rewards
- **Solution**: System prevents duplicates via `unique_together` constraint on `ReferralReward`
- **Solution**: `check_referral_milestones()` excludes already-earned rewards

**Issue**: Points not appearing
- **Solution**: Check that Points.add_points() is being called
- **Solution**: Verify Points table in admin panel

**Issue**: Email not sending
- **Solution**: Check email configuration in settings
- **Solution**: Emails are sent with `fail_silently=True` - check logs

## Security Considerations

1. **Unique Codes**: Referral codes are unique and generated securely
2. **No Gaming**: System tracks actual user registrations and enrollments
3. **Session-based**: Referral codes stored in session, preventing URL manipulation
4. **Rate Limiting**: Consider implementing rate limiting for referral signups
5. **Fraud Detection**: Monitor for suspicious patterns in referral activity

## Support

For questions or issues with the referral system:

1. Check this documentation
2. Review test cases for usage examples
3. Examine admin panel for configuration
4. Contact development team for technical support
