from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from clientes.models import ClientePerfil
import json

class ClientePerfilModelTest(TestCase):
    databases = {'default', 'hospedagem'}
    """
    Test suite for the ClientePerfil database model.
    Verifies creation, relationship integrity, and audit logging features.
    """

    def setUp(self):
        # Create standard Django user
        self.user = User.objects.create_user(
            username='123.456.789-00',
            email='test@navievibe.com',
            password='securepassword123',
            first_name='João',
            last_name='Silva'
        )

    def test_profile_creation_and_fields(self):
        """
        Verify that a ClientePerfil can be successfully created and associated with a User.
        """
        perfil = ClientePerfil.objects.create(
            user=self.user,
            cpf='123.456.789-00',
            telefone='(88) 99999-9999',
            cep='62320-000',
            endereco='Rua da Serra',
            numero='100',
            bairro='Centro',
            cidade='Tianguá',
            estado='CE',
            aceite_termos=True,
            data_aceite_termos=timezone.now(),
            registro_ip='127.0.0.1',
            registro_user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        )

        self.assertEqual(perfil.user.username, '123.456.789-00')
        self.assertEqual(perfil.cpf, '123.456.789-00')
        self.assertEqual(perfil.telefone, '(88) 99999-9999')
        self.assertTrue(perfil.aceite_termos)
        self.assertEqual(perfil.registro_ip, '127.0.0.1')
        self.assertIn('Mozilla', perfil.registro_user_agent)
        self.assertEqual(str(perfil), 'João Silva (CPF: 123.456.789-00)')


