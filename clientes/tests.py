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


class ClientesSocialFeedAndProfileTest(TestCase):
    databases = {'default', 'hospedagem'}

    def setUp(self):
        self.client = Client()
        
        # Create user 1
        self.user1 = User.objects.create_user(
            username='111.111.111-11',
            email='user1@test.com',
            password='password123',
            first_name='Pedro',
            last_name='Alvares'
        )
        self.profile1 = ClientePerfil.objects.create(
            user=self.user1,
            cpf='111.111.111-11',
            telefone='(88) 91111-1111',
            cep='62320-000',
            endereco='Rua Um',
            numero='10',
            bairro='Centro',
            cidade='Tianguá',
            estado='CE',
            aceite_termos=True,
            data_aceite_termos=timezone.now()
        )

        # Create user 2
        self.user2 = User.objects.create_user(
            username='222.222.222-22',
            email='user2@test.com',
            password='password123',
            first_name='Ana',
            last_name='Silva'
        )
        self.profile2 = ClientePerfil.objects.create(
            user=self.user2,
            cpf='222.222.222-22',
            telefone='(88) 92222-2222',
            cep='62320-000',
            endereco='Rua Dois',
            numero='20',
            bairro='Centro',
            cidade='Tianguá',
            estado='CE',
            aceite_termos=True,
            data_aceite_termos=timezone.now()
        )

        # Create hotel / reservation setup for user 2
        from hoteis.models import Local, Hotel, Quarto, UnidadeQuarto, Reserva
        from datetime import date, timedelta
        
        self.local = Local.objects.create(nome='Serra de Ibiapaba', endereco='Estrada da Confiança', cidade='Tianguá', estado='CE')
        self.hotel = Hotel.objects.create(nome='Pousada Ramilos Tianguá', descricao='Melhor pousada da serra', local=self.local)
        self.quarto = Quarto.objects.create(hotel=self.hotel, nome='Chalé Standard', preco=150.00)
        self.unidade = UnidadeQuarto.objects.create(quarto=self.quarto, identificador='Ch-10')
        self.reserva = Reserva.objects.create(
            usuario=self.user2,
            unidade=self.unidade,
            data_checkin=date.today(),
            data_checkout=date.today() + timedelta(days=2),
            subtotal=300.00,
            valor_total=300.00,
            status='confirmada'
        )

    def test_link_post_to_own_reservation(self):
        """
        Verify that a user can create a post linked to their own reservation,
        and it automatically sets the establishment name.
        """
        from clientes.models import PostMomento
        
        self.client.login(username='222.222.222-22', password='password123')
        
        reserva_payload_id = f"RES-{self.reserva.id.hex}"
        response = self.client.post(reverse('clientes:criar_post'), {
            'reserva_id': reserva_payload_id,
            'texto': 'Hospedagem excelente! Adorei tudo.',
            'avaliacao': 5
        })
        self.assertEqual(response.status_code, 302) # Redirects to painel
        
        post = PostMomento.objects.filter(usuario=self.user2).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.reserva, self.reserva)
        self.assertEqual(post.estabelecimento_nome, 'Pousada Ramilos Tianguá')
        self.assertEqual(post.avaliacao, 5)

    def test_link_post_to_other_user_reservation_fails_silently(self):
        """
        Verify that if a user attempts to link a post to someone else's reservation,
        the post is created but not linked (reserva is None).
        """
        from clientes.models import PostMomento
        
        self.client.login(username='111.111.111-11', password='password123')
        
        reserva_payload_id = f"RES-{self.reserva.id.hex}"
        response = self.client.post(reverse('clientes:criar_post'), {
            'reserva_id': reserva_payload_id,
            'texto': 'Tentando burlar vinculando a outra reserva...',
            'avaliacao': 4
        })
        self.assertEqual(response.status_code, 302)
        
        post = PostMomento.objects.filter(usuario=self.user1).first()
        self.assertIsNotNone(post)
        self.assertIsNone(post.reserva) # Should not be linked!

    def test_like_and_comment_on_posts(self):
        """
        Verify liking and commenting on database posts works correctly.
        """
        from clientes.models import PostMomento, ComentarioMomento
        
        # Create a post
        post = PostMomento.objects.create(
            usuario=self.user2,
            texto='Post inicial',
            avaliacao=5
        )
        
        self.client.login(username='111.111.111-11', password='password123')
        
        # Like
        response = self.client.post(reverse('clientes:like_post', args=[post.id.hex]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text-slate-500', response.content.decode('utf-8')) # HTML check
        self.assertTrue(post.likes.filter(id=self.user1.id).exists())
        
        # Unlike
        response = self.client.post(reverse('clientes:like_post', args=[post.id.hex]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(post.likes.filter(id=self.user1.id).exists())
        
        # Comment
        response = self.client.post(reverse('clientes:comentar_post', args=[post.id.hex]), {
            'texto': 'Comentário legal!'
        })
        self.assertEqual(response.status_code, 302)
        
        comment = ComentarioMomento.objects.filter(post=post).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.usuario, self.user1)
        self.assertEqual(comment.texto, 'Comentário legal!')

    def test_editar_perfil_and_theme(self):
        """
        Verify that posting to profile edit updates user and profile details.
        """
        self.client.login(username='111.111.111-11', password='password123')
        
        response = self.client.post(reverse('clientes:editar_perfil'), {
            'first_name': 'Pedro Novo',
            'last_name': 'Alvares Novo',
            'email': 'pedro.novo@test.com',
            'telefone': '(88) 98888-7777',
            'cep': '62320-001',
            'endereco': 'Rua Nova',
            'numero': '15',
            'bairro': 'Bairro Novo',
            'cidade': 'Ubajara',
            'estado': 'CE'
        })
        self.assertEqual(response.status_code, 302)
        
        # Refresh from DB
        self.user1.refresh_from_db()
        self.profile1.refresh_from_db()
        
        self.assertEqual(self.user1.first_name, 'Pedro Novo')
        self.assertEqual(self.user1.last_name, 'Alvares Novo')
        self.assertEqual(self.user1.email, 'pedro.novo@test.com')
        self.assertEqual(self.profile1.telefone, '(88) 98888-7777')
        self.assertEqual(self.profile1.cep, '62320-001')
        self.assertEqual(self.profile1.endereco, 'Rua Nova')
        self.assertEqual(self.profile1.cidade, 'Ubajara')

