from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from parceiros.models import SolicitacaoEmpresa, StatusSolicitacao, TipoEmpresa
from hoteis.models import Hotel, ParceiroUsuario

class AdministracaoAuthTests(TestCase):
    databases = {'default', 'parceiros', 'hospedagem'}

    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('administracao:dashboard')
        self.login_url = reverse('administracao:login')
        
        # Criar usuários
        self.superuser = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpassword'
        )
        self.normal_user = User.objects.create_user(
            username='client_test',
            email='client@test.com',
            password='testpassword'
        )
        
        # Criar solicitação fictícia
        self.solicitacao = SolicitacaoEmpresa.objects.create(
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Empresa Teste",
            cnpj="12.345.678/0001-90",
            tipo_empresa=TipoEmpresa.HOTEL_POUSADA,
            cep="12345-678",
            endereco="Rua Teste",
            numero="100",
            cidade="Cidade Teste",
            estado="CE",
            responsavel_nome="Responsavel Teste",
            responsavel_cargo="Diretor",
            responsavel_email="responsavel@test.com",
            responsavel_telefone="(88) 99999-9999",
            descricao_negocio="Uma empresa de teste",
            status=StatusSolicitacao.PENDENTE
        )

    def test_anonymous_user_redirected(self):
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.dashboard_url}")

    def test_normal_user_redirected(self):
        self.client.login(username='client_test', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.dashboard_url}")

    def test_superuser_can_access_dashboard(self):
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Teste")
        self.assertContains(response, "Dashboard de Controle")

    def test_superuser_can_update_status(self):
        self.client.login(username='admin_test', password='testpassword')
        update_url = reverse('administracao:solicitacao_update_status', kwargs={'pk': self.solicitacao.pk})
        
        response = self.client.post(update_url, {
            'status': StatusSolicitacao.APROVADO,
            'notas_internas': "Aprovado nos testes automatizados."
        })
        
        self.solicitacao.refresh_from_db()
        self.assertEqual(self.solicitacao.status, StatusSolicitacao.APROVADO)
        self.assertEqual(self.solicitacao.notas_internas, "Aprovado nos testes automatizados.")
        self.assertEqual(self.solicitacao.atendido_por, 'admin_test')

    def test_hoteis_list_view_restricted(self):
        hoteis_list_url = reverse('administracao:hoteis_list')
        response = self.client.get(hoteis_list_url)
        self.assertRedirects(response, f"{self.login_url}?next={hoteis_list_url}")

    def test_superuser_can_create_hotel(self):
        self.client.login(username='admin_test', password='testpassword')
        create_url = reverse('administracao:hotel_create')
        
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Hotel / Pousada")
        
        post_data = {
            'nome_fantasia': 'Pousada Teste Sol',
            'razao_social': 'Pousada Teste Sol LTDA',
            'cnpj': '99.888.777/0001-66',
            'descricao': 'Uma pousada teste charmosa.',
            'whatsapp': '(88) 98888-8888',
            'email_contato': 'sol@pousadateste.com',
            'slug': 'pousadatestesol',
            'cor_primaria': '#e11d48',
            'status': 'ativo',
            'destaque': 'on',
            'cep': '62300-000',
            'endereco': 'Rua Principal, 500',
            'cidade': 'Tianguá',
            'estado': 'CE',
            'local_id': 'new',
            'local_nome': 'Tianguá Centro Novo',
            'responsavel_nome': 'Joao Proprietario',
            'username': 'joaoprop',
            'user_email': 'joao@pousadateste.com',
            'password': 'joaopassword',
            'password_confirm': 'joaopassword',
            'cpf': '123.456.789-00'
        }
        
        response = self.client.post(create_url, post_data)
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        hotel = Hotel.objects.get(slug='pousadatestesol')
        self.assertEqual(hotel.nome, 'Pousada Teste Sol')
        self.assertEqual(hotel.local.nome, 'Tianguá Centro Novo')
        self.assertEqual(hotel.empresa.cnpj, '99.888.777/0001-66')
        
        user = User.objects.get(username='joaoprop')
        self.assertEqual(user.first_name, 'Joao Proprietario')
        
        parceiro = ParceiroUsuario.objects.get(user=user)
        self.assertEqual(parceiro.hotel, hotel)
        self.assertEqual(parceiro.role, 'proprietario')
        self.assertEqual(parceiro.cpf, '123.456.789-00')
