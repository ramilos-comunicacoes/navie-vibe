import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.apps import apps

search_term = "ativo carregado"
for model in apps.get_models():
    # Only check models that have char/text fields
    try:
        queryset = model.objects.all()
        for obj in queryset:
            for field in obj._meta.fields:
                val = getattr(obj, field.name)
                if val and search_term in str(val).lower():
                    print(f"FOUND in {model.__name__} (ID: {obj.pk}), Field: {field.name} = {val}")
    except Exception as e:
        pass
