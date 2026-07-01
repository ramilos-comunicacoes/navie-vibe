import os
import sys
import django

# Set up django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.contrib.auth.models import User
from restaurantes.models import Restaurante, RestauranteUsuario

def main():
    print("Iniciando criação de super usuário de restaurantes...")
    
    # 1. Garantir que o User 'tiagoismar' existe no banco default
    try:
        user = User.objects.using('default').get(username='tiagoismar')
        user.set_password('limaodoce')
        user.save(using='default')
        print(f"[+] Usuário existente encontrado e senha atualizada para 'limaodoce': {user.username}")
    except User.DoesNotExist:
        user = User.objects.db_manager('default').create_user(
            username='tiagoismar',
            email='pousadaramilos@outlook.com',
            password='limaodoce',
            first_name='Tiago',
            last_name='Ismar'
        )
        print(f"[+] Novo usuário criado no banco default com senha 'limaodoce': {user.username}")

    # 2. Obter o Restaurante (Manacá da Serra) do banco restaurantes
    try:
        restaurante = Restaurante.objects.using('restaurantes').get(slug='manaca-da-serra')
        print(f"[+] Restaurante encontrado: {restaurante.nome}")
    except Restaurante.DoesNotExist:
        print("[-] Erro: Restaurante 'manaca-da-serra' não encontrado no banco restaurantes. Por favor execute register_restaurants_navie.py primeiro.")
        return

    # 3. Criar o perfil de RestauranteUsuario no banco restaurantes
    profile, created = RestauranteUsuario.objects.using('restaurantes').update_or_create(
        user=user,
        defaults={
            'restaurante': restaurante,
            'role': 'proprietario',
            'ativo': True,
            'cpf': '111.222.333-44'
        }
    )
    
    if created:
        print(f"[+] Perfil RestauranteUsuario CRIADO para {user.username} (vinculado a {restaurante.nome})")
    else:
        print(f"[+] Perfil RestauranteUsuario ATUALIZADO para {user.username} (vinculado a {restaurante.nome})")

    print("[SUCESSO] Usuário pronto para acessar o portal de restaurantes!")

if __name__ == "__main__":
    main()
