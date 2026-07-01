import os
import django
import unicodedata
from django.utils.text import slugify

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel, Quarto, UnidadeQuarto

def cadastrar():
    print("=" * 60)
    print("INICIANDO CADASTRO DE CHALÉS - POUSADA RAMILOS SERTÃO")
    print("=" * 60)
    
    # 1. Tenta localizar a Pousada Ramilos Sertão
    hotel = None
    
    # Tenta pelo slug da pousada do Sertão da Ramilos
    try:
        hotel = Hotel.objects.get(slug='ramilos-sertao')
    except Hotel.DoesNotExist:
        # Se não achar por slug, tenta por id=5 (ID correspondente na VPS)
        try:
            hotel = Hotel.objects.get(id=5)
        except Hotel.DoesNotExist:
            # Tenta buscar pelo nome
            hotel = Hotel.objects.filter(nome__icontains='sertão').first() or Hotel.objects.filter(nome__icontains='sertao').first()
            
    if not hotel:
        print("ERRO: Pousada Ramilos Sertão não foi localizada no banco de dados!")
        print("Certifique-se de que a pousada existe ou consulte os IDs disponíveis.")
        return
        
    print(f"Pousada Localizada: {hotel.nome} (ID: {hotel.id})")
    
    # Descritivo personalizado conforme solicitado
    descricao_chale = (
        "Chalé aconchegante perfeito para casais, cercado pela tranquilidade e belezas "
        "naturais da nossa pousada perto da sede de Tianguá. Desfrute de um ambiente "
        "romântico com toda a privacidade, jardim arborizado, capela histórica para contemplação, "
        "piscina refrescante e uma quadra de esportes de areia (futevôlei) para o seu lazer. "
        "Café da manhã especial incluso na estadia."
    )
    
    # 2. Cadastra ou atualiza a Categoria Quarto
    quarto, created = Quarto.objects.get_or_create(
        hotel=hotel,
        nome='Chalé Aconchegante do Sertão',
        defaults={
            'preco': 300.00,
            'capacidade_pessoas': 2,
            'comodidades': 'Ar Condicionado, Wi-Fi, Café da Manhã Incluso, Piscina, Estacionamento',
            'tags': 'Casal, Romance, Natureza, Esporte',
            'descricao': descricao_chale
        }
    )
    
    if created:
        print(f"\n[OK] Categoria '{quarto.nome}' criada com sucesso!")
    else:
        # Garante a atualização dos dados se já existir
        quarto.preco = 300.00
        quarto.descricao = descricao_chale
        quarto.comodidades = 'Ar Condicionado, Wi-Fi, Café da Manhã Incluso, Piscina, Estacionamento'
        quarto.tags = 'Casal, Romance, Natureza, Esporte'
        quarto.save()
        print(f"\n[OK] Categoria '{quarto.nome}' já existia e foi atualizada com preço de R$ 300,00.")

    # 3. Cria as 10 unidades físicas (Chalé 01 até Chalé 10)
    print("\nCadastrando unidades físicas:")
    unidades_criadas = 0
    for i in range(1, 11):
        identificador = f"Chalé {i:02d}"
        unidade, u_created = UnidadeQuarto.objects.get_or_create(
            quarto=quarto,
            identificador=identificador,
            defaults={
                'ativa': True,
                'disponivel': True
            }
        )
        if u_created:
            print(f"  - {identificador}: [NOVO] Cadastrado com sucesso!")
            unidades_criadas += 1
        else:
            print(f"  - {identificador}: [JÁ EXISTIA] Mantido inalterado.")
            
    print("-" * 60)
    print(f"PROCESSO CONCLUÍDO! {unidades_criadas} novos chalés cadastrados.")
    print("=" * 60)

if __name__ == '__main__':
    cadastrar()
