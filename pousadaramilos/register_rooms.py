import os
import sys
import django
from decimal import Decimal

# Set up django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from sistema.models import Pousada, CategoriaQuarto, Quarto

def register():
    # 1. Obter a pousada de Luís Correia (ID 8)
    try:
        pousada = Pousada.objects.get(id=8)
    except Pousada.DoesNotExist:
        print("Pousada ID 8 não encontrada!")
        return

    # Atualizar o nome da pousada para Pousada Ramilos Praia
    pousada.nome = "Pousada Ramilos Praia"
    pousada.save()
    print(f"Pousada ID 8 renomeada para: {pousada.nome}")

    # 2. Definição das Categorias de Quarto
    categorias_data = {
        "pcd": {
            "nome": "Quarto Adaptado PCD (4 pessoas)",
            "preco_base": Decimal("355.00"),
            "capacidade_adultos": 4,
            "capacidade_criancas": 0,
            "comodidades": "Ar Condicionado, Banheiro Adaptado, Porta Larga, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Acomodação adaptada para cadeirantes. Porta do banheiro mais larga e vaso adaptado (barras de ferro a instalar). A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "standard_quadruplo": {
            "nome": "Quarto Standard Quádruplo",
            "preco_base": Decimal("355.00"),
            "capacidade_adultos": 4,
            "capacidade_criancas": 0,
            "comodidades": "Ar Condicionado, 3 Camas de Solteiro, 1 Cama de Casal, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto padrão confortável equipado com 3 camas de solteiro e 1 cama de casal. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "quintuplo_standard": {
            "nome": "Quarto Quíntuplo Standard (3 Solteiro + 1 Casal)",
            "preco_base": Decimal("435.00"),
            "capacidade_adultos": 5,
            "capacidade_criancas": 0,
            "comodidades": "Ar Condicionado, 3 Camas de Solteiro, 1 Cama de Casal, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto padrão amplo equipado com 3 camas de solteiro e 1 cama de casal. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        },
        "quintuplo_familia": {
            "nome": "Quarto Quíntuplo Família (2 Casal + 1 Solteiro)",
            "preco_base": Decimal("435.00"),
            "capacidade_adultos": 5,
            "capacidade_criancas": 0,
            "comodidades": "Ar Condicionado, 2 Camas de Casal, 1 Cama de Solteiro, Piscina, Cozinha Compartilhada, Café da Manhã",
            "descricao": "Quarto espaçoso ideal para famílias, equipado com 2 camas de casal e 1 cama de solteiro. A pousada oferece piscina, cozinha compartilhada e café da manhã. Não disponibilizamos toalhas nem lençol."
        }
    }

    # Criar/Obter Categorias
    categorias_obj = {}
    for key, data in categorias_data.items():
        cat, created = CategoriaQuarto.objects.get_or_create(
            pousada=pousada,
            nome=data["nome"],
            defaults={
                "preco_base": data["preco_base"],
                "capacidade_adultos": data["capacidade_adultos"],
                "capacidade_criancas": data["capacidade_criancas"],
                "comodidades": data["comodidades"],
                "descricao": data["descricao"],
                "ativo": True
            }
        )
        if not created:
            # Atualizar os dados se já existir
            cat.preco_base = data["preco_base"]
            cat.capacidade_adultos = data["capacidade_adultos"]
            cat.capacidade_criancas = data["capacidade_criancas"]
            cat.comodidades = data["comodidades"]
            cat.descricao = data["descricao"]
            cat.save()
            print(f"Categoria atualizada: {cat.nome}")
        else:
            print(f"Categoria criada: {cat.nome}")
        
        categorias_obj[key] = cat

    # 3. Definição dos Quartos Físicos
    quartos_list = [
        {"numero": "1", "categoria": "pcd", "capacidade": 4},
        {"numero": "2", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "3", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "4", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "5", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "6", "categoria": "quintuplo_standard", "capacidade": 5},
        {"numero": "8", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "9", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "10", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "11", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "12", "categoria": "standard_quadruplo", "capacidade": 4},
        {"numero": "13", "categoria": "quintuplo_familia", "capacidade": 5},
    ]

    # Criar/Obter Quartos Físicos
    for q_data in quartos_list:
        quarto, created = Quarto.objects.get_or_create(
            pousada=pousada,
            numero=q_data["numero"],
            defaults={
                "categoria": categorias_obj[q_data["categoria"]],
                "status": "LIVRE",
                "capacidade_maxima": q_data["capacidade"]
            }
        )
        if not created:
            # Atualizar se já existir
            quarto.categoria = categorias_obj[q_data["categoria"]]
            quarto.capacidade_maxima = q_data["capacidade"]
            quarto.save()
            print(f"Quarto físico {quarto.numero} atualizado (Categoria: {quarto.categoria.nome})")
        else:
            print(f"Quarto físico {quarto.numero} criado (Categoria: {quarto.categoria.nome})")

    print("\nTodo o cadastro foi concluído com sucesso!")

if __name__ == "__main__":
    register()
