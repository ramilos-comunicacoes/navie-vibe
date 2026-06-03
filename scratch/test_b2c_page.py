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
html = response.content.decode('utf-8')

# Write to file
with open('scratch/rendered_b2c.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Status code:", response.status_code)
print("Length of HTML:", len(html))
