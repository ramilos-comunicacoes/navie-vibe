from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages.storage.base import BaseStorage
from django.utils.datastructures import MultiValueDict
from django.http import QueryDict
from decimal import Decimal
import datetime
import os

from core.models import Empresa
from hoteis.models import Local, Hotel, Quarto, UnidadeQuarto, ParceiroUsuario, Reserva
from financeiro.models import TransacaoFinanceira, AnexoTransacao, get_anexo_upload_path
from financeiro.views import criar_transacao_api

class MockStorage(BaseStorage):
    def _get(self):
        return [], True
    def _store(self, messages, response, *args, **kwargs):
        return []

class FinanceiroTestCase(TestCase):
    databases = '__all__'

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='finance_partner', password='password123')
        
        # 1. Setup global Empresa
        self.empresa = Empresa.objects.create(
            nome_fantasia='Hotel Tiangua Premium',
            razao_social='Hotel Tiangua Premium LTDA',
            cnpj='11.222.333/0001-44',
            categoria='hospedagem',
            endereco='Av. Principal, 500',
            cidade='Tianguá',
            estado='CE',
            cep='62320-000',
            email_contato='tianguapremium@gmail.com',
            telefone_contato='88998888888'
        )
        
        # 2. Setup Local
        self.local = Local.objects.create(
            nome='Serra de Tianguá',
            endereco='Av. Principal, 500',
            cidade='Tianguá',
            estado='CE'
        )
        
        # 3. Setup Hotel
        self.hotel = Hotel.objects.create(
            empresa=self.empresa,
            nome='Pousada Serra Vibe',
            descricao='Pousada premium nas montanhas',
            local=self.local,
            slug='pousada-serra-vibe'
        )
        
        # 4. Setup ParceiroUsuario
        self.parceiro = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role='proprietario',
            ativo=True
        )
        
        # 5. Setup Quarto & UnidadeQuarto
        self.quarto = Quarto.objects.create(
            hotel=self.hotel,
            nome='Chalé Luxo Vista Vale',
            preco=450.00,
            capacidade_pessoas=2
        )
        self.unidade = UnidadeQuarto.objects.create(
            quarto=self.quarto,
            identificador='202',
            ativa=True
        )
        
        # 6. Setup Reserva
        self.reserva = Reserva.objects.create(
            unidade=self.unidade,
            data_checkin=datetime.date.today(),
            data_checkout=datetime.date.today() + datetime.timedelta(days=3),
            valor_total=1350.00,
            status='confirmada',
            quantidade_hospedes=2,
            hospede_nome='Ana Paula Souza'
        )

    def test_transacao_legacy_date_sync(self):
        """Testa se o campo data (legado) é automaticamente preenchido com a data de vencimento no save."""
        vencimento = datetime.date(2026, 6, 15)
        transacao = TransacaoFinanceira.objects.create(
            hotel=self.hotel,
            tipo='despesa',
            categoria='manutencao',
            valor=Decimal('350.75'),
            descricao='Troca de chuveiro elétrico no Quarto 202',
            data_vencimento=vencimento,
            data_pagamento=None
        )
        self.assertEqual(transacao.data, vencimento)

    def test_transacao_codigo_generacao(self):
        """Testa se o código semântico único é gerado corretamente."""
        transacao = TransacaoFinanceira.objects.create(
            hotel=self.hotel,
            tipo='receita',
            categoria='diarias',
            valor=Decimal('1350.00'),
            descricao='Diárias pagas via reserva',
            data_vencimento=datetime.date(2026, 6, 1),
            reserva=self.reserva,
            unidade=self.unidade
        )
        # TX-{hotel_id}-{cat_code}-{reserva_short}-{date}-{rand}
        self.assertIsNotNone(transacao.codigo)
        parts = transacao.codigo.split('-')
        self.assertEqual(parts[0], 'TX')
        self.assertEqual(parts[1], str(self.hotel.id))
        self.assertEqual(parts[2], 'DIA')
        self.assertEqual(parts[3], str(self.reserva.id)[:8].upper())
        self.assertEqual(parts[4], '20260601')
        self.assertEqual(len(parts[5]), 4) # Random code part

    def test_anexo_codigo_generacao_e_upload_path(self):
        """Testa a geração de código para anexo e o caminho do arquivo gerado."""
        transacao = TransacaoFinanceira.objects.create(
            hotel=self.hotel,
            tipo='despesa',
            categoria='energia_agua',
            valor=Decimal('520.40'),
            descricao='Conta de energia Enel',
            data_vencimento=datetime.date(2026, 6, 5)
        )
        
        arquivo_mock = SimpleUploadedFile("comprovante.pdf", b"file_content", content_type="application/pdf")
        anexo = AnexoTransacao.objects.create(
            transacao=transacao,
            arquivo=arquivo_mock
        )
        
        self.assertIsNotNone(anexo.codigo)
        self.assertTrue(anexo.codigo.startswith(f"ANX-{transacao.codigo}-"))
        
        # Test path generator output
        path = get_anexo_upload_path(anexo, "comprovante.pdf")
        # should be like: {empresa_slug}/financeiro/anexos/{ano}/{mes}/{dia}/{transacao_codigo}/comprovante.pdf
        expected_start = "hotel-tiangua-premium/financeiro/anexos/2026/06/05/"
        self.assertTrue(path.startswith(expected_start))
        self.assertTrue(path.endswith(f"/{transacao.codigo}/comprovante.pdf"))

    def test_criar_transacao_api_sucesso(self):
        """Testa se a API de criação de transação processa valores com máscara BRL, arquivos e associações."""
        post_data = {
            'tipo': 'receita',
            'categoria': 'walk_in',
            'valor': 'R$ 2.450,85',
            'descricao': 'Reserva direta de balcão walk-in',
            'data_vencimento': '2026-06-10',
            'data_pagamento': '2026-06-10',
            'unidade': str(self.unidade.id),
            'reserva': str(self.reserva.id),
        }
        
        file1 = SimpleUploadedFile("comprovante1.pdf", b"pdf1", content_type="application/pdf")
        file2 = SimpleUploadedFile("comprovante2.jpg", b"jpg2", content_type="image/jpeg")
        
        request = self.factory.post('/financeiro/criar/')
        request.user = self.user
        
        qdict = QueryDict('', mutable=True)
        for k, v in post_data.items():
            qdict[k] = v
        request._post = qdict
        request._files = MultiValueDict({'arquivos': [file1, file2]})
        
        setattr(request, '_messages', MockStorage(request))
        
        response = criar_transacao_api(request)
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        
        # Verify transaction database record
        transacao = TransacaoFinanceira.objects.get(descricao='Reserva direta de balcão walk-in')
        self.assertEqual(transacao.hotel, self.hotel)
        self.assertEqual(transacao.tipo, 'receita')
        self.assertEqual(transacao.categoria, 'walk_in')
        self.assertEqual(transacao.valor, Decimal('2450.85'))
        self.assertEqual(transacao.data_vencimento, datetime.date(2026, 6, 10))
        self.assertEqual(transacao.data_pagamento, datetime.date(2026, 6, 10))
        self.assertEqual(transacao.unidade, self.unidade)
        self.assertEqual(transacao.reserva, self.reserva)
        self.assertEqual(transacao.criado_por, self.user)
        
        # Verify attached files
        anexos = list(transacao.anexos.all())
        self.assertEqual(len(anexos), 2)
        filenames = [os.path.basename(a.arquivo.name) for a in anexos]
        self.assertIn('comprovante1.pdf', filenames)
        self.assertIn('comprovante2.jpg', filenames)

    def test_criar_transacao_api_htmx(self):
        """Testa se a API responde corretamente com os cabeçalhos de recarregamento do HTMX."""
        post_data = {
            'tipo': 'despesa',
            'categoria': 'salarios',
            'valor': '1200.00',
            'descricao': 'Pagamento faxineira diarista',
            'data_vencimento': '2026-06-02',
        }
        
        request = self.factory.post(
            '/financeiro/criar/',
            data=post_data,
            HTTP_HX_REQUEST='true'
        )
        request.user = self.user
        setattr(request, '_messages', MockStorage(request))
        
        response = criar_transacao_api(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Refresh'], 'true')

    def test_criar_transacao_api_invalid_valor(self):
        """Testa a validação contra valores monetários inválidos ou nulos."""
        post_data = {
            'tipo': 'receita',
            'categoria': 'frigobar',
            'valor': 'R$ -15,00', # Negative invalid value
            'descricao': 'Consumo de frigobar',
            'data_vencimento': '2026-06-02',
        }
        
        request = self.factory.post('/financeiro/criar/', data=post_data)
        request.user = self.user
        setattr(request, '_messages', MockStorage(request))
        
        response = criar_transacao_api(request)
        self.assertEqual(response.status_code, 400)
        
        # Verify no transaction was created
        self.assertFalse(TransacaoFinanceira.objects.filter(descricao='Consumo de frigobar').exists())

    def test_criar_transacao_api_invalid_dates(self):
        """Testa a validação contra formatos de data incorretos."""
        post_data = {
            'tipo': 'despesa',
            'categoria': 'energia_agua',
            'valor': '100.00',
            'descricao': 'Conta de água',
            'data_vencimento': '02/06/2026', # Wrong format (should be YYYY-MM-DD)
        }
        
        request = self.factory.post('/financeiro/criar/', data=post_data)
        request.user = self.user
        setattr(request, '_messages', MockStorage(request))
        
        response = criar_transacao_api(request)
        self.assertEqual(response.status_code, 400)
