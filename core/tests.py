from django.test import TestCase, RequestFactory
from django.shortcuts import redirect
from core.models import Empresa
from hoteis.models import Local, Hotel
from core.middleware import SubdomainMiddleware
from django.http import Http404

class SubdomainMiddlewareTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SubdomainMiddleware(get_response=lambda r: r)
        
        # 1. Create a unified company (Empresa)
        self.empresa = Empresa.objects.create(
            nome_fantasia='Grupo Ramilos',
            razao_social='Ramilos Hoteis LTDA',
            cnpj='12.345.678/0001-90',
            categoria='hospedagem',
            slug='pousadasramilos',
            modalidade_portal='unificado',
            ativa=True
        )
        
        self.local = Local.objects.create(
            nome='Tianguá Local',
            endereco='Av. Central, 100',
            cidade='Tianguá',
            estado='CE'
        )
        
        # 2. Create hotels belonging to the company
        self.hotel_tiangua = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos Tianguá',
            descricao='Serra',
            local=self.local,
            slug='ramilostiangua',
            status='ativo'
        )
        self.hotel_praia = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Ramilos Praia',
            descricao='Praia',
            local=self.local,
            slug='ramilospraia',
            status='ativo'
        )

    def test_unified_portal_subdomain_resolves_empresa(self):
        request = self.factory.get('/', HTTP_HOST='pousadasramilos.navievibe.com')
        self.middleware(request)
        
        self.assertEqual(getattr(request, 'subdomain', None), 'pousadasramilos')
        self.assertEqual(getattr(request, 'empresa_atual', None), self.empresa)

    def test_old_hotel_subdomain_does_not_redirect_and_sets_hotel(self):
        request = self.factory.get('/', HTTP_HOST='ramilostiangua.navievibe.com')
        response = self.middleware(request)
        
        # Should not redirect, so the response is our get_response mock (request itself)
        self.assertEqual(response, request)
        self.assertEqual(getattr(request, 'subdomain', None), 'ramilostiangua')
        self.assertEqual(getattr(request, 'hotel_atual', None), self.hotel_tiangua)

    def test_old_hotel_subdomain_b2b_route_does_not_redirect(self):
        # Accessing dashboard should bypass redirect
        request = self.factory.get('/hospedagens/sistema/', HTTP_HOST='ramilostiangua.navievibe.com')
        response = self.middleware(request)
        
        # Should not be intercepted by redirect, so the response is our get_response mock (request itself)
        self.assertEqual(response, request)
        self.assertEqual(getattr(request, 'subdomain', None), 'ramilostiangua')
        self.assertEqual(getattr(request, 'hotel_atual', None), self.hotel_tiangua)

    def test_nonexistent_subdomain_b2c_raises_404(self):
        request = self.factory.get('/', HTTP_HOST='nonexistent.navievibe.com')
        with self.assertRaises(Http404):
            self.middleware(request)

    def test_nonexistent_subdomain_b2b_does_not_raise_404(self):
        # Accessing login or dashboard under random subdomain should bypass 404 override
        request = self.factory.get('/hospedagens/auth/', HTTP_HOST='nonexistent.navievibe.com')
        response = self.middleware(request)
        self.assertEqual(response, request)
