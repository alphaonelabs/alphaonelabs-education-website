from django.core.management.base import BaseCommand
from django.utils.text import slugify
from web.models import Meetup

class Command(BaseCommand):
    help = 'Update slugs to ensure they are unique'

    def handle(self, *args, **kwargs):
        meetups = Meetup.objects.all()
        for meetup in meetups:
            original_slug = slugify(meetup.title)
            slug = original_slug
            counter = 1
            while Meetup.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            meetup.slug = slug
            meetup.save()
        self.stdout.write(self.style.SUCCESS('Successfully updated slugs'))