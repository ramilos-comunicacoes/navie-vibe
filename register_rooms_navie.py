import os
import sys
import django
from decimal import Decimal

# Set up django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from hoteis.models import Hotel, Quarto, UnidadeQuarto

def register():
    # Try finding the hotel by name or fallback to ID 5
    hotel = Hotel.objects.filter(nome__icontains="Pousada Ramilos Praia").first()
    if not hotel:
        try:
            hotel = Hotel.objects.get(id=5)
            hotel.nome = "Pousada Ramilos Praia"
            hotel.save()
        except Hotel.DoesNotExist:
            print("Hotel ID 5 or name containing 'Pousada Ramilos Praia' not found!")
            return

    print(f"Hotel selecionado: {hotel.nome} (ID {hotel.id})")

    # 1. Definição das Categorias de Quarto (models.Quarto)
    categorias_data = {
        "pcd": {
            "nome": "Quarto Adaptado PCD (4 pessoas)",
            "preco": Decimal("355.00"),
            "capacidade_pessoas": 4,
            "comodidades": "Ar Condicionado, Banheiro Adaptado, Porta Larga, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Acomodação adaptada para cadeirantes. Porta do banheiro mais larga e vaso adaptado (barras de ferro a instalar). A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "standard_quadruplo": {
            "nome": "Quarto Standard Quádruplo",
            "preco": Decimal("355.00"),
            "capacidade_pessoas": 4,
            "comodidades": "Ar Condicionado, 3 Camas de Solteiro, 1 Cama de Casal, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto padrão confortável equipado com 3 camas de solteiro and 1 cama de casal. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "quintuplo_standard": {
            "nome": "Quarto Quíntuplo Standard (3 Solteiro + 1 Casal)",
            "preco": Decimal("435.00"),
            "capacidade_pessoas": 5,
            "comodidades": "Ar Condicionado, 3 Camas de Solteiro, 1 Cama de Casal, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto padrão amplo equipado com 3 camas de solteiro e 1 cama de casal. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "quintuplo_familia": {
            "nome": "Quarto Quíntuplo Família (2 Casal + 1 Solteiro)",
            "preco": Decimal("435.00"),
            "capacidade_pessoas": 5,
            "comodidades": "Ar Condicionado, 2 Camas de Casal, 1 Cama de Solteiro, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto espaçoso ideal para famílias, equipado com 2 camas de casal e 1 cama de solteiro. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        }
    }

    # Criar/Obter Categorias
    categorias_obj = {}
    for key, data in categorias_data.items():
        cat, created = Quarto.objects.get_or_create(
            hotel=hotel,
            nome=data["nome"],
            defaults={
                "preco": data["preco"],
                "capacidade_pessoas": data["capacidade_pessoas"],
                "comodidades": data["comodidades"],
                "descricao": data["descricao"]
            }
        )
        if not created:
            # Atualizar os dados se já existir
            cat.preco = data["preco"]
            cat.capacidade_pessoas = data["capacidade_pessoas"]
            cat.comodidades = data["comodidades"]
            cat.descricao = data["descricao"]
            cat.save()
            print(f"Categoria atualizada: {cat.nome}")
        else:
            print(f"Categoria criada: {cat.nome}")
        
        categorias_obj[key] = cat

    # 2. Definição dos Quartos Físicos (models.UnidadeQuarto)
    # IDs/nomes conforme as especificações
    quartos_list = [
        {"identificador": "Quarto 1", "categoria": "pcd"},
        {"identificador": "Quarto 2", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 3", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 4", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 5", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 6", "categoria": "quintuplo_standard"},
        {"identificador": "Quarto 8", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 9", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 10", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 11", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 12", "categoria": "standard_quadruplo"},
        {"identificador": "Quarto 13", "categoria": "quintuplo_familia"}
    ]

    for q in quartos_list:
        cat_obj = categorias_obj[q["categoria"]]
        unidade, created = UnidadeQuarto.objects.get_or_create(
            quarto=cat_obj,
            identificador=q["identificador"],
            defaults={"ativa": True, "disponivel": True}
        )
        if created:
            print(f"Quarto físico criado: {unidade.identificador} ({cat_obj.nome})")
        else:
            print(f"Quarto físico já existente: {unidade.identificador}")

if __name__ == "__main__":
    register()
