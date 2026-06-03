import os
import sys
import django
from django.utils.text import slugify

# Inicializa as configurações do Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel

def populate_slugs():
    print("Atualizando slugs dos hotéis/pousadas...")
    for h in Hotel.objects.all():
        original_slug = h.slug
        if not h.slug or h.slug == 'None' or h.slug.strip() == '':
            # Gera slug a partir do nome
            base_slug = slugify(h.nome)
            slug = base_slug
            num = 2
            while Hotel.objects.filter(slug=slug).exclude(id=h.id).exists():
                slug = f'{base_slug}-{num}'
                num += 1
            h.slug = slug
            h.save(update_fields=['slug'])
            print(f'Hotel ID {h.id}: "{h.nome}" -> Atualizado Slug: "{h.slug}" (era "{original_slug}")')
        else:
            print(f'Hotel ID {h.id}: "{h.nome}" -> Já possui Slug: "{h.slug}"')

if __name__ == '__main__':
    populate_slugs()
