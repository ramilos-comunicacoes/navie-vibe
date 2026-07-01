import os
import sys
import django

# Set up django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.contrib.auth.models import User
from restaurantes.models import Restaurante, RestauranteUsuario

def create_credentials():
    print("Iniciando a criação de credenciais para os restaurantes...")
    
    partners = [
        {"username": "casadeengenho", "email": "contato@casadeengenho.com.br", "slug": "casa-de-engenho", "password": "casaEng@2026vibe"},
        {"username": "manacadaserra", "email": "contato@manacadaserra.com.br", "slug": "manaca-da-serra", "password": "manacaSer@2026vibe"},
        {"username": "premibeer", "email": "contato@premibeer.com.br", "slug": "premibeer", "password": "premiBeer@2026vibe"},
        {"username": "bienecacau", "email": "contato@bienecacau.com.br", "slug": "biene-cacau", "password": "bieneCac@2026vibe"},
    ]
    
    for p in partners:
        # 1. Cria ou atualiza o usuário no banco padrão
        user, created = User.objects.using('default').get_or_create(username=p["username"])
        user.email = p["email"]
        user.set_password(p["password"])
        user.is_staff = False
        user.is_superuser = False
        user.save(using='default')
        status = "criado" if created else "atualizado"
        print(f"Usuário {p['username']} {status} com sucesso.")
        
        # 2. Busca o restaurante correspondente no banco restaurantes
        try:
            restaurante = Restaurante.objects.using('restaurantes').get(slug=p["slug"])
        except Restaurante.DoesNotExist:
            print(f"[-] Restaurante com slug {p['slug']} não existe. Pulando...")
            continue
            
        # 3. Cria ou atualiza o RestauranteUsuario
        perfil, created_p = RestauranteUsuario.objects.using('restaurantes').get_or_create(
            user_id=user.id,
            defaults={"restaurante": restaurante, "role": "proprietario", "ativo": True}
        )
        if not created_p:
            perfil.restaurante = restaurante
            perfil.role = "proprietario"
            perfil.ativo = True
            perfil.save(using='restaurantes')
            
        status_p = "criado" if created_p else "atualizado"
        print(f"Perfil de Restaurante para {p['username']} {status_p} e ativado com sucesso.")

if __name__ == "__main__":
    create_credentials()
