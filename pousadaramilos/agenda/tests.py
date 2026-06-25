from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from sistema.models import Pousada, Usuario
from agenda.models import Atividade

class AtividadeTestCase(TestCase):
    def setUp(self):
        # Criar duas pousadas para testar isolamento de dados
        self.pousada_a = Pousada.objects.create(
            nome="Pousada A",
            endereco="Endereço A",
            telefone_whatsapp="111111111"
        )
        self.pousada_b = Pousada.objects.create(
            nome="Pousada B",
            endereco="Endereço B",
            telefone_whatsapp="222222222"
        )
        
        # Criar usuário Direção vinculado à pousada A
        self.user_direcao = Usuario.objects.create_user(
            username="diretor",
            password="password123",
            role="DIRECAO",
            pousada_vinculada=self.pousada_a
        )
        
        # Criar usuário Portaria vinculado à pousada B
        self.user_portaria_b = Usuario.objects.create_user(
            username="portariab",
            password="password123",
            role="PORTARIA",
            pousada_vinculada=self.pousada_b
        )
        
        # Criar usuário Serviço vinculado à pousada A
        self.user_servico = Usuario.objects.create_user(
            username="servico",
            password="password123",
            role="SERVICO",
            pousada_vinculada=self.pousada_a
        )
        
        # Atividade na Pousada A
        self.atividade_a = Atividade.objects.create(
            titulo="Limpar piscina A",
            status="todo",
            prioridade="alta",
            usuario=self.user_servico,
            pousada=self.pousada_a
        )
        
        # Atividade na Pousada B
        self.atividade_b = Atividade.objects.create(
            titulo="Consertar cerca B",
            status="todo",
            prioridade="normal",
            usuario=self.user_portaria_b,
            pousada=self.pousada_b
        )
        
        self.client = Client()

    def test_painel_atividades_requires_login(self):
        response = self.client.get(reverse('agenda:painel_atividades'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_painel_atividades_shows_only_current_pousada_tasks(self):
        # Login com usuário da Pousada A
        self.client.login(username="diretor", password="password123")
        response = self.client.get(reverse('agenda:painel_atividades'))
        self.assertEqual(response.status_code, 200)
        
        # Deve listar a atividade da Pousada A
        self.assertContains(response, "Limpar piscina A")
        # Não deve listar a atividade da Pousada B
        self.assertNotContains(response, "Consertar cerca B")

    def test_create_atividade_via_form_view(self):
        self.client.login(username="diretor", password="password123")
        
        post_data = {
            'titulo': 'Nova tarefa teste',
            'descricao': 'Descrição da tarefa teste',
            'status': 'todo',
            'prioridade': 'normal',
            'usuario': self.user_servico.id,
        }
        
        response = self.client.post(reverse('agenda:nova_tarefa'), post_data)
        self.assertEqual(response.status_code, 200) # HTMX success code/empty response with HX-Trigger
        self.assertTrue('HX-Trigger' in response)
        
        # Verifica no banco se foi criada
        self.assertTrue(Atividade.objects.filter(titulo='Nova tarefa teste', pousada=self.pousada_a).exists())

    def test_mudar_status_via_drag_and_drop(self):
        self.client.login(username="diretor", password="password123")
        
        # Muda status de 'todo' para 'doing'
        self.assertEqual(self.atividade_a.status, 'todo')
        response = self.client.post(
            reverse('agenda:mudar_status', kwargs={'pk': self.atividade_a.id}),
            {'status': 'doing'},
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        self.atividade_a.refresh_from_db()
        self.assertEqual(self.atividade_a.status, 'doing')

    def test_is_atrasada_property(self):
        # Data de vencimento no passado
        self.atividade_a.data_vencimento = timezone.now() - timedelta(hours=2)
        self.atividade_a.status = 'todo'
        self.atividade_a.save()
        self.assertTrue(self.atividade_a.is_atrasada)
        
        # Se estiver concluída, mesmo no passado, não deve constar como atrasada
        self.atividade_a.status = 'done'
        self.atividade_a.save()
        self.assertFalse(self.atividade_a.is_atrasada)

    def test_deletar_atividade(self):
        self.client.login(username="diretor", password="password123")
        
        atividade_id = self.atividade_a.id
        self.assertTrue(Atividade.objects.filter(id=atividade_id).exists())
        
        response = self.client.post(reverse('agenda:deletar_tarefa', kwargs={'pk': self.atividade_a.id}))
        self.assertEqual(response.status_code, 200)
        
        self.assertFalse(Atividade.objects.filter(id=atividade_id).exists())
