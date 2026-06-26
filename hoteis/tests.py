from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from core.models import Empresa
from hoteis.models import Local, Hotel, Quarto, UnidadeQuarto, ParceiroUsuario, Reserva, HotelSecao, HotelSecaoItem
from hoteis.views import partner_quarto_salvar
from django.contrib.messages.storage.base import BaseStorage
from unittest.mock import patch
import json
import datetime
from decimal import Decimal


class MockStorage(BaseStorage):
    def _get(self):
        return [], True
    def _store(self, messages, response, *args, **kwargs):
        return []

class MockSession(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False


class PartnerQuartoSaveTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='partner_user', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test Empresa',
            razao_social='Test Empresa LTDA',
            cnpj='12.345.678/0001-90',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='contato@test.com',
            telefone_contato='88999999999'
        )
        self.local = Local.objects.create(nome='Test Local', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos',
            descricao='Pousada Teste',
            local=self.local,
            slug='pousadaramilos'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )

    def test_save_new_quarto_with_units(self):
        # Prepare POST data
        data = {
            'nome': 'Suíte Premium',
            'descricao': 'Descrição da suíte premium',
            'preco': '350.00',
            'capacidade_pessoas': '3',
            'tags': 'Casal, Serra',
            'comodidades': 'Ar Condicionado, Wi-Fi',
            'unidades_ids': ['new', 'new'],
            'unidades_identificadores': ['101', '102'],
        }
        
        request = self.factory.post('/hospedagens/quartos/formulario/salvar/', data)
        request.user = self.user
        request.session = {}
        
        # Enable messages framework in request using MockStorage
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_quarto_salvar(request)
        self.assertEqual(response.status_code, 200)
        
        # Verify Quarto was created
        quarto = Quarto.objects.get(nome='Suíte Premium', hotel=self.hotel)
        self.assertEqual(quarto.preco, 350.00)
        self.assertEqual(quarto.capacidade_pessoas, 3)
        
        # Verify UnidadeQuarto instances were created
        units = list(quarto.unidades.filter(ativa=True).order_by('identificador'))
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].identificador, '101')
        self.assertEqual(units[1].identificador, '102')

    def test_edit_existing_quarto_units(self):
        # First, create a quarto with some units
        quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Suíte Master',
            preco=400.00,
            capacidade_pessoas=2
        )
        u1 = UnidadeQuarto.objects.create(quarto=quarto, identificador='201', ativa=True)
        u2 = UnidadeQuarto.objects.create(quarto=quarto, identificador='202', ativa=True)
        
        # Now edit: update 201 to 201-A, keep 202, add new unit 203
        data = {
            'quarto_id': str(quarto.id),
            'nome': 'Suíte Master Modificada',
            'descricao': 'Nova desc',
            'preco': '450.00',
            'capacidade_pessoas': '2',
            'unidades_ids': [str(u1.id), str(u2.id), 'new'],
            'unidades_identificadores': ['201-A', '202', '203'],
        }
        
        request = self.factory.post('/hospedagens/quartos/formulario/salvar/', data)
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_quarto_salvar(request)
        self.assertEqual(response.status_code, 200)
        
        # Verify Quarto updated
        quarto.refresh_from_db()
        self.assertEqual(quarto.nome, 'Suíte Master Modificada')
        self.assertEqual(quarto.preco, 450.00)
        
        # Verify units updated and new added
        units = list(quarto.unidades.filter(ativa=True).order_by('identificador'))
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0].identificador, '201-A')
        self.assertEqual(units[1].identificador, '202')
        self.assertEqual(units[2].identificador, '203')
        
        # Verify that u1 was updated (not recreated)
        u1.refresh_from_db()
        self.assertEqual(u1.identificador, '201-A')

    def test_delete_existing_quarto_unit(self):
        # Create a quarto with some units
        quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Chalé Luxo',
            preco=500.00,
            capacidade_pessoas=4
        )
        u1 = UnidadeQuarto.objects.create(quarto=quarto, identificador='Ch-01', ativa=True)
        u2 = UnidadeQuarto.objects.create(quarto=quarto, identificador='Ch-02', ativa=True)
        
        # Edit and submit only Ch-01 (effectively removing Ch-02)
        data = {
            'quarto_id': str(quarto.id),
            'nome': 'Chalé Luxo',
            'descricao': 'Desc',
            'preco': '500.00',
            'capacidade_pessoas': '4',
            'unidades_ids': [str(u1.id)],
            'unidades_identificadores': ['Ch-01'],
        }
        
        request = self.factory.post('/hospedagens/quartos/formulario/salvar/', data)
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_quarto_salvar(request)
        self.assertEqual(response.status_code, 200)
        
        # Verify Ch-02 deleted
        active_units = list(quarto.unidades.filter(ativa=True))
        self.assertEqual(len(active_units), 1)
        self.assertEqual(active_units[0].identificador, 'Ch-01')
        
        # Verify Ch-02 is physically deleted
        self.assertFalse(UnidadeQuarto.objects.filter(id=u2.id).exists())

    def test_delete_existing_quarto_unit_with_booking_deactivates(self):
        # Create a quarto with some units
        quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Chalé Booking',
            preco=500.00,
            capacidade_pessoas=4
        )
        u1 = UnidadeQuarto.objects.create(quarto=quarto, identificador='Ch-01', ativa=True)
        u2 = UnidadeQuarto.objects.create(quarto=quarto, identificador='Ch-02', ativa=True)
        
        # Create booking pointing to u2
        Reserva.objects.create(
            unidade=u2,
            data_checkin=datetime.date.today(),
            data_checkout=datetime.date.today() + datetime.timedelta(days=2),
            valor_total=1000.00,
            status='confirmada'
        )
        
        # Edit and submit only Ch-01 (effectively removing Ch-02, which is linked to a booking)
        data = {
            'quarto_id': str(quarto.id),
            'nome': 'Chalé Booking',
            'descricao': 'Desc',
            'preco': '500.00',
            'capacidade_pessoas': '4',
            'unidades_ids': [str(u1.id)],
            'unidades_identificadores': ['Ch-01'],
        }
        
        request = self.factory.post('/hospedagens/quartos/formulario/salvar/', data)
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_quarto_salvar(request)
        self.assertEqual(response.status_code, 200)
        
        # Verify Ch-01 remains active
        active_units = list(quarto.unidades.filter(ativa=True))
        self.assertEqual(len(active_units), 1)
        self.assertEqual(active_units[0].identificador, 'Ch-01')
        
        # Verify Ch-02 is deactivated (ativa=False) but still exists in database due to foreign key
        u2.refresh_from_db()
        self.assertFalse(u2.ativa)
        self.assertTrue(UnidadeQuarto.objects.filter(id=u2.id).exists())


class PartnerReservaSaveTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='partner_res_user', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test Empresa 2',
            razao_social='Test Empresa 2 LTDA',
            cnpj='98.765.432/0001-10',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='contato2@test.com',
            telefone_contato='88999999998'
        )
        self.local = Local.objects.create(nome='Test Local 2', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos 2',
            descricao='Pousada Teste 2',
            local=self.local,
            slug='pousadaramilos2'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )
        self.quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Suíte Executiva',
            preco=250.00,
            capacidade_pessoas=2
        )
        self.unidade = UnidadeQuarto.objects.create(quarto=self.quarto, identificador='105', ativa=True)

    def test_create_reserva_manual_with_brl_format(self):
        from hoteis.views import partner_reserva_criar
        
        # We will post formatted BRL price e.g. "1.250,00"
        data = {
            'unidade_id': str(self.unidade.id),
            'data_checkin': (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'data_checkout': (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'valor_total': '1.250,00',
            'status': 'confirmada',
            'quantidade_hospedes': '2',
            'nome_1': 'Hóspede Um',
            'cpf_1': '123.456.789-01',
            'email_1': 'h1@gmail.com',
            'telefone_1': '(88) 99999-8888',
            'nome_2': 'Hóspede Dois',
            'cpf_2': '987.654.321-02',
        }
        
        request = self.factory.post('/hospedagens/sistema/reservas/criar/', data)
        request.user = self.user
        request.session = {}
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_reserva_criar(request)
        self.assertEqual(response.status_code, 200)
        
        # Verify Reserva was created with correct parsed price
        reserva = Reserva.objects.get(unidade=self.unidade)
        self.assertEqual(reserva.valor_total, 1250.00)
        self.assertEqual(reserva.quantidade_hospedes, 2)
        
        # Verify guests
        hospedes = list(reserva.hospedes.all().order_by('ordem'))
        self.assertEqual(len(hospedes), 2)
        self.assertEqual(hospedes[0].nome, 'Hóspede Um')
        self.assertEqual(hospedes[0].cpf, '123.456.789-01')
        self.assertEqual(hospedes[1].nome, 'Hóspede Dois')


class ConciergeTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='partner_res_user', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test Empresa 2',
            razao_social='Test Empresa 2 LTDA',
            cnpj='98.765.432/0001-10',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='contato2@test.com',
            telefone_contato='88999999998'
        )
        self.local = Local.objects.create(nome='Test Local 2', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos 2',
            descricao='Pousada Teste 2',
            local=self.local,
            slug='pousadaramilos2'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )
        self.quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Suíte Executiva',
            preco=250.00,
            capacidade_pessoas=2
        )
        self.unidade = UnidadeQuarto.objects.create(quarto=self.quarto, identificador='105', ativa=True)
        
        # Create an active reservation
        self.reserva = Reserva.objects.create(
            unidade=self.unidade,
            data_checkin=datetime.date.today(),
            data_checkout=datetime.date.today() + datetime.timedelta(days=2),
            valor_total=500.00,
            status='hospedado',
            quantidade_hospedes=1
        )
        
        # Create a consumption product
        from hoteis.models import ProdutoConsumo
        self.produto = ProdutoConsumo.objects.create(
            hotel=self.hotel,
            nome='Coca-Cola Lata',
            preco=6.50,
            tipo='bebida',
            disponivel=True
        )

    def test_partner_hospedes_pedidos_authorized(self):
        from hoteis.views import partner_hospedes_pedidos
        from hoteis.models import PedidoServico
        
        # Create a service order
        PedidoServico.objects.create(
            reserva=self.reserva,
            unidade=self.unidade,
            hotel=self.hotel,
            status='pendente',
            valor_total=0.0
        )
        
        request = self.factory.get('/partner/hospedes/pedidos/')
        request.user = self.user
        request.session = {}
        
        response = partner_hospedes_pedidos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Solicitação de serviço de quarto', status_code=200, html=False)

    def test_partner_hospedes_pedidos_empty(self):
        from hoteis.views import partner_hospedes_pedidos
        
        request = self.factory.get('/partner/hospedes/pedidos/')
        request.user = self.user
        request.session = {}
        
        response = partner_hospedes_pedidos(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhum pedido de quarto ativo', status_code=200, html=False)

    def test_partner_hospedes_pedidos_unauthorized(self):
        from hoteis.views import partner_hospedes_pedidos
        
        # Create an unauthorized user without a perfil_parceiro
        unauthorized_user = User.objects.create_user(username='other_user', password='password123')
        request = self.factory.get('/partner/hospedes/pedidos/')
        request.user = unauthorized_user
        request.session = {}
        
        response = partner_hospedes_pedidos(request)
        self.assertEqual(response.status_code, 403)

    def test_partner_hospedes_atualizar_status(self):
        from hoteis.views import partner_hospedes_atualizar_status
        from hoteis.models import PedidoServico
        
        pedido = PedidoServico.objects.create(
            reserva=self.reserva,
            unidade=self.unidade,
            hotel=self.hotel,
            status='pendente',
            valor_total=0.0
        )
        
        request = self.factory.post(f'/partner/hospedes/pedido/{pedido.id}/status/', {'status': 'preparo'})
        request.user = self.user
        request.session = {}
        
        response = partner_hospedes_atualizar_status(request, pedido_id=pedido.id)
        self.assertEqual(response.status_code, 200)
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, 'preparo')
        self.assertContains(response, 'Em Preparo')

    def test_partner_hospedes_lancar_consumo(self):
        from hoteis.views import partner_hospedes_lancar_consumo
        from hoteis.models import PedidoServico, ItemPedidoServico, ReservaLog
        
        data = {
            'produto_id': str(self.produto.id),
            'quantidade': '2',
            'observacoes': 'Teste de consumo'
        }
        
        request = self.factory.post(f'/partner/hospedes/reserva/{self.reserva.id}/lancar/', data)
        request.user = self.user
        request.session = {}
        
        response = partner_hospedes_lancar_consumo(request, reserva_id=self.reserva.id)
        self.assertEqual(response.status_code, 200)
        
        # Check that reservation total value increased by 2 * 6.50 = 13.00
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.valor_total, 513.00)
        
        # Check that PedidoServico and ItemPedidoServico were created
        pedido = PedidoServico.objects.filter(reserva=self.reserva).first()
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.status, 'entregue')
        self.assertEqual(pedido.valor_total, 13.00)
        
        item = ItemPedidoServico.objects.filter(pedido=pedido).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.produto, self.produto)
        self.assertEqual(item.quantidade, 2)
        self.assertEqual(item.preco_unitario, 6.50)
        
        # Check that audit log was created
        log = ReservaLog.objects.filter(reserva=self.reserva, acao='consumo_lancado').first()
        self.assertIsNotNone(log)
        self.assertIn('Coca-Cola Lata', log.detalhes)


class CheckoutPaymentTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='checkout_user', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test Empresa Checkout',
            razao_social='Test Empresa Checkout LTDA',
            cnpj='88.765.432/0001-10',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='contato3@test.com',
            telefone_contato='88999999998'
        )
        self.local = Local.objects.create(nome='Test Local Checkout', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos Checkout',
            descricao='Pousada Teste Checkout',
            local=self.local,
            slug='pousadacheckout'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )
        self.quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Suíte Executiva',
            preco=250.00,
            capacidade_pessoas=2
        )
        self.unidade = UnidadeQuarto.objects.create(quarto=self.quarto, identificador='105', ativa=True)
        
        # Pre-configured B2C Session Cart
        self.cart_session = {
            'quarto_id': self.quarto.id,
            'unidade_identificador': '105',
            'checkin': (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'checkout': (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'quantidade_hospedes': 1,
            'hospedes': [{
                'nome': 'Hóspede Titular',
                'cpf': '123.456.789-01',
                'email': 'titular@gmail.com',
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

    def test_checkout_pagamento_get(self):
        from hoteis.views import checkout_processar
        
        request = self.factory.get('/carrinho/checkout/')
        request.user = self.user
        request.session = MockSession({'carrinho': self.cart_session})
        setattr(request, '_messages', MockStorage(request))
        
        response = checkout_processar(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Pagamento', status_code=200, html=False)

    @patch('requests.post')
    def test_checkout_processar_post_card_approved(self, mock_post):
        from hoteis.views import checkout_processar
        from hoteis.models import Reserva
        
        # Mock Mercado Pago Response
        mock_response = mock_post.return_value
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'status': 'processed',
            'status_detail': 'accredited',
            'id': 'ORDTST1234567890',
            'transactions': {
                'payments': [{
                    'id': 'PAY12345',
                    'status': 'processed',
                    'status_detail': 'accredited'
                }]
            }
        }
        
        data = {
            'forma_pagamento': 'cartao',
            'token': 'mock_token_123',
            'payment_method_id': 'visa',
            'installments': 1
        }
        
        request = self.factory.post(
            '/carrinho/checkout/', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.user = self.user
        request.session = MockSession({'carrinho': self.cart_session})
        setattr(request, '_messages', MockStorage(request))
        
        response = checkout_processar(request)
        self.assertEqual(response.status_code, 200)
        
        resp_json = json.loads(response.content)
        self.assertTrue(resp_json['success'])
        self.assertIn('redirect_url', resp_json)
        
        # Verify Reserva created
        reserva = Reserva.objects.get(id=resp_json['reserva_id'])
        self.assertEqual(reserva.status, 'confirmada')
        self.assertEqual(reserva.valor_total, 550.00)

    @patch('requests.post')
    def test_checkout_processar_post_pix_pending(self, mock_post):
        from hoteis.views import checkout_processar
        from hoteis.models import Reserva
        
        # Mock Mercado Pago Response
        mock_response = mock_post.return_value
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'status': 'action_required',
            'status_detail': 'waiting_transfer',
            'id': 'ORDTST987654321',
            'transactions': {
                'payments': [{
                    'id': 'PAY98765',
                    'status': 'action_required',
                    'status_detail': 'waiting_transfer',
                    'payment_method': {
                        'id': 'pix',
                        'type': 'bank_transfer',
                        'qr_code': 'mock_pix_copy_paste_code_here',
                        'qr_code_base64': 'mock_base64_image_data'
                    }
                }]
            }
        }
        
        data = {
            'forma_pagamento': 'pix'
        }
        
        request = self.factory.post(
            '/carrinho/checkout/', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.user = self.user
        request.session = MockSession({'carrinho': self.cart_session})
        setattr(request, '_messages', MockStorage(request))
        
        response = checkout_processar(request)
        self.assertEqual(response.status_code, 200)
        
        resp_json = json.loads(response.content)
        self.assertTrue(resp_json['success'])
        self.assertEqual(resp_json['forma_pagamento'], 'pix')
        self.assertEqual(resp_json['pix_qr_code'], 'mock_pix_copy_paste_code_here')
        self.assertEqual(resp_json['pix_qr_code_base64'], 'mock_base64_image_data')
        
        # Verify Reserva created as pending
        reserva = Reserva.objects.get(id=resp_json['reserva_id'])
        self.assertEqual(reserva.status, 'pendente')

    @patch('requests.post')
    def test_checkout_processar_post_card_declined(self, mock_post):
        from hoteis.views import checkout_processar
        
        # Mock Mercado Pago Response to return an error (400 Bad Request)
        mock_response = mock_post.return_value
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'message': 'Invalid card token.',
            'cause': [{
                'code': '2063',
                'description': 'The card token is invalid or expired.'
            }]
        }
        
        data = {
            'forma_pagamento': 'cartao',
            'token': 'invalid_token',
            'payment_method_id': 'visa',
            'installments': 1
        }
        
        request = self.factory.post(
            '/carrinho/checkout/', 
            data=json.dumps(data), 
            content_type='application/json'
        )
        request.user = self.user
        request.session = MockSession({'carrinho': self.cart_session})
        setattr(request, '_messages', MockStorage(request))
        
        response = checkout_processar(request)
        self.assertEqual(response.status_code, 400)
        
        resp_json = json.loads(response.content)
        self.assertFalse(resp_json['success'])
        self.assertEqual(resp_json['error'], 'Pagamento Recusado: The card token is invalid or expired.')


from hoteis.views import partner_secao_salvar, partner_secao_deletar, partner_secao_item_salvar, partner_secao_item_deletar

class PartnerSecaoTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='secao_partner', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test CMS',
            razao_social='Test CMS LTDA',
            cnpj='33.444.555/0001-22',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='contato@test.com',
            telefone_contato='88999999999'
        )
        self.local = Local.objects.create(nome='Test Local', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada CMS',
            descricao='Pousada CMS Teste',
            local=self.local,
            slug='pousadacms'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )

    def test_create_and_delete_secao(self):
        # 1. Create a section
        data = {
            'titulo': 'Atrações Sítio',
            'subtitulo': 'Subtítulo',
            'tipo': 'atracoes',
            'ordem': '1',
            'ativa': 'on'
        }
        request = self.factory.post('/hospedagens/secoes/salvar/', data)
        request.user = self.user
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_secao_salvar(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('HX-Redirect'), '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes')
        
        secao = HotelSecao.objects.get(titulo='Atrações Sítio', hotel=self.hotel)
        self.assertEqual(secao.tipo, 'atracoes')
        self.assertEqual(secao.ordem, 1)
        self.assertTrue(secao.ativa)

        # 2. Add an item to this section
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Small mock image
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded_image = SimpleUploadedFile('test.gif', small_gif, content_type='image/gif')
        
        item_data = {
            'secao_id': secao.id,
            'titulo': 'Voo Livre',
            'descricao': 'Voe de parapente',
            'preco': '150.00',
            'link_cta': 'https://sitiodobosco.com.br',
            'ordem': '2',
            'imagem': uploaded_image
        }
        
        item_request = self.factory.post('/hospedagens/secoes/itens/salvar/', item_data)
        item_request.user = self.user
        item_request.FILES['imagem'] = uploaded_image
        setattr(item_request, '_messages', MockStorage(request))
        
        item_response = partner_secao_item_salvar(item_request)
        self.assertEqual(item_response.status_code, 200)
        
        item = HotelSecaoItem.objects.get(titulo='Voo Livre', secao=secao)
        self.assertEqual(item.preco, Decimal('150.00'))
        self.assertEqual(item.link_cta, 'https://sitiodobosco.com.br')
        self.assertEqual(item.ordem, 2)

        # Cleanup files created during test
        if item.imagem:
            item.imagem.delete(save=False)

    def test_vanity_url_context_has_destaques_personalizado(self):
        # Create a destaques section
        secao = HotelSecao.objects.create(
            hotel=self.hotel,
            titulo="Destaques Especiais",
            tipo="destaques",
            ativa=True
        )
        
        # Access vanity url
        from django.urls import reverse
        response = self.client.get(reverse('hoteis:vanity_url', kwargs={'slug': self.hotel.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('destaques_personalizado', response.context)
        self.assertEqual(response.context['destaques_personalizado'].id, secao.id)

    def test_secao_cleanup_on_type_change(self):
        # 1. Create a section with video and text
        secao = HotelSecao.objects.create(
            hotel=self.hotel,
            titulo="Seção Vídeo",
            tipo="video",
            video_url="https://youtube.com/watch?v=123",
            texto="Descrição do vídeo"
        )
        
        # 2. Change layout type to 'galeria' which does not support video_url or texto
        data = {
            'titulo': 'Seção Vídeo',
            'tipo': 'galeria',
            'ordem': '0',
            'ativa': 'on'
        }
        request = self.factory.post(f'/hospedagens/secoes/salvar/{secao.id}/', data)
        request.user = self.user
        setattr(request, '_messages', MockStorage(request))
        
        response = partner_secao_salvar(request, secao_id=secao.id)
        self.assertEqual(response.status_code, 200)
        
        # Reload section
        secao.refresh_from_db()
        self.assertEqual(secao.tipo, 'galeria')
        self.assertIsNone(secao.video_url)
        self.assertIsNone(secao.texto)


class PartnerQuartoDisponibilidadeTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='partner_user_disp', password='password123')
        self.empresa = Empresa.objects.create(
            nome_fantasia='Test Hotel Co',
            razao_social='Test Hotel Co LTDA',
            cnpj='11.222.333/0001-44',
            categoria='hospedagem'
        )
        self.local = Local.objects.create(nome='Local Test', endereco='Rua A, 1', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Hotel Test',
            local=self.local,
            slug='hoteltest'
        )
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )
        self.quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Chalé Luxo',
            preco=250.00,
            capacidade_pessoas=2
        )
        self.unidade = UnidadeQuarto.objects.create(
            quarto=self.quarto,
            identificador='Chalé 01',
            ativa=True
        )

    def test_atualizar_disponibilidade_indisponivel_manutencao(self):
        from hoteis.views import partner_atualizar_disponibilidade_quarto
        from hoteis.models import Tarefa
        
        data = {
            'disponivel': 'false',
            'motivo_indisponivel': 'manutencao',
            'justificativa_indisponivel': 'Ar condicionado quebrado'
        }
        
        request = self.factory.post(f'/hospedagens/quartos/atualizar-disponibilidade/{self.unidade.id}/', data)
        request.user = self.user
        request.session = {}
        
        response = partner_atualizar_disponibilidade_quarto(request, self.unidade.id)
        self.assertEqual(response.status_code, 200)
        
        self.unidade.refresh_from_db()
        self.assertFalse(self.unidade.disponivel)
        self.assertEqual(self.unidade.motivo_indisponivel, 'manutencao')
        self.assertEqual(self.unidade.justificativa_indisponivel, 'Ar condicionado quebrado')
        self.assertEqual(self.unidade.status_mapa, 'indisponivel')
        
        # Check if task was created
        task_exists = Tarefa.objects.filter(unidade=self.unidade, status='todo', titulo__icontains='Manutenção').exists()
        self.assertTrue(task_exists)

    def test_atualizar_disponibilidade_voltar_disponivel(self):
        from hoteis.views import partner_atualizar_disponibilidade_quarto
        from hoteis.models import Tarefa
        
        # Set to unavailable first
        self.unidade.disponivel = False
        self.unidade.motivo_indisponivel = 'limpeza'
        self.unidade.save()
        
        # Create active clean task
        task = Tarefa.objects.create(
            hotel=self.hotel,
            titulo="Limpeza e Preparação",
            unidade=self.unidade,
            status='todo'
        )
        
        data = {
            'disponivel': 'true'
        }
        
        request = self.factory.post(f'/hospedagens/quartos/atualizar-disponibilidade/{self.unidade.id}/', data)
        request.user = self.user
        request.session = {}
        
        response = partner_atualizar_disponibilidade_quarto(request, self.unidade.id)
        self.assertEqual(response.status_code, 200)
        
        self.unidade.refresh_from_db()
        self.assertTrue(self.unidade.disponivel)
        self.assertIsNone(self.unidade.motivo_indisponivel)
        self.assertEqual(self.unidade.status_mapa, 'livre')
        
        # Check if task was marked done
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')

    def test_verifica_disponibilidade_unidade_checks_availability(self):
        from hoteis.utils import verifica_disponibilidade_unidade, checar_disponibilidade_quarto
        import datetime
        
        checkin = datetime.date.today()
        checkout = checkin + datetime.timedelta(days=2)
        
        # Initially available
        self.assertTrue(verifica_disponibilidade_unidade(self.unidade, checkin, checkout))
        self.assertTrue(checar_disponibilidade_quarto(self.quarto, checkin, checkout))
        
        # Make unavailable
        self.unidade.disponivel = False
        self.unidade.save()
        
        self.assertFalse(verifica_disponibilidade_unidade(self.unidade, checkin, checkout))
        self.assertFalse(checar_disponibilidade_quarto(self.quarto, checkin, checkout))






