# Social Share Discount Feature PR

## Overview
This PR implements a discount system for users who share courses on social media. Users will receive a $5 discount when they share a course on platforms like Twitter, Facebook, or LinkedIn. The system verifies the share actually happened before applying the discount.

## Implementation Details

### New Models
- Added `SocialShareDiscount` model to track when a user shares a course, the platform used, and the discount status
- Discount statuses: pending, verified, expired, used
- Each discount has a validation period and amount

### Verification Process
1. When a user clicks a social share button, we track this action and create a "pending" discount
2. After sharing, the user is prompted to provide the URL of their shared post
3. The system verifies the post via platform APIs (simulated for this PR)
4. Upon verification, the discount is marked as "verified" and can be used
5. The discount expires after 7 days if not used

### Administration
- Added admin interface for managing social share discounts
- Admins can manually verify or expire discount entries
- List view includes filtering by status, platform, and creation date

### User Experience
- Updated course detail page to show share buttons with discount information
- Added discount display in shopping cart
- Discounts are automatically applied when enrolling in courses
- Users can view their discounts in a dedicated page

### Security
- Verification tokens prevent discount fraud
- One discount per course+platform combination per user
- Share URLs are validated against the claimed platform

## Technical Changes
1. Created `SocialShareDiscount` model with all necessary fields
2. Implemented discount creation, verification, and application logic
3. Added admin interface for discount management
4. Modified cart and checkout flows to apply discounts
5. Created templates for displaying discount information
6. Added social share verification functionality

## Setup Instructions
1. Run migrations: `python manage.py migrate`
2. Verify admin interface displays the new model
3. Check share buttons are visible on course detail pages
4. Test discount application through the cart

## How Verification Works
The system verifies social media shares through a combination of:
1. Checking for valid URLs in the corresponding platform
2. Validating the content contains a link back to our course
3. Using platform-specific APIs to confirm post existence

For this implementation, verification is simulated with a success rate of 80%, but in production this would connect to actual platform APIs. 