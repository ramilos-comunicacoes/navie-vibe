import os
import sys
import django

# Adiciona o diretório raiz do projeto ao PATH do Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define as configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Empresa
from hoteis.models import Local, Hotel, ParceiroUsuario

print("Iniciando semeadura da Pousada Ramilos e Proprietário Tiago Ismar...")

# 1. Criar Empresa Central no banco 'default'
empresa, created_emp = Empresa.objects.get_or_create(
    cnpj="99.888.777/0001-99",
    defaults={
        'nome_fantasia': "Pousada Ramilos Tianguá",
        'razao_social': "Pousada Ramilos Tianguá LTDA",
        'categoria': "hospedagem",
        'email_contato': "pousadaramilos@outlook.com",
        'telefone_contato': "(88) 99999-8888",
        'endereco': "Av. Ibiapaba, 100",
        'cidade': "Tianguá",
        'estado': "CE",
        'cep': "62320-000",
    }
)
if created_emp:
    print(f"Empresa '{empresa.nome_fantasia}' criada com sucesso no banco 'default'.")
else:
    print(f"Empresa '{empresa.nome_fantasia}' já existia no banco 'default'.")

# 2. Criar Local e Hotel no banco 'hospedagem'
local, _ = Local.objects.get_or_create(
    nome="Tianguá Centro",
    defaults={
        'endereco': "Centro de Tianguá",
        'cidade': "Tianguá",
        'estado': "CE"
    }
)

hotel, created_hotel = Hotel.objects.get_or_create(
    empresa=empresa,
    defaults={
        'nome': "Pousada Ramilos Tianguá",
        'descricao': "Pousada familiar no coração de Tianguá, oferecendo muito conforto, aconchego e café da manhã serrano incrível.",
        'local': local,
        'status': 'ativo',
        'destaque': False,
        'slug': 'pousadaramilostiangua',
    }
)
if created_hotel:
    print(f"Hotel '{hotel.nome}' criado com sucesso no banco 'hospedagem'.")
else:
    hotel.slug = 'pousadaramilostiangua'
    hotel.save()
    print(f"Hotel '{hotel.nome}' já existia. Forçado slug 'pousadaramilostiangua'.")

# 3. Criar Usuário no banco 'default'
if not User.objects.filter(username="tiagoismar").exists():
    user = User.objects.create_user(
        username="tiagoismar",
        email="pousadaramilos@outlook.com",
        password="limaodoce",
        first_name="Tiago",
        last_name="Ismar"
    )
    print(f"Usuário 'tiagoismar' criado com sucesso no banco 'default'.")
else:
    user = User.objects.get(username="tiagoismar")
    # Atualiza a senha apenas para garantir fidelidade
    user.set_password("limaodoce")
    user.save()
    print(f"Usuário 'tiagoismar' já existia. Senha resetada para 'limaodoce'.")

# 4. Criar ParceiroUsuario (Proprietário Ativo) no banco 'hospedagem'
parceiro, created_parc = ParceiroUsuario.objects.get_or_create(
    user=user,
    defaults={
        'hotel': hotel,
        'role': 'proprietario',
        'cpf': "111.222.333-44",
        'ativo': True, # Já entra validado e pré-aprovado!
    }
)
if created_parc:
    print(f"Perfil de Parceiro (Proprietário Ativo) associado com sucesso a '{user.username}'!")
else:
    parceiro.ativo = True
    parceiro.save()
    print(f"Perfil de Parceiro já existia para '{user.username}'. Forçado estado 'ativo=True'.")

print("\nSemeadura concluída com sucesso! Conta pronta para ser utilizada.")