class ClientesAuthViewsTest(TestCase):
    databases = {'default', 'hospedagem'}
    """
    Test suite for the AJAX authentication views and endpoints.
    Checks dynamic registration, logins, validation, and session lifecycles.
    """

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('clientes:api_registrar')
        self.login_url = reverse('clientes:api_login')
        self.dashboard_url = reverse('clientes:painel')
        self.login_page_url = reverse('clientes:login_cadastro')

        # Dummy data for testing registration
        self.valid_payload = {
            'nome_completo': 'Maria Oliveira',
            'cpf': '987.654.321-11',
            'email': 'maria@navievibe.com',
            'telefone': '(88) 98888-8888',
            'cep': '62320-000',
            'endereco': 'Av. de Fátima',
            'numero': '450',
            'bairro': 'Planalto',
            'cidade': 'Tianguá',
            'estado': 'CE',
            'password': 'strongpassword456',
            'aceite_termos': True
        }

    def test_login_cadastro_page_renders(self):
        """
        Verify that the login and registration page is rendering with status 200.
        """
        response = self.client.get(self.login_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'clientes/login_cadastro.html')

    def test_api_registrar_success(self):
        """
        Test that registration succeeds when sending valid payload, creating both
        the Django Auth User and the ClientePerfil with correct audit trail fields.
        """
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_payload),
            content_type='application/json',
            HTTP_USER_AGENT='TestAgent/1.0',
            REMOTE_ADDR='192.168.1.50'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['redirect_url'], '/clientes/painel/')

        # Assert database updates
        user_exists = User.objects.filter(username='987.654.321-11').exists()
        self.assertTrue(user_exists)

        user = User.objects.get(username='987.654.321-11')
        self.assertEqual(user.first_name, 'Maria')
        self.assertEqual(user.last_name, 'Oliveira')
        self.assertEqual(user.email, 'maria@navievibe.com')

        perfil = ClientePerfil.objects.get(user=user)
        self.assertEqual(perfil.cpf, '987.654.321-11')
        self.assertEqual(perfil.telefone, '(88) 98888-8888')
        self.assertEqual(perfil.registro_ip, '192.168.1.50')
        self.assertEqual(perfil.registro_user_agent, 'TestAgent/1.0')
        self.assertTrue(perfil.aceite_termos)
        self.assertIsNotNone(perfil.data_aceite_termos)

    def test_api_registrar_missing_fields(self):
        """
        Verify that the registration endpoint fails with 400 Bad Request if mandatory fields are missing.
        """
        incomplete_payload = self.valid_payload.copy()
        del incomplete_payload['email']  # Remove email

        response = self.client.post(
            self.register_url,
            data=json.dumps(incomplete_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('O campo email é obrigatório', data['erro'])

    def test_api_registrar_without_terms(self):
        """
        Verify that the registration fails if the user does not accept the Terms of Use.
        """
        no_terms_payload = self.valid_payload.copy()
        no_terms_payload['aceite_termos'] = False

        response = self.client.post(
            self.register_url,
            data=json.dumps(no_terms_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['erro'], 'Você deve aceitar os Termos de Uso.')

    def test_api_registrar_duplicate_cpf(self):
        """
        Verify that registering with a duplicate CPF returns an error.
        """
        # First register
        self.client.post(
            self.register_url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # Try to register again with same payload (CPF) but different email
        duplicate_payload = self.valid_payload.copy()
        duplicate_payload['email'] = 'other_email@navievibe.com'

        response = self.client.post(
            self.register_url,
            data=json.dumps(duplicate_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['erro'], 'Já existe um cadastro com este CPF.')

    def test_api_login_success(self):
        """
        Verify that a registered user can log in successfully via the AJAX endpoint.
        """
        # First register the user
        self.client.post(
            self.register_url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.client.logout()  # Log out to test login specifically

        # Attempt login
        login_payload = {
            'username': '987.654.321-11',
            'password': 'strongpassword456'
        }

        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['redirect_url'], '/clientes/painel/')

    def test_api_login_failure(self):
        """
        Verify that incorrect credentials result in an authentication failure.
        """
        login_payload = {
            'username': '987.654.321-11',
            'password': 'wrongpassword'
        }

        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['erro'], 'CPF ou senha incorretos.')


class ClientesDashboardViewTest(TestCase):
    databases = {'default', 'hospedagem'}
    """
    Test suite for the customer cockpit (Dashboard/Painel).
    Verifies access permissions, stays loading, and mock vertical data integration.
    """

    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('clientes:painel')
        
        # Create standard user
        self.user = User.objects.create_user(
            username='999.999.999-99',
            email='dashboard@navievibe.com',
            password='securepassword789',
            first_name='Carlos',
            last_name='Silva'
        )
        
        # Create associated profile
        self.perfil = ClientePerfil.objects.create(
            user=self.user,
            cpf='999.999.999-99',
            telefone='(88) 99999-9999',
            cep='62320-000',
            endereco='Rua Principal',
            numero='10',
            bairro='Centro',
            cidade='Tianguá',
            estado='CE',
            aceite_termos=True,
            data_aceite_termos=timezone.now(),
            registro_ip='127.0.0.1',
            registro_user_agent='TestAgent/1.0'
        )

    def test_dashboard_redirects_anonymous(self):
        """
        Verify that accessing the dashboard while logged out redirects to the login page.
        """
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('clientes:login_cadastro'), response.url)

    def test_dashboard_renders_authenticated(self):
        """
        Verify that an authenticated user can view the dashboard and the mock shows/cinema cards are rendered.
        """
        self.client.login(username='999.999.999-99', password='securepassword789')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'clientes/painel.html')
        
        # Check context lists are populated
        self.assertIn('hospedagens', response.context)
        self.assertIn('shows', response.context)
        self.assertIn('cinema', response.context)
        self.assertIn('perfil', response.context)
        
        # Check specific injected mock listings exist in context or HTML page content
        self.assertEqual(len(response.context['shows']), 2)
        self.assertEqual(len(response.context['cinema']), 1)
        self.assertContains(response, 'Ibiapaba Rock Festival 2026')
        self.assertContains(response, 'Batman: O Retorno do Cavaleiro')
        self.assertContains(response, 'Pousada da Serra')
