import uuid
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserInteraction, CarrinhoStatus, RegistroConsumo
from .analytics import limpar_historico_antigo, obter_perfil_interesses_usuario, registrar_consumo_unificado

class TrackerMiddlewareTestCase(TestCase):
    databases = {'default', 'hospedagem', 'restaurantes'}
    
    def setUp(self):
        self.client = Client()

    def test_tracker_cookie_is_set_on_home(self):
        response = self.client.get('/')
        self.assertIn('navie_tracker_id', response.cookies)
        cookie_val = response.cookies['navie_tracker_id'].value
        self.assertTrue(uuid.UUID(cookie_val))

    def test_tracker_cookie_not_set_on_static(self):
        response = self.client.get('/static/css/output.css')
        self.assertNotIn('navie_tracker_id', response.cookies)


class ActiveDayRetentionTestCase(TestCase):
    databases = {'default', 'hospedagem'}
    
    def setUp(self):
        self.tracker_id = str(uuid.uuid4())
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_limpar_historico_antigo_keeps_only_last_30_active_days(self):
        # Criar interações espalhadas por 35 dias únicos
        base_time = timezone.now()
        
        # Vamos gerar interações para 35 dias retroativos distintos
        for day in range(35):
            date_to_log = base_time - timedelta(days=day)
            
            # Criamos registros forçando a data de criação criada_em
            # Como auto_now_add impede mudar no save direto, podemos atualizar após a criação com update()
            inter = UserInteraction.objects.create(
                tracker_id=self.tracker_id,
                usuario=self.user,
                interaction_type='page_view',
                path=f'/pagina-{day}/',
                time_spent=10
            )
            # Força o update do criado_em no banco de dados para simular histórico
            UserInteraction.objects.filter(id=inter.id).update(criado_em=date_to_log)
            
        # Certifica-se de que temos 35 registros no banco antes da limpeza
        self.assertEqual(UserInteraction.objects.filter(tracker_id=self.tracker_id).count(), 35)
        
        # Executar a limpeza
        limpar_historico_antigo(self.tracker_id, self.user)
        
        # Após a limpeza, deve manter exatamente as interações dos 30 dias mais recentes.
        # Os registros dos dias 30, 31, 32, 33, 34 mais antigos (5 dias) devem ter sido apagados.
        self.assertEqual(UserInteraction.objects.filter(tracker_id=self.tracker_id).count(), 30)
        
        # O registro correspondente ao dia 30 retroativo (index 30, ou seja, 30 dias atrás) deve ser apagado
        cutoff_date = (base_time - timedelta(days=30)).date()
        self.assertFalse(UserInteraction.objects.filter(tracker_id=self.tracker_id, criado_em__date__lt=cutoff_date).exists())


class UserInterestProfilingTestCase(TestCase):
    databases = {'default', 'hospedagem'}
    
    def setUp(self):
        self.tracker_id = str(uuid.uuid4())
        self.user = User.objects.create_user(username='profileuser', password='password')

    def test_obter_perfil_interesses_usuario(self):
        # 1. Criar visualizações
        # Rastreia hospedagem
        UserInteraction.objects.create(
            tracker_id=self.tracker_id,
            usuario=self.user,
            interaction_type='item_detail',
            category='hospedagem',
            item_id='quarto_deluxe',
            parent_id='hotel_ramiros',
            time_spent=120,
            path='/hotel/1/'
        )
        # Rastreia cinema (mais tempo)
        UserInteraction.objects.create(
            tracker_id=self.tracker_id,
            usuario=self.user,
            interaction_type='item_detail',
            category='cinema',
            item_id='filme_interestelar',
            parent_id='cinema_centro',
            time_spent=300,
            path='/cinema/filme/1/'
        )

        # 2. Criar carrinho abandonado
        CarrinhoStatus.objects.create(
            tracker_id=self.tracker_id,
            usuario=self.user,
            category='hospedagem',
            item_id='quarto_deluxe',
            quantidade=1,
            recuperado=False,
            metadata={'checkin': '2026-06-10'}
        )

        # 3. Registrar consumo
        registrar_consumo_unificado(
            usuario=self.user,
            tracker_id=self.tracker_id,
            category='cinema',
            item_id='pipoca_grande',
            nome='Pipoca Grande com Manteiga',
            preco=25.00,
            quantidade=2
        )

        # Buscar perfil consolidado
        perfil = obter_perfil_interesses_usuario(self.tracker_id, self.user)

        # Verificar se as categorias preferidas estão ordenadas por tempo gasto
        # 'cinema' tem 300s, 'hospedagem' tem 120s
        self.assertEqual(perfil['categorias_preferidas'], ['cinema', 'hospedagem'])

        # Verificar se detecta o carrinho abandonado
        self.assertEqual(len(perfil['carrinhos_abandonados']), 1)
        self.assertEqual(perfil['carrinhos_abandonados'][0]['item_id'], 'quarto_deluxe')

        # Verificar histórico de consumo
        self.assertEqual(len(perfil['historico_consumo']), 1)
        self.assertEqual(perfil['historico_consumo'][0]['nome'], 'Pipoca Grande com Manteiga')
        self.assertEqual(perfil['historico_consumo'][0]['quantidade_total'], 2)


class TrackingApiTestCase(TestCase):
    databases = {'default', 'hospedagem'}
    
    def setUp(self):
        self.client = Client()
        self.track_url = reverse('analytics:api_registrar_interacao')
        self.tracker_id = str(uuid.uuid4())
        # Definir cookie de teste no cliente
        self.client.cookies['navie_tracker_id'] = self.tracker_id

    def test_api_registers_valid_interaction(self):
        payload = {
            'url': 'http://localhost/hotel/1/',
            'path': '/hotel/1/',
            'time_spent': 45,
            'interaction_type': 'page_view',
            'category': 'hospedagem',
            'item_id': 'quarto_standard',
            'parent_id': 'hotel_1'
        }
        
        # POST sem CSRF deve funcionar (csrf_exempt)
        response = self.client.post(
            self.track_url,
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        resp_data = response.json()
        self.assertTrue(resp_data['success'])
        
        # Verificar inserção no banco
        self.assertTrue(UserInteraction.objects.filter(
            tracker_id=self.tracker_id,
            category='hospedagem',
            time_spent=45
        ).exists())

    def test_api_ignores_zero_seconds_page_view(self):
        payload = {
            'url': 'http://localhost/',
            'path': '/',
            'time_spent': 0,
            'interaction_type': 'page_view'
        }
        response = self.client.post(
            self.track_url,
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ignored'))
        self.assertFalse(UserInteraction.objects.filter(tracker_id=self.tracker_id).exists())
