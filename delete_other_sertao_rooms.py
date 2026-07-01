import os
import django

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel, Quarto

def apagar_outros():
    print("=" * 60)
    print("APAGANDO OUTRAS CATEGORIAS DE QUARTO - POUSADA RAMILOS SERTÃO")
    print("=" * 60)
    
    hotel = None
    try:
        hotel = Hotel.objects.get(slug='ramilos-sertao')
    except Hotel.DoesNotExist:
        try:
            hotel = Hotel.objects.get(id=5)
        except Hotel.DoesNotExist:
            hotel = Hotel.objects.filter(nome__icontains='sertão').first() or Hotel.objects.filter(nome__icontains='sertao').first()
            
    if not hotel:
        print("ERRO: Pousada Ramilos Sertão não foi localizada!")
        return
        
    print(f"Pousada Localizada: {hotel.nome} (ID: {hotel.id})")
    
    # Exclui todas as categorias deste hotel exceto o "Chalé Aconchegante do Sertão"
    # O Django se encarrega de deletar as unidades físicas por cascata (Cascade)
    exclusões = Quarto.objects.filter(hotel=hotel).exclude(nome='Chalé Aconchegante do Sertão')
    total_deletar = exclusões.count()
    
    if total_deletar == 0:
        print("\nNenhuma outra categoria de quarto foi encontrada para exclusão. Tudo certo!")
    else:
        print(f"\nEncontradas {total_deletar} outras categorias para excluir.")
        for q in exclusões:
            print(f"  - Deletando categoria: '{q.nome}' e suas acomodações...")
            
        deleted_count, details = exclusões.delete()
        print("-" * 60)
        print(f"SUCESSO! Registros apagados: {deleted_count}")
        
    print("=" * 60)

if __name__ == '__main__':
    apagar_outros()
