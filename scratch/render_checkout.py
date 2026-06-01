import os
import sys
import django

# Set up Django environment
sys.path.append(r'c:\Dev\JAVA\Naviê Vibe')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from django.template.loader import render_to_string
from hoteis.models import Quarto
from sas.financeiro import calcular_taxas_reserva
from decimal import Decimal

def test_render():
    quarto = Quarto.objects.first()
    if not quarto:
        print("Nenhum quarto encontrado no banco!")
        return
        
    carrinho_session = {
        'quarto_id': quarto.id,
        'unidade_identificador': '101',
        'checkin': '2026-06-01',
        'checkout': '2026-06-05',
        'quantidade_hospedes': 1,
        'hospedes': [{
            'nome': 'Hóspede Teste',
            'cpf': '123.456.789-01',
            'email': 'teste@gmail.com',
            'telefone': '(88) 99999-8888',
            'cep': '62320-000',
            'endereco': 'Rua Teste, 100'
        }],
        'veiculo': {
            'placa': 'ABC-1234',
            'modelo': 'Fusca',
            'cor': 'Azul'
        }
    }
    
    fin = calcular_taxas_reserva(quarto.hotel.empresa, 'hospedagem', quarto.preco, 4)
    
    context = {
        'carrinho': carrinho_session,
        'quarto': quarto,
        'noites': 4,
        'financeiro': fin,
        'mp_public_key': 'APP_USR-mock-key',
    }
    
    try:
        html = render_to_string('hoteis/checkout_pagamento.html', context)
        print("Template renderizado com SUCESSO!")
        print(f"Tamanho do HTML: {len(html)} bytes")
        
        # Procurar por classes de exibição ou ocultação
        if "hidden md:grid" in html:
            print("Encontrado 'hidden md:grid' no HTML!")
        else:
            print("NÃO encontrado 'hidden md:grid'!")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Erro ao renderizar template:", e)

if __name__ == '__main__':
    test_render()
