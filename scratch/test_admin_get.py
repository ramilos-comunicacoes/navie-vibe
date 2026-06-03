import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from hoteis.models import Hotel

client = Client()

user = User.objects.filter(is_superuser=True).first()
client.force_login(user)

hotel = Hotel.objects.first()
if hotel:
    print(f"Hotel database coordinates: lat={hotel.latitude}, lng={hotel.longitude}")
    response = client.get(f'/sistemadeadministracao/hoteis/{hotel.id}/editar/')
    content = response.content.decode('utf-8')
    for line in content.split('\n'):
        if 'id_latitude' in line or 'id_longitude' in line:
            print("Rendered:", line.strip())
