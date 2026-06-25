from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from sistema.models import Pousada, CategoriaQuarto, Quarto, Reserva, TransacaoFinanceira, ReservaLog, Usuario

class ReservaTogglePagamentoTestCase(TestCase):
    def setUp(self):
        # Create Pousada
        self.pousada = Pousada.objects.create(
            nome="Pousada de Teste",
            endereco="Endereço de Teste",
            telefone_whatsapp="123456789"
        )
        
        # Create CategoriaQuarto
        self.categoria = CategoriaQuarto.objects.create(
            pousada=self.pousada,
            nome="Suite Simples",
            preco_base=Decimal("150.00"),
            capacidade_adultos=2,
            capacidade_criancas=1,
            ativo=True
        )
        
        # Create Quarto
        self.quarto = Quarto.objects.create(
            pousada=self.pousada,
            numero="101",
            categoria=self.categoria,
            status="LIVRE"
        )
        
        # Create User
        self.user = Usuario.objects.create_user(
            username="atendente",
            password="password123",
            role="PORTARIA",
            pousada_vinculada=self.pousada
        )
        
        # Create Reserva
        self.reserva = Reserva.objects.create(
            quarto=self.quarto,
            data_checkin=timezone.now().date(),
            data_checkout=timezone.now().date() + timedelta(days=2),
            valor_total=Decimal("300.00"),
            valor_pago=Decimal("0.00"),
            status="CONFIRMADA",
            hospede_nome="João da Silva",
            hospede_cpf="12345678901",
            hospede_email="joao@gmail.com",
            hospede_telefone="11999999999",
            quantidade_hospedes=1
        )
        
        self.client = Client()
        self.client.login(username="atendente", password="password123")
        
    def test_toggle_pagamento_to_paid(self):
        # Check starting state
        self.assertEqual(self.reserva.valor_pago, Decimal("0.00"))
        self.assertFalse(TransacaoFinanceira.objects.filter(reserva=self.reserva).exists())
        
        # Toggle payment ON
        response = self.client.post(
            reverse('sistema:partner_reserva_toggle_pagamento', kwargs={'reserva_id': self.reserva.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify database updates
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.valor_pago, Decimal("300.00"))
        
        # Verify TransacaoFinanceira is created
        transactions = TransacaoFinanceira.objects.filter(reserva=self.reserva, categoria='DIARIA')
        self.assertTrue(transactions.exists())
        self.assertEqual(transactions.first().valor, Decimal("300.00"))
        self.assertEqual(transactions.first().tipo, "RECEITA")
        
        # Verify ReservaLog is created
        logs = ReservaLog.objects.filter(reserva=self.reserva, acao='pagamento')
        self.assertTrue(logs.exists())
        
    def test_toggle_pagamento_to_unpaid(self):
        # Set to paid first
        self.reserva.valor_pago = Decimal("300.00")
        self.reserva.save()
        TransacaoFinanceira.objects.create(
            reserva=self.reserva,
            pousada=self.pousada,
            tipo="RECEITA",
            valor=Decimal("300.00"),
            categoria="DIARIA"
        )
        
        # Toggle payment OFF
        response = self.client.post(
            reverse('sistema:partner_reserva_toggle_pagamento', kwargs={'reserva_id': self.reserva.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify database updates
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.valor_pago, Decimal("0.00"))
        
        # Verify TransacaoFinanceira is deleted
        self.assertFalse(TransacaoFinanceira.objects.filter(reserva=self.reserva, categoria='DIARIA').exists())
        
        # Verify ReservaLog is created
        logs = ReservaLog.objects.filter(reserva=self.reserva, acao='estorno_pagamento')
        self.assertTrue(logs.exists())
