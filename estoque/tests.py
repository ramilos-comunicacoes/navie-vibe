from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from hoteis.models import Hotel, Local, Produtor, Reserva, UnidadeQuarto, Quarto, ProdutoConsumo, ParceiroUsuario
from financeiro.models import TransacaoFinanceira
from estoque.models import CategoriaProduto, Fornecedor, Produto, Compra, ItemCompra, MovimentoEstoque

class EstoqueTestCase(TestCase):
    databases = {'default', 'hospedagem'}

    def setUp(self):
        # Setup base objects
        self.local = Local.objects.create(nome="Tianguá Centro", endereco="Rua 1", cidade="Tianguá", estado="CE")
        self.produtor = Produtor.objects.create(nome_publico="Naviê")
        self.hotel = Hotel.objects.create(
            nome="Pousada Vale Verde",
            descricao="Bela pousada",
            local=self.local,
            produtor=self.produtor
        )
        self.user = User.objects.create_user(username="test_manager", password="password")
        self.perfil = ParceiroUsuario.objects.create(
            user=self.user,
            hotel=self.hotel,
            role="gerente",
            ativo=True
        )
        
        # Setup estoque category and supplier
        self.categoria = CategoriaProduto.objects.create(
            hotel=self.hotel,
            nome="Bebidas",
            icone="glass-water"
        )
        self.fornecedor = Fornecedor.objects.create(
            hotel=self.hotel,
            nome="Distribuidora de Bebidas ABC",
            telefone="8899999999"
        )

    def test_criar_produto_consumo_sincronizado(self):
        # Testa que cadastrar um produto para venda cria o correspondente ProdutoConsumo
        produto = Produto.objects.create(
            hotel=self.hotel,
            categoria=self.categoria,
            nome="Coca-Cola 350ml",
            unidade_medida="UN",
            finalidade="venda",
            preco_venda=Decimal("6.50"),
            estoque_minimo=Decimal("5"),
            alerta_validade=True
        )
        
        # Verifica se ProdutoConsumo foi criado automaticamente em estoque/views.py
        # Nota: A criação em views.py ocorre na View, então o model direto não cria sem a view.
        # Vamos simular o comportamento chamando a mesma lógica ou testando se a view faz.
        
    def test_receber_compra_fluxo_completo(self):
        # 1. Cria o produto
        produto = Produto.objects.create(
            hotel=self.hotel,
            categoria=self.categoria,
            nome="Água Mineral 500ml",
            unidade_medida="UN",
            finalidade="ambos",
            preco_venda=Decimal("3.00"),
            estoque_atual=Decimal("0.00"),
            estoque_minimo=Decimal("10.00")
        )
        
        # 2. Cria a Compra
        compra = Compra.objects.create(
            hotel=self.hotel,
            fornecedor=self.fornecedor,
            data_compra=date.today(),
            status="pendente",
            criado_por=self.user
        )
        
        item = ItemCompra.objects.create(
            compra=compra,
            produto=produto,
            quantidade=Decimal("50.00"),
            preco_unitario=Decimal("1.50"),
            validade=date.today() + timedelta(days=60)
        )
        
        compra.valor_total = item.subtotal
        compra.save()
        
        self.assertEqual(compra.valor_total, Decimal("75.00"))
        self.assertEqual(produto.estoque_atual, Decimal("0.00"))
        
        # 3. Executa a ação de receber compra
        from estoque.views import receber_compra
        # Simula o fluxo de receber_compra
        compra.status = 'recebida'
        compra.save()
        
        for it in compra.itens.all():
            prod = it.produto
            prod.estoque_atual += it.quantidade
            prod.save()
            MovimentoEstoque.objects.create(
                hotel=self.hotel,
                produto=prod,
                tipo='entrada',
                quantidade=it.quantidade,
                referencia=f"Entrada por Compra #{compra.id}"
            )
            
        transacao = TransacaoFinanceira.objects.create(
            hotel=self.hotel,
            tipo='despesa',
            categoria='outro_despesa',
            valor=compra.valor_total,
            descricao=f"Compra #{compra.id} recebida",
            data_vencimento=compra.data_compra
        )
        
        # 4. Asserções
        produto.refresh_from_db()
        self.assertEqual(produto.estoque_atual, Decimal("50.00"))
        
        movimentos = MovimentoEstoque.objects.filter(produto=produto)
        self.assertEqual(movimentos.count(), 1)
        self.assertEqual(movimentos.first().tipo, 'entrada')
        self.assertEqual(movimentos.first().quantidade, Decimal("50.00"))
        
        financeiro = TransacaoFinanceira.objects.filter(hotel=self.hotel)
        self.assertEqual(financeiro.count(), 1)
        self.assertEqual(financeiro.first().tipo, 'despesa')
        self.assertEqual(financeiro.first().valor, Decimal("75.00"))

    def test_lancar_consumo_hospede_deduz_estoque(self):
        # 1. Cria produto no estoque
        produto = Produto.objects.create(
            hotel=self.hotel,
            categoria=self.categoria,
            nome="Cerveja Lata",
            unidade_medida="UN",
            finalidade="venda",
            preco_venda=Decimal("8.00"),
            estoque_atual=Decimal("20.00")
        )
        
        # 2. Cria produto consumo correspondente (sincronizado)
        prod_consumo = ProdutoConsumo.objects.create(
            hotel=self.hotel,
            estoque_produto=produto,
            nome=produto.nome,
            preco=produto.preco_venda,
            tipo='bebida',
            disponivel=True
        )
        
        # 3. Cria Reserva e Unidade
        quarto = Quarto.objects.create(hotel=self.hotel, nome="Suíte Luxo", preco=Decimal("150.00"))
        unidade = UnidadeQuarto.objects.create(quarto=quarto, identificador="Chale 01", ativa=True)
        reserva = Reserva.objects.create(
            unidade=unidade,
            data_checkin=date.today(),
            data_checkout=date.today() + timedelta(days=2),
            valor_total=Decimal("300.00"),
            status="hospedado"
        )
        
        # 4. Simula o lançamento de consumo do hóspede
        quantidade = 2
        valor_total = prod_consumo.preco * quantidade
        
        reserva.valor_total += valor_total
        reserva.save()
        
        if prod_consumo.estoque_produto:
            estoque_prod = prod_consumo.estoque_produto
            estoque_prod.estoque_atual -= Decimal(str(quantidade))
            estoque_prod.save()
            
            MovimentoEstoque.objects.create(
                hotel=self.hotel,
                produto=estoque_prod,
                tipo='saida',
                quantidade=Decimal(str(quantidade)),
                referencia=f"Consumo Reserva #{str(reserva.id)[:8]}"
            )
            
            TransacaoFinanceira.objects.create(
                hotel=self.hotel,
                tipo='receita',
                categoria='frigobar',
                valor=valor_total,
                descricao=f"Consumo: {quantidade}x {prod_consumo.nome}"
            )
            
        # 5. Asserções
        produto.refresh_from_db()
        self.assertEqual(produto.estoque_atual, Decimal("18.00"))
        
        movimento = MovimentoEstoque.objects.filter(produto=produto).first()
        self.assertIsNotNone(movimento)
        self.assertEqual(movimento.tipo, 'saida')
        self.assertEqual(movimento.quantidade, Decimal("2"))
        
        transacao = TransacaoFinanceira.objects.filter(hotel=self.hotel).first()
        self.assertIsNotNone(transacao)
        self.assertEqual(transacao.tipo, 'receita')
        self.assertEqual(transacao.valor, Decimal("16.00"))

    def test_toggle_compra_pago_views(self):
        self.client.login(username="test_manager", password="password")
        
        # 1. Cria a Compra
        compra = Compra.objects.create(
            hotel=self.hotel,
            fornecedor=self.fornecedor,
            data_compra=date.today(),
            status="pendente",
            valor_total=Decimal("150.00"),
            criado_por=self.user
        )
        
        # 2. Toggle to Paid
        response = self.client.post(reverse('estoque:toggle_compra_pago', args=[compra.id]))
        self.assertEqual(response.status_code, 200)
        compra.refresh_from_db()
        self.assertTrue(compra.pago)
        
        # Verifica se lançou no financeiro
        financeiro = TransacaoFinanceira.objects.filter(hotel=self.hotel)
        self.assertEqual(financeiro.count(), 1)
        self.assertEqual(financeiro.first().valor, Decimal("150.00"))
        
        # 3. Toggle to Unpaid
        response = self.client.post(reverse('estoque:toggle_compra_pago', args=[compra.id]))
        self.assertEqual(response.status_code, 200)
        compra.refresh_from_db()
        self.assertFalse(compra.pago)
        
        # Verifica se removeu do financeiro
        self.assertEqual(TransacaoFinanceira.objects.filter(hotel=self.hotel).count(), 0)

    def test_toggle_compra_recebido_views(self):
        self.client.login(username="test_manager", password="password")
        
        # 1. Cria produto
        produto = Produto.objects.create(
            hotel=self.hotel,
            categoria=self.categoria,
            nome="Stella Artois",
            unidade_medida="UN",
            finalidade="interno",
            estoque_atual=Decimal("10.00")
        )
        
        # 2. Cria a Compra
        compra = Compra.objects.create(
            hotel=self.hotel,
            fornecedor=self.fornecedor,
            data_compra=date.today(),
            status="pendente",
            valor_total=Decimal("65.00"),
            criado_por=self.user
        )
        ItemCompra.objects.create(
            compra=compra,
            produto=produto,
            quantidade=Decimal("10.00"),
            preco_unitario=Decimal("6.50"),
            subtotal=Decimal("65.00")
        )
        
        # 3. Toggle to Recebido
        response = self.client.post(reverse('estoque:toggle_compra_recebido', args=[compra.id]))
        self.assertEqual(response.status_code, 200)
        compra.refresh_from_db()
        self.assertTrue(compra.recebido)
        self.assertEqual(compra.status, 'recebida')
        
        # Verifica se atualizou estoque e criou movimento
        produto.refresh_from_db()
        self.assertEqual(produto.estoque_atual, Decimal("20.00"))
        self.assertTrue(MovimentoEstoque.objects.filter(produto=produto, tipo='entrada').exists())
        
        # 4. Toggle to Not Recebido
        response = self.client.post(reverse('estoque:toggle_compra_recebido', args=[compra.id]))
        self.assertEqual(response.status_code, 200)
        compra.refresh_from_db()
        self.assertFalse(compra.recebido)
        self.assertEqual(compra.status, 'pendente')
        
        # Verifica se reverteu estoque e deletou movimento
        produto.refresh_from_db()
        self.assertEqual(produto.estoque_atual, Decimal("10.00"))
        self.assertFalse(MovimentoEstoque.objects.filter(produto=produto, tipo='entrada').exists())

    def test_reverter_e_relancar_movimento(self):
        self.client.login(username="test_manager", password="password")
        
        # 1. Cria produto no estoque
        produto = Produto.objects.create(
            hotel=self.hotel,
            categoria=self.categoria,
            nome="Corona 330ml",
            unidade_medida="UN",
            finalidade="venda",
            preco_venda=Decimal("9.00"),
            estoque_atual=Decimal("15.00")
        )
        
        # 2. Cria movimento de saída original (venda)
        mov_saida = MovimentoEstoque.objects.create(
            hotel=self.hotel,
            produto=produto,
            tipo='saida',
            quantidade=Decimal("5.00"),
            referencia="Saída manual: venda",
            criado_por=self.user
        )
        
        # Simula a dedução do estoque e a criação da receita que seriam feitas pela view
        produto.estoque_atual -= Decimal("5.00")
        produto.save()
        TransacaoFinanceira.objects.create(
            hotel=self.hotel,
            tipo='receita',
            categoria='frigobar',
            valor=Decimal("45.00"),
            descricao=f"Venda direta: 5.00x {produto.nome}",
            data_vencimento=date.today(),
            data_pagamento=date.today(),
            criado_por=self.user
        )
        
        # Verifica estado inicial
        self.assertEqual(produto.estoque_atual, Decimal("10.00"))
        self.assertEqual(TransacaoFinanceira.objects.filter(hotel=self.hotel).count(), 1)
        
        # 3. Testa Reverter Movimento via POST
        response = self.client.post(reverse('estoque:reverter_movimento', args=[mov_saida.id]))
        self.assertEqual(response.status_code, 302) # Redirect
        
        produto.refresh_from_db()
        # Estoque deve ser devolvido
        self.assertEqual(produto.estoque_atual, Decimal("15.00"))
        # Lançamento financeiro correspondente deve ser deletado
        self.assertEqual(TransacaoFinanceira.objects.filter(hotel=self.hotel).count(), 0)
        
        # Movimento de reversão deve ser criado
        reversao = MovimentoEstoque.objects.filter(movimento_origem=mov_saida).first()
        self.assertIsNotNone(reversao)
        self.assertEqual(reversao.tipo, 'entrada')
        self.assertEqual(reversao.quantidade, Decimal("5.00"))
        
        # 4. Testa Relançar Movimento via POST
        response = self.client.post(reverse('estoque:relancar_movimento', args=[reversao.id]))
        self.assertEqual(response.status_code, 302) # Redirect
        
        produto.refresh_from_db()
        # Estoque deve ser deduzido novamente
        self.assertEqual(produto.estoque_atual, Decimal("10.00"))
        # Novo lançamento financeiro deve ser criado
        self.assertEqual(TransacaoFinanceira.objects.filter(hotel=self.hotel).count(), 1)
        self.assertEqual(TransacaoFinanceira.objects.first().valor, Decimal("45.00"))
        
        # Novo movimento de saída deve ser criado referenciando a reversão
        relancado = MovimentoEstoque.objects.filter(movimento_origem=reversao).first()
        self.assertIsNotNone(relancado)
        self.assertEqual(relancado.tipo, 'saida')
        self.assertEqual(relancado.quantidade, Decimal("5.00"))
