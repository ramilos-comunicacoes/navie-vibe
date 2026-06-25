from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from parceiros.models import SolicitacaoEmpresa, StatusSolicitacao, TipoEmpresa
from hoteis.models import Hotel, ParceiroUsuario, Local, ConfigSistema, HotelTarifaFaixa, HotelDocumento, HotelTermoAdesao, HotelAuditLog
from core.models import Empresa


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

    def test_hotel_salvar_configuracao_admin_anonymous(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test", cidade="Tianguá", estado="CE")
        # Setup Hotel
        hotel = Hotel.objects.create(nome="Pousada Anon", local=local, slug="pousadaanon")
        save_url = reverse('administracao:hotel_salvar_configuracao_admin', kwargs={'pk': hotel.pk})
        
        response = self.client.post(save_url, {
            'slug': 'pousadaconta',
            'taxa_fixa_navie': '10.00',
            'taxa_percentual_navie': '5.00',
            'limite_trafego_gb': '150',
            'consumo_trafego_gb': '5.50',
            'status': 'ativo'
        })
        # Anonymous user should be redirected
        login_url = reverse('administracao:login')
        self.assertRedirects(response, f"{login_url}?next={save_url}")
        
        # Verify hotel was not updated
        hotel.refresh_from_db()
        self.assertEqual(hotel.slug, "pousadaanon")

    def test_hotel_salvar_configuracao_admin_normal_user(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test 2", cidade="Tianguá", estado="CE")
        # Setup Hotel
        hotel = Hotel.objects.create(nome="Pousada Normal", local=local, slug="pousadanormal")
        save_url = reverse('administracao:hotel_salvar_configuracao_admin', kwargs={'pk': hotel.pk})
        
        # Login normal user
        self.client.login(username='client_test', password='testpassword')
        response = self.client.post(save_url, {
            'slug': 'pousadanormalchanged',
            'taxa_fixa_navie': '10.00',
            'taxa_percentual_navie': '5.00',
            'limite_trafego_gb': '150',
            'consumo_trafego_gb': '5.50',
            'status': 'ativo'
        })
        login_url = reverse('administracao:login')
        self.assertRedirects(response, f"{login_url}?next={save_url}")
        
        # Verify hotel was not updated
        hotel.refresh_from_db()
        self.assertEqual(hotel.slug, "pousadanormal")

    def test_hotel_salvar_configuracao_admin_superuser(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test 3", cidade="Tianguá", estado="CE")
        # Setup Hotel
        hotel = Hotel.objects.create(
            nome="Pousada Admin", 
            local=local, 
            slug="pousadaadmin",
            taxa_fixa_navie=15.00,
            taxa_percentual_navie=10.00,
            limite_trafego_gb=100,
            consumo_trafego_gb=14.20
        )
        save_url = reverse('administracao:hotel_salvar_configuracao_admin', kwargs={'pk': hotel.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.post(save_url, {
            'slug': 'pousadaadminchanged',
            'taxa_fixa_navie': '12.50',
            'taxa_percentual_navie': '8.50',
            'limite_trafego_gb': '200',
            'consumo_trafego_gb': '25.30',
            'status': 'ativo',
            'venda_online': 'on'
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify hotel was updated
        hotel.refresh_from_db()
        self.assertEqual(hotel.slug, "pousadaadminchanged")
        self.assertEqual(float(hotel.taxa_fixa_navie), 12.50)
        self.assertEqual(float(hotel.taxa_percentual_navie), 8.50)
        self.assertEqual(hotel.limite_trafego_gb, 200)
        self.assertEqual(float(hotel.consumo_trafego_gb), 25.30)
        self.assertTrue(hotel.venda_online)
        self.assertEqual(hotel.status, 'ativo')

    def test_hotel_salvar_configuracao_admin_duplicate_slug(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test 4", cidade="Tianguá", estado="CE")
        # Setup Hotel 1 & 2
        hotel1 = Hotel.objects.create(nome="Pousada Um", local=local, slug="pousadaum")
        hotel2 = Hotel.objects.create(nome="Pousada Dois", local=local, slug="pousadadois")
        
        save_url = reverse('administracao:hotel_salvar_configuracao_admin', kwargs={'pk': hotel2.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        # Try to change hotel2's slug to 'pousadaum'
        response = self.client.post(save_url, {
            'slug': 'pousadaum',
            'taxa_fixa_navie': '10.00',
            'taxa_percentual_navie': '5.00',
            'limite_trafego_gb': '150',
            'consumo_trafego_gb': '5.50',
            'status': 'ativo'
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify hotel2 slug was not updated
        hotel2.refresh_from_db()
        self.assertEqual(hotel2.slug, "pousadadois")

    def test_hotel_documento_adicionar_superuser(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test Doc", cidade="Tianguá", estado="CE")
        hotel = Hotel.objects.create(nome="Hotel Doc", local=local, slug="hoteldoc")
        add_doc_url = reverse('administracao:hotel_documento_adicionar', kwargs={'pk': hotel.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        
        # Create a mock file
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("contract.pdf", b"file_content", content_type="application/pdf")
        
        response = self.client.post(add_doc_url, {
            'nome': 'Contrato Oficial',
            'arquivo': mock_file
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify document was created
        self.assertEqual(HotelDocumento.objects.filter(hotel=hotel, nome='Contrato Oficial').count(), 1)
        doc = HotelDocumento.objects.get(hotel=hotel, nome='Contrato Oficial')
        self.assertTrue(doc.arquivo.name.startswith('hoteis/documentos/contract'))
        
        # Verify audit log was created
        log = HotelAuditLog.objects.get(hotel=hotel, campo_alterado='documento')
        self.assertIn('Contrato Oficial', log.valor_novo)
        
        # Clean up files uploaded during test
        doc.arquivo.delete(save=False)

    def test_hotel_documento_excluir_superuser(self):
        # Setup Local
        local = Local.objects.create(nome="Tiangua Test Doc 2", cidade="Tianguá", estado="CE")
        hotel = Hotel.objects.create(nome="Hotel Doc 2", local=local, slug="hoteldoc2")
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("contract2.pdf", b"file_content", content_type="application/pdf")
        doc = HotelDocumento.objects.create(hotel=hotel, nome='Contrato 2', arquivo=mock_file)
        
        excluir_url = reverse('administracao:hotel_documento_excluir', kwargs={'doc_pk': doc.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.post(excluir_url)
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify document was deleted
        self.assertEqual(HotelDocumento.objects.filter(pk=doc.pk).count(), 0)
        
        # Verify audit log was created
        log = HotelAuditLog.objects.get(hotel=hotel, campo_alterado='documento', valor_novo='Removido')
        self.assertEqual(log.valor_antigo, 'Documento existente: Contrato 2')

    def test_hotel_termo_registrar_superuser(self):
        local = Local.objects.create(nome="Tiangua Test Termo", cidade="Tianguá", estado="CE")
        hotel = Hotel.objects.create(nome="Hotel Termo", local=local, slug="hoteltermo")
        termo_url = reverse('administracao:hotel_termo_registrar', kwargs={'pk': hotel.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.post(termo_url, {
            'versao_termo': '2.1'
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify termo is logged
        self.assertEqual(HotelTermoAdesao.objects.filter(hotel=hotel, versao_termo='2.1').count(), 1)
        termo = HotelTermoAdesao.objects.get(hotel=hotel, versao_termo='2.1')
        self.assertEqual(termo.usuario, self.superuser)
        
        # Verify audit log
        log = HotelAuditLog.objects.get(hotel=hotel, campo_alterado='termo_adesao')
        self.assertIn('2.1', log.valor_novo)

    def test_hotel_tarifas_faixa_salvar_superuser(self):
        local = Local.objects.create(nome="Tiangua Test Faixa", cidade="Tianguá", estado="CE")
        hotel = Hotel.objects.create(nome="Hotel Faixa", local=local, slug="hotelfaixa")
        faixa_url = reverse('administracao:hotel_tarifas_faixa_salvar', kwargs={'pk': hotel.pk})
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.post(faixa_url, {
            'valor_minimo': '100.00',
            'valor_maximo': '200.00',
            'taxa_fixa': '15.00',
            'taxa_percentual': '5.00'
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify faixa was created
        self.assertEqual(HotelTarifaFaixa.objects.filter(hotel=hotel, valor_minimo=100.00).count(), 1)
        faixa = HotelTarifaFaixa.objects.get(hotel=hotel, valor_minimo=100.00)
        self.assertEqual(float(faixa.valor_maximo), 200.00)
        self.assertEqual(float(faixa.taxa_fixa), 15.00)
        self.assertEqual(float(faixa.taxa_percentual), 5.00)
        
        # Verify audit log
        log = HotelAuditLog.objects.get(hotel=hotel, campo_alterado='tarifa_faixa')
        self.assertIn('100.00 a R$ 200.00', log.valor_novo)

    def test_salvar_configuracao_sistema(self):
        config_url = reverse('administracao:salvar_configuracao_sistema')
        
        # Login superuser
        self.client.login(username='admin_test', password='testpassword')
        response = self.client.post(config_url, {
            'taxa_fixa_padrao': '18.00',
            'taxa_percentual_padrao': '12.00',
            'limite_trafego_padrao': '250'
        })
        self.assertRedirects(response, reverse('administracao:hoteis_list'))
        
        # Verify ConfigSistema was updated
        config = ConfigSistema.objects.first()
        self.assertIsNotNone(config)
        self.assertEqual(float(config.taxa_fixa_padrao), 18.00)
        self.assertEqual(float(config.taxa_percentual_padrao), 12.00)
        self.assertEqual(config.limite_trafego_padrao, 250)


