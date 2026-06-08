from django.db import models
from django.contrib.auth.models import User
from hoteis.models import Hotel
from datetime import date

class CategoriaProduto(models.Model):
    """Categoria para classificar os produtos do estoque (ex: Limpeza, Alimentício, Frigobar)."""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='categorias_produto')
    nome = models.CharField('Nome', max_length=100)
    icone = models.CharField('Ícone Lucide', max_length=50, default='box', help_text="Nome do ícone Lucide a ser exibido (ex: spray-can, utensils, box).")

    class Meta:
        ordering = ['nome']
        verbose_name = 'Categoria de Produto'
        verbose_name_plural = 'Categorias de Produtos'

    def __str__(self):
        return f"{self.nome} ({self.hotel.nome})"

class Fornecedor(models.Model):
    """Fornecedores de insumos ou produtos para o hotel."""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='fornecedores')
    nome = models.CharField('Razão Social / Nome', max_length=150)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    email = models.EmailField('E-mail', blank=True, null=True)
    cnpj_cpf = models.CharField('CNPJ/CPF', max_length=20, blank=True, null=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'

    def __str__(self):
        return self.nome

class Produto(models.Model):
    """Produtos cadastrados no almoxarifado do hotel."""
    UNIDADES_MEDIDA = [
        ('UN', 'Unidade (UN)'),
        ('KG', 'Quilo (KG)'),
        ('LT', 'Litro (LT)'),
        ('PCT', 'Pacote (PCT)'),
        ('CX', 'Caixa (CX)'),
        ('MT', 'Metro (MT)'),
    ]

    FINALIDADES = [
        ('interno', 'Consumo Interno'),
        ('venda', 'Venda / Frigobar'),
        ('ambos', 'Ambos (Consumo & Venda)'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='produtos')
    categoria = models.ForeignKey(CategoriaProduto, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos')
    nome = models.CharField('Nome do Produto', max_length=150)
    descricao = models.TextField('Descrição', blank=True, null=True)
    imagem = models.ImageField('Foto do Item', upload_to='produtos/', blank=True, null=True)
    codigo_barras = models.CharField('Código de Barras', max_length=50, blank=True, null=True)
    localizacao = models.CharField('Localização / Prateleira', max_length=100, blank=True, null=True, help_text="Ex: Prateleira A, Gaveta 2")
    unidade_medida = models.CharField('Unidade de Medida', max_length=10, choices=UNIDADES_MEDIDA, default='UN')
    finalidade = models.CharField('Finalidade', max_length=10, choices=FINALIDADES, default='interno')
    preco_venda = models.DecimalField('Preço de Venda (R$)', max_digits=10, decimal_places=2, null=True, blank=True, help_text="Preço cobrado ao hóspede se marcado para venda.")
    estoque_atual = models.DecimalField('Estoque Atual', max_digits=10, decimal_places=2, default=0.00)
    estoque_minimo = models.DecimalField('Estoque Mínimo', max_digits=10, decimal_places=2, default=0.00, help_text="Limite mínimo para disparar alerta de reposição.")
    alerta_validade = models.BooleanField('Alerta de Validade', default=True, help_text="Se ativo, monitora a validade dos lotes comprados.")
    ativo = models.BooleanField('Ativo', default=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return f"{self.nome} ({self.get_unidade_medida_display()})"

    @property
    def precisa_reposicao(self):
        """Retorna True se o estoque atual estiver abaixo ou igual ao estoque mínimo (se estoque_minimo > 0)."""
        return self.estoque_minimo > 0 and self.estoque_atual <= self.estoque_minimo

    @property
    def proxima_validade(self):
        """Retorna a validade mais próxima de lotes recebidos ainda em estoque."""
        if not self.alerta_validade:
            return None
        # Busca a menor validade de itens de compra cuja compra esteja recebida e seja maior ou igual a hoje
        item = ItemCompra.objects.filter(
            produto=self, 
            compra__status='recebida', 
            validade__isnull=False
        ).order_by('validade').first()
        return item.validade if item else None

    @property
    def status_validade(self):
        """Retorna 'critico' (<= 7 dias), 'alerta' (<= 30 dias), 'ok' ou None se sem alertas."""
        val = self.proxima_validade
        if not val:
            return None
        dias = (val - date.today()).days
        if dias <= 7:
            return 'critico'
        elif dias <= 30:
            return 'alerta'
        return 'ok'

class Compra(models.Model):
    """Registro de compras e entradas de almoxarifado."""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('recebida', 'Recebida (Entregue no Estoque)'),
        ('cancelada', 'Cancelada'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='compras')
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='compras')
    data_compra = models.DateField('Data de Compra', default=date.today)
    observacao = models.TextField('Observações', blank=True, null=True)
    valor_total = models.DecimalField('Valor Total (R$)', max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField('Status', max_length=15, choices=STATUS_CHOICES, default='pendente')
    pago = models.BooleanField('Pago', default=False)
    recebido = models.BooleanField('Recebido', default=False)
    
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False, related_name='compras_registradas')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_compra', '-criado_em']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f"Compra #{self.id} - {self.fornecedor.nome if self.fornecedor else 'Sem Fornecedor'} ({self.data_compra})"

class DocumentoCompra(models.Model):
    """Documentos e comprovantes associados a uma compra (ex: Notas Fiscais, recibos)."""
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='documentos')
    arquivo = models.FileField('Arquivo', upload_to='compras/documentos/')
    nome = models.CharField('Nome do Arquivo', max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Documento de Compra'
        verbose_name_plural = 'Documentos de Compras'

    def __str__(self):
        return self.nome or f"Doc #{self.id}"

class ItemCompra(models.Model):
    """Itens pertencentes a uma compra."""
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='itens_compra')
    quantidade = models.DecimalField('Quantidade', max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField('Preço Unitário (R$)', max_digits=10, decimal_places=2)
    subtotal = models.DecimalField('Subtotal (R$)', max_digits=10, decimal_places=2)
    validade = models.DateField('Data de Validade', blank=True, null=True)

    class Meta:
        verbose_name = 'Item de Compra'
        verbose_name_plural = 'Itens de Compras'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantidade} {self.produto.unidade_medida} of {self.produto.nome}"

class MovimentoEstoque(models.Model):
    """Histórico de entradas, saídas e ajustes físicos no estoque."""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('ajuste', 'Ajuste de Inventário'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='movimentos_estoque')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentos')
    tipo = models.CharField('Tipo de Movimentação', max_length=10, choices=TIPO_CHOICES)
    quantidade = models.DecimalField('Quantidade', max_digits=10, decimal_places=2, help_text="Quantidade movimentada (sempre positiva).")
    referencia = models.CharField('Referência / Motivo', max_length=255, blank=True, null=True, help_text="Ex: 'Compra #12', 'Consumo do Quarto 101', 'Perda por quebra'.")
    
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False, related_name='movimentos_estoque')
    movimento_origem = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False, related_name='reversoes')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.quantidade} {self.produto.unidade_medida} de {self.produto.nome}"
