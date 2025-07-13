import random
import string
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Generates a new Django SECRET_KEY'

    def handle(self, *args, **kwargs):
        key = ''.join(random.choices(
            string.ascii_letters + string.digits + string.punctuation,
            k=50
        ))
        self.stdout.write(key)
