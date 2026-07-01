from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from core.models import Empresa
from hoteis.models import Local, Hotel, ParceiroUsuario
from hoteis.middleware import PartnerHotelMiddleware

class MultiPousadaTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        
        # 1. Create two companies (Empresas)
        self.empresa_grupo = Empresa.objects.create(
            nome_fantasia='Grupo Ramilos',
            razao_social='Ramilos Hoteis LTDA',
            cnpj='12.345.678/0001-90',
            categoria='hospedagem',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='grupo@ramilos.com',
            telefone_contato='88999999999'
        )
        self.empresa_outra = Empresa.objects.create(
            nome_fantasia='Outra Pousada Solo',
            razao_social='Solo LTDA',
            cnpj='98.765.432/0001-21',
            categoria='hospedagem',
            endereco='Rua Lateral, 50',
            cidade='Ubajara',
            estado='CE',
            cep='62350-000',
            email_contato='contato@solo.com',
            telefone_contato='88988888888'
        )
        
        self.local = Local.objects.create(nome='Test Local', endereco='Av. Central, 100', cidade='Tianguá', estado='CE')
        
        # 2. Create three hotels
        # Hotel A and B belong to Grupo Ramilos (multi-property group)
        self.hotel_a = Hotel.objects.create(
            empresa=self.empresa_grupo,
            nome='Pousada Ramilos Centro',
            descricao='Centro de Tianguá',
            local=self.local,
            slug='ramiloscentro',
            status='ativo'
        )
        self.hotel_b = Hotel.objects.create(
            empresa=self.empresa_grupo,
            nome='Pousada Ramilos Praia',
            descricao='Praia de Tianguá (imaginária)',
            local=self.local,
            slug='ramilospraia',
            status='ativo'
        )
        # Hotel C belongs to a different company
        self.hotel_c = Hotel.objects.create(
            empresa=self.empresa_outra,
            nome='Pousada Solo Ubajara',
            descricao='Serra de Ubajara',
            local=self.local,
            slug='pousadasolo',
            status='ativo'
        )
        
        # 3. Create users with different roles
        self.user_owner = User.objects.create_user(username='tiago_proprietario', password='password123')
        self.user_portaria = User.objects.create_user(username='roberto_portaria', password='password123')
        
        # 4. Create partner profiles
        self.perfil_owner = ParceiroUsuario.objects.create(
            user=self.user_owner,
            hotel=self.hotel_a,
            role='proprietario',
            ativo=True
        )
        self.perfil_portaria = ParceiroUsuario.objects.create(
            user=self.user_portaria,
            hotel=self.hotel_a,
            role='portaria',
            ativo=True
        )
        self.user_camareira = User.objects.create_user(username='juliana_camareira', password='password123')
        self.perfil_camareira = ParceiroUsuario.objects.create(
            user=self.user_camareira,
            hotel=self.hotel_a,
            role='camareira',
            ativo=True
        )
        
        # Initialize middleware
        self.middleware = PartnerHotelMiddleware(get_response=lambda r: r)

    def _prepare_request(self, request, user):
        request.user = user
        # Add session middleware interface
        session_middleware = SessionMiddleware(get_response=lambda r: r)
        session_middleware.process_request(request)
        return request

    def test_owner_can_see_all_company_hotels(self):
        request = self.factory.get('/hospedagens/sistema/')
        request = self._prepare_request(request, self.user_owner)
        
        self.middleware(request)
        
        # Should populate hoteis_autorizados with hotel_a and hotel_b
        hoteis_ids = [h.id for h in request.hoteis_autorizados]
        self.assertIn(self.hotel_a.id, hoteis_ids)
        self.assertIn(self.hotel_b.id, hoteis_ids)
        self.assertNotIn(self.hotel_c.id, hoteis_ids)
        self.assertEqual(request.hotel_ativo.id, self.hotel_a.id)

    def test_owner_can_switch_hotel_via_get_param(self):
        # Request with ?set_hotel=B_ID
        request = self.factory.get(f'/hospedagens/sistema/?set_hotel={self.hotel_b.id}')
        request = self._prepare_request(request, self.user_owner)
        
        self.middleware(request)
        
        # Active hotel should switch to hotel_b
        self.assertEqual(request.hotel_ativo.id, self.hotel_b.id)
        self.assertEqual(request.session['active_hotel_id'], self.hotel_b.id)
        
        # In-memory dynamic shadowing should update the profile
        self.assertEqual(request.user.perfil_parceiro.hotel.id, self.hotel_b.id)

    def test_owner_preserves_switched_hotel_from_session(self):
        request = self.factory.get('/hospedagens/sistema/')
        request = self._prepare_request(request, self.user_owner)
        
        # Inject active_hotel_id directly in session
        request.session['active_hotel_id'] = self.hotel_b.id
        
        self.middleware(request)
        
        # Active hotel should load from session
        self.assertEqual(request.hotel_ativo.id, self.hotel_b.id)
        self.assertEqual(request.user.perfil_parceiro.hotel.id, self.hotel_b.id)

    def test_owner_cannot_switch_to_other_company_hotel(self):
        # Try to switch to hotel_c (which belongs to a different company)
        request = self.factory.get(f'/hospedagens/sistema/?set_hotel={self.hotel_c.id}')
        request = self._prepare_request(request, self.user_owner)
        
        self.middleware(request)
        
        # Switch should be ignored, falling back to hotel_a
        self.assertEqual(request.hotel_ativo.id, self.hotel_a.id)
        self.assertEqual(request.user.perfil_parceiro.hotel.id, self.hotel_a.id)

    def test_operatives_cannot_switch_hotel(self):
        # Juliana Camareira (operativo role) tries to switch to hotel_b
        request = self.factory.get(f'/hospedagens/sistema/?set_hotel={self.hotel_b.id}')
        request = self._prepare_request(request, self.user_camareira)
        
        self.middleware(request)
        
        # Switch should be ignored, locked to hotel_a
        self.assertEqual(request.hotel_ativo.id, self.hotel_a.id)
        self.assertEqual(request.user.perfil_parceiro.hotel.id, self.hotel_a.id)
        
        # and list of authorized hotels should be empty
        self.assertEqual(request.hoteis_autorizados, [])

    def test_portaria_can_switch_hotel(self):
        # Roberto Portaria tries to switch to hotel_b
        request = self.factory.get(f'/hospedagens/sistema/?set_hotel={self.hotel_b.id}')
        request = self._prepare_request(request, self.user_portaria)
        
        self.middleware(request)
        
        # Switch should succeed, switching to hotel_b
        self.assertEqual(request.hotel_ativo.id, self.hotel_b.id)
        self.assertEqual(request.user.perfil_parceiro.hotel.id, self.hotel_b.id)
        
        # and list of authorized hotels should contain both
        hoteis_ids = [h.id for h in request.hoteis_autorizados]
        self.assertIn(self.hotel_a.id, hoteis_ids)
        self.assertIn(self.hotel_b.id, hoteis_ids)
