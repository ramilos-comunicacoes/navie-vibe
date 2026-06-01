import os
import sys
import django
from django.template import Template, Context

sys.path.append(r"c:\Dev\JAVA\Naviê Vibe")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navie.settings")
django.setup()

template = Template('{"X-CSRFToken": "{{ csrf_token }}"}')
context = Context({'csrf_token': 'my_token_123'})
print(template.render(context))
