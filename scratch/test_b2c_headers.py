import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.test import Client

client = Client()
response = client.get('/pousadaramilostiangua/?preview=1')
print("Status:", response.status_code)
print("Headers:")
for key, val in response.headers.items():
    print(f"  {key}: {val}")
