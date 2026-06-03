import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth.models import User

rf = RequestFactory()
request = rf.get('/administracao/hoteis/novo/')
# Create a dummy superuser request
user = User(username='admin', first_name='Administrador')
request.user = user

context = {
    'request': request,
    'locais': [],
    'errors': [],
    'action': 'create',
    'active_tab': 'hoteis',
    'GOOGLE_API_KEY': 'dummy_key',
}

try:
    html = render_to_string('administracao/hotel_form.html', context)
    print("Template rendered successfully!")
    print("Has btn-auto-locate:", 'btn-auto-locate' in html)
    print("Has btn-toggle-satellite:", 'btn-toggle-satellite' in html)
    print("Has btn-toggle-roadmap:", 'btn-toggle-roadmap' in html)
except Exception as e:
    import traceback
    print("ERROR rendering template:")
    traceback.print_exc()
