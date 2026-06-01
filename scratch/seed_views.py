import os
import sys
import django
import random

# Adiciona o diretório atual ao python path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Quarto, Hotel

def seed_views():
    print("Iniciando seed de visualizações...")
    
    # 1. Seed para Hotéis (Páginas principais)
    hoteis = Hotel.objects.all()
    print(f"Encontrados {hoteis.count()} hotéis.")
    for hotel in hoteis:
        v = random.randint(150, 450)
        hotel.visualizacoes = v
        hotel.save()
        print(f"Hotel {hotel.nome}: {v} visualizações.")
        
    # 2. Seed para Quartos (Acomodações)
    quartos = list(Quarto.objects.all())
    print(f"Encontrados {len(quartos)} quartos.")
    
    if len(quartos) == 0:
        print("Nenhum quarto encontrado para seed.")
        return
        
    # Gerar valores únicos entre 100 e 300
    valores = random.sample(range(100, 300), len(quartos))
    for i, quarto in enumerate(quartos):
        v = valores[i]
        quarto.visualizacoes = v
        quarto.save()
        print(f"Quarto {quarto.nome} ({quarto.hotel.nome}): {v} visualizações.")
        
    print("Seed concluído com sucesso!")

if __name__ == "__main__":
    seed_views()
