import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.messages.storage.fallback import FallbackStorage
from hoteis.views import partner_dashboard

# Get user tiagoismar
user = User.objects.get(username='tiagoismar')

# Create request
factory = RequestFactory()
request = factory.get('/hospedagens/sistema/')
request.user = user

# Add session and messages support
request.session = SessionStore()
request._messages = FallbackStorage(request)

# Call view
response = partner_dashboard(request)
html = response.content.decode('utf-8')

# Find around the video class
lines = html.splitlines()
for idx, line in enumerate(lines):
    if 'hero_video' in line or 'Escolher' in line or 'h-8' in line:
        print(f"{idx+1}: {line}")
