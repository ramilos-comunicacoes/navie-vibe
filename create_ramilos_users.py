import os
import sys
import django

# Inicializa o ambiente do Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from django.contrib.auth.models import User
from hoteis.models import Hotel, ParceiroUsuario

def create_users():
    # Encontra o hotel Pousada Ramilos Tianguá (ID 4)
    try:
        hotel = Hotel.objects.get(id=4)
        print(f"Hotel selecionado: {hotel.nome} (ID {hotel.id})")
    except Hotel.DoesNotExist:
        print("Erro: Hotel com ID 4 (Pousada Ramilos Tianguá) não foi encontrado no banco.")
        return

    # Lista de usuários a criar
    usuarios_novos = [
        {
            "username": "jeanne@navievibe.com",
            "first_name": "Jeanne",
            "password": "Jeanne@Ramilos2026",
            "role": "gerente"
        },
        {
            "username": "eliane@navievibe.com",
            "first_name": "Eliane",
            "password": "Eliane@Ramilos2026",
            "role": "portaria"
        },
        {
            "username": "rosiane@navievibe.com",
            "first_name": "Rosiane",
            "password": "Rosiane@Ramilos2026",
            "role": "portaria"
        },
        {
            "username": "nayara@navievibe.com",
            "first_name": "Nayara",
            "password": "Nayara@Ramilos2026",
            "role": "portaria"
        }
    ]

    print("\nIniciando a criação de usuários...")
    print("=" * 60)
    for u in usuarios_novos:
        # 1. Criar ou obter o User no banco default
        user, created = User.objects.get_or_create(
            username=u["username"],
            defaults={
                "email": u["username"],
                "first_name": u["first_name"],
                "is_active": True
            }
        )
        
        # Define a senha
        user.set_password(u["password"])
        user.save()
        
        # 2. Criar ou obter o ParceiroUsuario no banco de hospedagem
        parceiro, p_created = ParceiroUsuario.objects.get_or_create(
            user=user,
            defaults={
                "hotel": hotel,
                "role": u["role"],
                "ativo": True
            }
        )
        
        # Garante que o parceiro está ativo e com a role/hotel correto se já existia
        if not p_created:
            parceiro.hotel = hotel
            parceiro.role = u["role"]
            parceiro.ativo = True
            parceiro.save()

        status_str = "CRIADO" if created else "ATUALIZADO (senha reiniciada)"
        print(f"Nome: {u['first_name']:<8} | Login: {u['username']:<22} | Cargo: {u['role']:<8} | Status: {status_str}")

    print("=" * 60)
    print("Usuários criados e associados com sucesso!")

if __name__ == "__main__":
    create_users()
