import os
import sys
import django
from decimal import Decimal
import datetime
import random

# Inicializa o ambiente do Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel, Reserva
from financeiro.models import TransacaoFinanceira
from django.contrib.auth.models import User

def seed_financial_data():
    print("--- Iniciando a semente de dados contabeis reais ---")
    
    # 1. Obter Hoteis e Usuario Admin
    hoteis = Hotel.objects.all()
    if not hoteis.exists():
        print("[ERRO] Nenhum hotel cadastrado. Por favor, rode a semente basica primeiro.")
        return
        
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_user:
        print("[ERRO] Nenhum usuario administrador encontrado no banco.")
        return
        
    hoje = datetime.date.today()
    
    # Descrições e Valores Realistas para Alimentar o DRE Contábil
    receitas_modelos = [
        ('walk_in', 'Balcão / Diária Walk-in Chalé', 380.00, 650.00),
        ('diarias', 'Reserva Marketplace Quarto Família', 450.00, 1200.00),
        ('diarias', 'Estadia Finalizada - Suite Casal', 290.00, 580.00),
        ('frigobar', 'Consumo de Frigobar - Cervejas & Refrigerantes', 35.00, 120.00),
        ('frigobar', 'Consumo Frigobar - Snacks e Chocolates', 15.00, 65.00),
        ('room_service', 'Pedido Copa - Porção de Peixe & Caipirinha', 85.00, 160.00),
        ('room_service', 'Serviço de Quarto - Café da manhã especial', 45.00, 95.00),
        ('spa_lazer', 'Spa e Massagem Relaxante Casal', 180.00, 350.00),
        ('spa_lazer', 'Aluguel de Bicicletas / Passeio Ecológico', 60.00, 120.00),
        ('outro_receita', 'Reembolso Estorno de Fornecedor', 150.00, 300.00)
    ]
    
    despesas_modelos = [
        ('salarios', 'Pagamento Folha - Recepcionista Turno A', 1450.00, 1850.00),
        ('salarios', 'Comissão Mensal - Equipe de Limpeza', 350.00, 750.00),
        ('manutencao', 'Reparo Técnico - Chuveiro Elétrico Ch 04', 80.00, 180.00),
        ('manutencao', 'Pintura Fachada / Retoque área externa', 350.00, 950.00),
        ('manutencao', 'Reposição de lâmpadas LED e tomadas', 45.00, 120.00),
        ('energia_agua', 'Fatura Mensal - Companhia de Energia Elétrica', 850.00, 1450.00),
        ('energia_agua', 'Conta Mensal - Companhia de Saneamento e Água', 320.00, 580.00),
        ('energia_agua', 'Provedor Telecom - Assinatura Internet Fibra Óptica', 120.00, 180.00),
        ('amenities', 'Lote Amenities - Mini Sabonetes & Shampoos de Luxo', 280.00, 480.00),
        ('amenities', 'Compra de Enxoval - 10 Toalhas de banho algodão fio penteado', 180.00, 350.00),
        ('taxa_marketplace', 'Fatura de Comissão - Plataformas de Divulgação', 220.00, 450.00),
        ('outro_despesa', 'Material de Escritório e papelaria recepção', 45.00, 95.00)
    ]

    for hotel in hoteis:
        # Limpar lancamentos contabeis antigos para evitar duplicacoes
        TransacaoFinanceira.objects.filter(hotel=hotel).delete()
        print(f"[HOTEL] Alimentando dados para o hotel: '{hotel.nome}'...")
        
        # Criar lançamentos contábeis nos últimos 15 dias
        count_receitas = 0
        count_despesas = 0
        
        for d in range(15):
            dia = hoje - datetime.timedelta(days=d)
            
            # Sorteia receitas para o dia (1 a 3 lançamentos)
            for _ in range(random.randint(1, 3)):
                cat, desc, min_v, max_v = random.choice(receitas_modelos)
                valor = Decimal(random.uniform(min_v, max_v)).quantize(Decimal('0.01'))
                
                # Opcional: tenta atrelar uma reserva do hotel para dar maior realismo
                reserva = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('?').first()
                
                TransacaoFinanceira.objects.create(
                    hotel=hotel,
                    reserva=reserva,
                    tipo='receita',
                    categoria=cat,
                    valor=valor,
                    descricao=f"{desc} (Dia {dia.strftime('%d/%m')})",
                    data=dia,
                    criado_por=admin_user
                )
                count_receitas += 1
                
            # Sorteia despesas para o dia (1 lançamento ocasional)
            if random.random() > 0.4:
                cat, desc, min_v, max_v = random.choice(despesas_modelos)
                valor = Decimal(random.uniform(min_v, max_v)).quantize(Decimal('0.01'))
                
                TransacaoFinanceira.objects.create(
                    hotel=hotel,
                    tipo='despesa',
                    categoria=cat,
                    valor=valor,
                    descricao=desc,
                    data=dia,
                    criado_por=admin_user
                )
                count_despesas += 1
                
        print(f"   [OK] Adicionadas {count_receitas} Receitas e {count_despesas} Despesas operacionais.")
        
    print("--- Semente financeira concluida com sucesso absoluto! ---")

if __name__ == '__main__':
    seed_financial_data()
