from django.core.management.base import BaseCommand
from core.models import AdminSettings


class Command(BaseCommand):
    help = 'Create default admin settings for OpenAI configuration'

    def handle(self, *args, **options):
        # Create default OpenAI settings
        openai_api_key, created_key = AdminSettings.objects.get_or_create(
            key='openai_api_key',
            defaults={
                'value': '',
                'description': 'OpenAI API Key (starts with sk-...)'
            }
        )
        
        openai_model, created_model = AdminSettings.objects.get_or_create(
            key='openai_model',
            defaults={
                'value': 'gpt-4o',
                'description': 'OpenAI model to use for AI generation (e.g., gpt-4o, gpt-3.5-turbo)'
            }
        )
        
        if created_key:
            self.stdout.write(
                self.style.SUCCESS('Created openai_api_key setting (empty - please set in Django Admin)')
            )
        else:
            self.stdout.write('openai_api_key setting already exists')
            
        if created_model:
            self.stdout.write(
                self.style.SUCCESS('Created openai_model setting with default value: gpt-4o')
            )
        else:
            self.stdout.write('openai_model setting already exists')
        
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('Next steps:')
        )
        self.stdout.write('1. Go to Django Admin: http://localhost:8000/admin/')
        self.stdout.write('2. Navigate to Admin Settings')
        self.stdout.write('3. Edit the "openai_api_key" entry and add your API key')
        self.stdout.write('4. Optionally adjust the "openai_model" if needed')