from django.core.management.base import BaseCommand
from django.utils.text import slugify
from web.models import MembershipPlan


class Command(BaseCommand):
    help = 'Populates the database with sample membership plans'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample membership plans...')
        
        # Delete existing plans if needed
        if options.get('delete_existing'):
            MembershipPlan.objects.all().delete()
            self.stdout.write('Deleted existing membership plans')
        
        # Try creating plans directly rather than get_or_create to avoid potential issues
        # with missing or renamed columns in the database
        
        # Check if plans already exist
        if MembershipPlan.objects.filter(slug='basic').exists():
            self.stdout.write('Basic plan already exists')
        else:
            try:
                # Create Basic plan
                basic = MembershipPlan(
                    name='Basic',
                    slug='basic',
                    description='Essential features for learners getting started',
                    is_active=True,
                    is_popular=False,
                    order=1
                )
                # Set fields separately to handle missing fields gracefully
                basic.price_monthly = 9.99
                basic.price_yearly = 99.99
                basic.billing_period = 'both'
                basic.features = [
                    'Access to basic courses',
                    'Community forum access',
                    'Email support within 48 hours',
                    'Monthly learning webinars',
                    'Access to learning path guides'
                ]
                basic.stripe_monthly_price_id = 'price_1OaXkRLkswLmMQQZlkVYMVqM'
                basic.stripe_yearly_price_id = 'price_1OaXkRLkswLmMQQZ1sWBB0TJ'
                basic.save()
                self.stdout.write(f'Created Basic plan')
            except Exception as e:
                self.stderr.write(f'Error creating Basic plan: {str(e)}')
        
        # Check if Pro plan already exists
        if MembershipPlan.objects.filter(slug='pro').exists():
            self.stdout.write('Pro plan already exists')
        else:
            try:
                # Create Pro plan
                pro = MembershipPlan(
                    name='Pro',
                    slug='pro',
                    description='Perfect for dedicated learners looking to advance quickly',
                    is_active=True,
                    is_popular=True,
                    order=2
                )
                # Set fields separately to handle missing fields gracefully
                pro.price_monthly = 19.99
                pro.price_yearly = 199.99
                pro.billing_period = 'both'
                pro.features = [
                    'All Basic features',
                    'Access to all courses and tutorials',
                    'Priority email support within 24 hours',
                    'Weekly group coaching sessions',
                    'Downloadable course materials',
                    'Project reviews and feedback',
                    'Assignment grading and feedback'
                ]
                pro.stripe_monthly_price_id = 'price_1OaXlDLkswLmMQQZVqS8KJPM'
                pro.stripe_yearly_price_id = 'price_1OaXlDLkswLmMQQZJdjMCQz7'
                pro.save()
                self.stdout.write(f'Created Pro plan')
            except Exception as e:
                self.stderr.write(f'Error creating Pro plan: {str(e)}')
        
        # Check if Premium plan already exists
        if MembershipPlan.objects.filter(slug='premium').exists():
            self.stdout.write('Premium plan already exists')
        else:
            try:
                # Create Premium plan
                premium = MembershipPlan(
                    name='Premium',
                    slug='premium',
                    description='Ultimate learning experience with personalized coaching',
                    is_active=True,
                    is_popular=False,
                    order=3
                )
                # Set fields separately to handle missing fields gracefully
                premium.price_monthly = 49.99
                premium.price_yearly = 499.99
                premium.billing_period = 'both'
                premium.features = [
                    'All Pro features',
                    'Monthly 1-on-1 coaching sessions',
                    'Priority support with dedicated advisor',
                    'Custom learning path creation',
                    'Job placement assistance',
                    'Certificate of completion for all courses',
                    'Access to exclusive premium content',
                    'Early access to new courses',
                    'Unlimited project submissions'
                ]
                premium.stripe_monthly_price_id = 'price_1OaXmSLkswLmMQQZhC5ftxe0'
                premium.stripe_yearly_price_id = 'price_1OaXmSLkswLmMQQZXcSPXVfq'
                premium.save()
                self.stdout.write(f'Created Premium plan')
            except Exception as e:
                self.stderr.write(f'Error creating Premium plan: {str(e)}')
            
        self.stdout.write(self.style.SUCCESS('Membership plans created successfully!'))
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete existing membership plans before creating new ones',
        ) 