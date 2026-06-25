import unicodedata
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings

# ==============================================================================
# 1. ENTIDADE: POUSADA (Tenant)
# Representa cada uma das propriedades físicas gerenciadas no sistema.
# ==============================================================================
class Pousada(models.Model):
    """
    Representa uma das unidades de pousada da rede Pousada Ramiros.
    Todas as reservas, quartos e transações estão vinculados a uma Pousada específica.
    """
    nome = models.CharField(
        max_length=150, 
        verbose_name="Nome da Pousada",
        help_text="Ex: Pousada Ramiros Centro, Pousada Ramiros Praia"
    )
    endereco = models.CharField(
        max_length=255, 
        verbose_name="Endereço Completo"
    )
    telefone_whatsapp = models.CharField(
        max_length=20, 
        verbose_name="WhatsApp de Contato",
        help_text="Telefone da pousada que receberá as mensagens de reserva do site"
    )
    cnpj = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="CNPJ da Unidade"
    )
    cor_primaria_hex = models.CharField(
        max_length=7, 
        default="#2563eb", 
        verbose_name="Cor Primária (Hexadecimal)",
        help_text="Código hexadecimal da cor de marca (ex: #2563eb). Alimenta o YIQ contrast no front-end."
    )
    mapa_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Latitude",
        help_text="Coordenada geográfica de latitude do mapa"
    )
    mapa_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Longitude",
        help_text="Coordenada geográfica de longitude do mapa"
    )
    ativo = models.BooleanField(
        default=True, 
        verbose_name="Unidade Ativa"
    )
    imagem_destaque = models.ImageField(
        upload_to='pousadas/',
        blank=True,
        null=True,
        verbose_name="Imagem de Destaque",
        help_text="Imagem da pousada exibida no carrossel do site público."
    )

    class Meta:
        verbose_name = "Pousada"
        verbose_name_plural = "Pousadas"
        ordering = ['nome']

    def __str__(self):
        return self.nome


# ==============================================================================
# 2. ENTIDADE: USUÁRIO CUSTOMIZADO (RBAC)
# Gerencia as permissões de acesso baseadas em cargos e vínculos de pousada.
# ==============================================================================
class Usuario(AbstractUser):
    """
    Custom User Model que estende o Django auth.User para implementar controle de acesso
    baseado em cargos (Role-Based Access Control) e vinculação territorial com pousadas.
    """
    ROLE_CHOICES = [
        ('DIRECAO', 'Direção'),
        ('PORTARIA', 'Portaria / Recepção'),
        ('SERVICO', 'Manutenção / Camareiraria'),
    ]

    nome_completo = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Nome Completo"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='PORTARIA', 
        verbose_name="Cargo / Função"
    )
    pousada_vinculada = models.ForeignKey(
        Pousada, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="funcionarios",
        verbose_name="Pousada de Atuação",
        help_text="Unidade à qual este funcionário está alocado. Administradores globais podem deixar este campo vazio."
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        nome = self.nome_completo if self.nome_completo else self.username
        return f"{nome} ({self.get_role_display()})"

    @property
    def is_direcao(self):
        return self.role == 'DIRECAO' or self.is_superuser

    @property
    def is_portaria(self):
        return self.role == 'PORTARIA'

    @property
    def is_servico(self):
        return self.role == 'SERVICO'


# ==============================================================================
# 3. ENTIDADE: CATEGORIA DE QUARTO (Modelo/Tipo de Quarto)
# Define as características, tarifas, comodidades e mídias de uma categoria (B2B Naviê)
# ==============================================================================
class CategoriaQuarto(models.Model):
    """
    Representa a Categoria de Acomodação (Ex: Suíte Casal Premium, Chalé Familiar).
    Concentra as tarifas, imagens, tours de vídeo, regras de desconto progressivo
    e metadados otimizados para SEO e IA (Google/Gemini).
    """
    pousada = models.ForeignKey(
        Pousada, 
        on_delete=models.CASCADE, 
        related_name='categorias', 
        verbose_name="Pousada"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Categoria Ativa"
    )
    nome = models.CharField(
        max_length=150, 
        verbose_name="Nome da Acomodação",
        help_text="Ex: Suíte Presidencial, Chalé Duplo"
    )
    slug = models.SlugField(
        max_length=180, 
        blank=True, 
        help_text="URL amigável gerada automaticamente a partir do nome"
    )
    descricao = models.TextField(
        blank=True, 
        verbose_name="Descrição da Acomodação",
        help_text="Texto publicitário exibido ao hóspede no site de vendas"
    )
    preco_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Preço da Diária Padrão"
    )
    
    # Mídias e Tours Virtuais
    video_url = models.CharField(
        max_length=500, 
        blank=True, 
        null=True, 
        verbose_name="URL de Vídeo Externo",
        help_text="Link para vídeo MP4 ou embed (YouTube/Vimeo)"
    )
    video_arquivo = models.FileField(
        upload_to='quartos/videos/', 
        blank=True, 
        null=True, 
        verbose_name="Arquivo de Vídeo Local",
        help_text="Arquivo de vídeo local do tour da acomodação (máx. 30MB)"
    )
    
    # Inteligência de Capacidade
    capacidade_adultos = models.PositiveIntegerField(
        default=2, 
        verbose_name="Capacidade Máxima de Adultos"
    )
    capacidade_criancas = models.PositiveIntegerField(
        default=0, 
        verbose_name="Capacidade Máxima de Crianças"
    )
    tags = models.CharField(
        max_length=255, 
        blank=True, 
        default="", 
        verbose_name="Tags para IA",
        help_text="Categorização para buscas por inteligência artificial (ex: Família, Romântico, Serra)"
    )
    comodidades = models.CharField(
        max_length=255, 
        blank=True, 
        default="", 
        verbose_name="Diferenciais / Comodidades",
        help_text="Diferenciais separados por vírgula (ex: Ar Condicionado, Wi-Fi, Hidromassagem)"
    )
    
    # Regras de Desconto Progressivo Multidias
    tem_desconto_multidias = models.BooleanField(
        default=False, 
        verbose_name="Habilitar Desconto Progressivo"
    )
    dias_minimos_desconto = models.IntegerField(
        default=3, 
        verbose_name="Noites Mínimas para Desconto"
    )
    percentual_desconto = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Percentual de Desconto (ex: 10.00 para 10%)"
    )
    
    # Otimização de SEO e Robôs de IA (Metadados Estruturados)
    seo_titulo = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        verbose_name="Título Otimizado (SEO/IA)"
    )
    seo_descricao = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Descrição Otimizada (SEO/IA)"
    )
    
    class Meta:
        verbose_name = "Categoria de Acomodação"
        verbose_name_plural = "Categorias de Acomodações"
        unique_together = [('pousada', 'slug')]

    @staticmethod
    def _normalizar_slug(texto):
        """Converte caracteres acentuados para ASCII antes de aplicar o slugify do Django."""
        nfkd = unicodedata.normalize('NFKD', texto)
        ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
        return slugify(ascii_str)
    
    def _gerar_slug_unico(self):
        """Gera um slug único por pousada, adicionando um sufixo numérico em caso de colisão."""
        base_slug = self._normalizar_slug(self.nome) or f'acomodacao-{self.id or 0}'
        candidato = base_slug
        num = 2
        while True:
            conflito = CategoriaQuarto.objects.filter(pousada=self.pousada, slug=candidato)
            if self.pk:
                conflito = conflito.exclude(pk=self.pk)
            if not conflito.exists():
                return candidato
            candidato = f'{base_slug}-{num}'
            num += 1
    
    def save(self, *args, **kwargs):
        # Auto-gera slug se alterado ou novo
        if not self.slug or (self.pk and CategoriaQuarto.objects.filter(pk=self.pk).values_list('nome', flat=True).first() != self.nome):
            self.slug = self._gerar_slug_unico()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.nome} ({self.pousada.nome} - R$ {self.preco_base})"


# ==============================================================================
# 4. ENTIDADE: IMAGEM DA CATEGORIA (Galeria Ordenada)
# ==============================================================================
class QuartoImagem(models.Model):
    """
    Galeria de fotos ordenadas vinculadas à categoria de acomodação.
    Suporta até 10 imagens por categoria.
    """
    categoria = models.ForeignKey(
        CategoriaQuarto, 
        on_delete=models.CASCADE, 
        related_name='imagens',
        verbose_name="Categoria"
    )
    url_imagem = models.ImageField(
        upload_to='quartos/galeria/', 
        verbose_name="Arquivo de Imagem"
    )
    ordem = models.IntegerField(
        default=0, 
        verbose_name="Ordem de Exibição"
    )
    
    class Meta:
        ordering = ['ordem']
        verbose_name = "Imagem da Acomodação"
        verbose_name_plural = "Imagens das Acomodações"

    def __str__(self):
        return f"Foto {self.ordem} - {self.categoria.nome}"


# ==============================================================================
# 5. ENTIDADE: QUARTO FÍSICO (Unidade de Quarto)
# A unidade física real (Ex: Quarto 101, Chalé 05) vinculada à Pousada e Categoria.
# ==============================================================================
class Quarto(models.Model):
    """
    Representa o quarto físico real (a unidade de inventário).
    Está integrado com status em tempo real de limpeza e recepção.
    """
    STATUS_CHOICES = [
        ('LIVRE', 'Livre (Pronto para Uso)'),
        ('OCUPADO', 'Ocupado'),
        ('SUJO', 'Sujo (Aguardando Limpeza)'),
        ('MANUTENCAO', 'Em Manutenção Física'),
    ]

    pousada = models.ForeignKey(
        Pousada, 
        on_delete=models.CASCADE, 
        related_name="quartos",
        verbose_name="Pousada"
    )
    categoria = models.ForeignKey(
        CategoriaQuarto, 
        on_delete=models.CASCADE, 
        related_name="quartos",
        verbose_name="Categoria de Acomodação"
    )
    numero = models.CharField(
        max_length=50, 
        verbose_name="Identificador / Número do Quarto",
        help_text="Ex: 101, Chale 02, Deck Presidencial"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='LIVRE', 
        verbose_name="Status Operacional"
    )
    capacidade_maxima = models.PositiveIntegerField(
        default=2,
        verbose_name="Capacidade Máxima",
        help_text="Limite físico rígido de hóspedes neste quarto."
    )

    class Meta:
        verbose_name = "Quarto Físico"
        verbose_name_plural = "Quartos Físicos"
        unique_together = ('pousada', 'numero')
        ordering = ['pousada', 'numero']

    @property
    def identificador(self):
        return self.numero

    def __str__(self):
        return f"{self.numero} ({self.categoria.nome} - {self.pousada.nome})"


# ==============================================================================
# 6. ENTIDADE: CLIENTE / HÓSPEDE
# Base unificada de hóspedes.
# ==============================================================================
class Cliente(models.Model):
    nome = models.CharField(max_length=200, verbose_name="Nome Completo")
    cpf_passaporte = models.CharField(max_length=30, unique=True, verbose_name="CPF ou Passaporte")
    telefone_whatsapp = models.CharField(max_length=25, verbose_name="WhatsApp")
    email = models.EmailField(verbose_name="E-mail")
    data_nascimento = models.DateField(blank=True, null=True, verbose_name="Data de Nascimento")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (CPF: {self.cpf_passaporte})"


# ==============================================================================
# 7. ENTIDADE: RESERVA
# Motor de reservas.
# ==============================================================================
class Reserva(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente de Confirmação / Pagamento'),
        ('CONFIRMADA', 'Reserva Confirmada (Garantida)'),
        ('HOSPEDADO', 'Hospedado (Check-in Realizado)'),
        ('FINALIZADA', 'Finalizada (Check-out Realizado)'),
        ('CANCELADA', 'Reserva Cancelada'),
    ]

    CANAL_CHOICES = [
        ('WEBSITE_WHATSAPP', 'Site Público (Redirecionamento WhatsApp)'),
        ('WEBSITE_DIRETO', 'Site Público (Venda Direta / Pix Online)'),
        ('INTEGRACAO_CHATBOT', 'WhatsApp Chatbot Automático'),
        ('BALCAO', 'Reserva de Balcão (Recepção Interna)'),
    ]

    quarto = models.ForeignKey(
        Quarto, 
        on_delete=models.CASCADE, 
        related_name="reservas",
        verbose_name="Quarto Alocado"
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="reservas",
        verbose_name="Hóspede Responsável"
    )
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reservas_usuario', 
        db_constraint=False
    )
    data_checkin = models.DateField(verbose_name="Data de Entrada (Check-in)")
    hora_checkin = models.TimeField(default="14:00", verbose_name="Horário de Entrada (Check-in)")
    data_checkout = models.DateField(verbose_name="Data de Saída (Check-out)")
    hora_checkout = models.TimeField(default="12:00", verbose_name="Horário de Saída (Check-out)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name="Status da Reserva")
    
    # Valores financeiros
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    taxas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total")
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor Já Pago")
    
    canal_origem = models.CharField(max_length=30, choices=CANAL_CHOICES, default='WEBSITE_WHATSAPP', verbose_name="Canal de Origem")
    
    # Datas de execução reais de portaria
    checkin_realizado_em = models.DateTimeField(null=True, blank=True)
    checkout_realizado_em = models.DateTimeField(null=True, blank=True)
    
    # Ficha de Registro Nacional de Hóspedes (FNRH) histórica do Titular
    hospede_nome = models.CharField(max_length=255, blank=True, null=True)
    hospede_cpf = models.CharField(max_length=20, blank=True, null=True)
    hospede_email = models.EmailField(blank=True, null=True)
    hospede_telefone = models.CharField(max_length=20, blank=True, null=True)
    hospede_rg = models.CharField(max_length=50, blank=True, null=True)
    hospede_nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    hospede_profissao = models.CharField(max_length=100, blank=True, null=True)
    hospede_endereco = models.TextField(blank=True, null=True)
    
    quantidade_hospedes = models.PositiveIntegerField(default=1)
    
    # Split de Taxas Administrativas do Sistema
    taxa_servico_plataforma = models.DecimalField('Taxa de Serviço Plataforma', max_digits=10, decimal_places=2, default=0.00)
    taxa_gateway = models.DecimalField('Taxa Gateway Absorvida', max_digits=10, decimal_places=2, default=0.00)
    repasse_parceiro = models.DecimalField('Repasse Líquido ao Parceiro', max_digits=10, decimal_places=2, default=0.00)
    ganho_liquido_plataforma = models.DecimalField('Ganho Líquido Plataforma', max_digits=10, decimal_places=2, default=0.00)
    
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Registro")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-data_checkin']

    def __str__(self):
        nome_resp = self.hospede_nome if self.hospede_nome else (self.cliente.nome if self.cliente else "N/A")
        return f"Reserva #{self.id} - {nome_resp} (Quarto {self.quarto.numero})"

    @property
    def total_noites(self):
        if self.data_checkout and self.data_checkin:
            return (self.data_checkout - self.data_checkin).days
        return 0



# ==============================================================================
# 8. ENTIDADE: TAREFA DE LIMPEZA / HIGIENIZAÇÃO (Equipe Camareiras)
# ==============================================================================
class TarefaLimpeza(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Aguardando Limpeza'),
        ('EM_ANDAMENTO', 'Em Higienização'),
        ('CONCLUIDA', 'Higienizado e Aprovado'),
    ]

    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name="tarefas_limpeza", verbose_name="Quarto")
    camareira = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas_limpeza", verbose_name="Camareira")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name="Status do Serviço")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Abertura")
    data_conclusao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Conclusão")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Tarefa de Limpeza"
        verbose_name_plural = "Tarefas de Limpeza"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Limpeza {self.quarto.numero} - {self.get_status_display()}"


# ==============================================================================
# 9. ENTIDADE: TAREFA DE MANUTENÇÃO (Equipe Técnica)
# ==============================================================================
class TarefaManutencao(models.Model):
    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANDAMENTO', 'Em Execução'),
        ('RESOLVIDA', 'Resolvido'),
    ]

    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name="tarefas_manutencao", verbose_name="Quarto")
    tecnico = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas_manutencao", verbose_name="Técnico")
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='MEDIA', verbose_name="Prioridade")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name="Status do Chamado")
    descricao_problema = models.TextField(verbose_name="Descrição do Defeito")
    solucao_aplicada = models.TextField(blank=True, null=True, verbose_name="Resolução")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Abertura do Chamado")

    class Meta:
        verbose_name = "Tarefa de Manutenção"
        verbose_name_plural = "Tarefas de Manutenção"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Manutenção Q.{self.quarto.numero} - {self.get_status_display()}"


# ==============================================================================
# 10. ENTIDADE: TRANSAÇÃO FINANCEIRA (Caixa / DRE)
# ==============================================================================
class TransacaoFinanceira(models.Model):
    TIPO_CHOICES = [
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    ]

    CATEGORIA_CHOICES = [
        ('DIARIA', 'Faturamento de Diárias'),
        ('CONSUMO', 'Serviço de Quarto / Consumos Extras'),
        ('MANUTENCAO', 'Despesa com Manutenção e Insumos'),
        ('SALARIO', 'Folha de Pagamento de Funcionários'),
        ('OUTRO', 'Outras Receitas / Despesas Gerais'),
    ]

    METODO_CHOICES = [
        ('PIX', 'Pix instantâneo'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'),
        ('DINHEIRO', 'Dinheiro em Espécie'),
        ('TRANSFERENCIA', 'Transferência / Boleto'),
    ]

    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name="transacoes", verbose_name="Reserva")
    pousada = models.ForeignKey(Pousada, on_delete=models.CASCADE, related_name="transacoes", verbose_name="Pousada")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Transação")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default='DIARIA', verbose_name="Classificação")
    data_pagamento = models.DateField(default=timezone.now, verbose_name="Data de Efetivação")
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_CHOICES, default='PIX', verbose_name="Forma")
    descricao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descrição")
    data_vencimento = models.DateField(blank=True, null=True, verbose_name="Data de Vencimento")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="transacoes_criadas", verbose_name="Criado por")

    class Meta:
        verbose_name = "Transação Financeira"
        verbose_name_plural = "Transações Financeiras"
        ordering = ['-data_pagamento']

    def __str__(self):
        return f"{self.get_tipo_display()} - R$ {self.valor} - Pousada: {self.pousada.nome}"


def get_hospede_upload_path(instance, filename):
    """
    Gera o caminho físico para upload dos documentos dos hóspedes.
    Estrutura: media/<pousada_slug>/clientes/hospedes/<nome>_<cpf_limpo>/<arquivo>
    """
    from django.utils.text import slugify
    pousada_slug = slugify(instance.reserva.quarto.pousada.nome)
    
    # Normalização de CPF/RG para criar pasta única
    documento_limpo = instance.cpf.strip().replace('.', '').replace('-', '') if instance.cpf else ""
    if not documento_limpo:
        documento_limpo = instance.rg.strip().replace('.', '').replace('-', '') if instance.rg else ""
    if not documento_limpo:
        documento_limpo = "sem_documento"
        
    cliente_nome = slugify(instance.nome.strip())
    pasta_cliente = f"{cliente_nome}_{documento_limpo}"
    
    return f"{pousada_slug}/clientes/hospedes/{pasta_cliente}/{filename}"


# ==============================================================================
# 11. ENTIDADE: HOSPEDE DA RESERVA (FNRH COMPLEMENTAR)
# ==============================================================================
class HospedeReserva(models.Model):
    """FNRH individual de cada hóspede da reserva."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='hospedes')
    ordem = models.PositiveSmallIntegerField(default=1)  # 1 = titular, 2+ = acompanhantes
    
    # Dados pessoais (FNRH)
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    rg = models.CharField(max_length=50, blank=True)
    nacionalidade = models.CharField(max_length=100, default='Brasileira')
    profissao = models.CharField(max_length=100, blank=True)
    endereco = models.TextField(blank=True)
    
    # Documentos anexados
    documento_frente = models.FileField(upload_to=get_hospede_upload_path, null=True, blank=True)
    documento_verso = models.FileField(upload_to=get_hospede_upload_path, null=True, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordem']
        unique_together = ['reserva', 'ordem']

    def __str__(self):
        return f"{self.nome} (Reserva #{self.reserva.id})"


def get_documento_hospede_upload_path(instance, filename):
    """
    Gera o caminho físico para upload de múltiplos documentos dos hóspedes.
    """
    from django.utils.text import slugify
    pousada_slug = slugify(instance.hospede.reserva.quarto.pousada.nome)
    
    documento_limpo = instance.hospede.cpf.strip().replace('.', '').replace('-', '') if instance.hospede.cpf else ""
    if not documento_limpo:
        documento_limpo = instance.hospede.rg.strip().replace('.', '').replace('-', '') if instance.hospede.rg else ""
    if not documento_limpo:
        documento_limpo = "sem_documento"
        
    cliente_nome = slugify(instance.hospede.nome.strip() or "sem_nome")
    pasta_cliente = f"{cliente_nome}_{documento_limpo}"
    
    return f"{pousada_slug}/clientes/hospedes/{pasta_cliente}/anexos/{filename}"


class DocumentoHospede(models.Model):
    """Documentos e anexos em geral de um hóspede da reserva."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospede = models.ForeignKey(HospedeReserva, on_delete=models.CASCADE, related_name='documentos')
    arquivo = models.FileField(upload_to=get_documento_hospede_upload_path)
    nome = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

    def __str__(self):
        return f"{self.nome or self.arquivo.name} ({self.hospede.nome})"


# ==============================================================================
# 11b. ENTIDADE: LOG DE RESERVA (Auditoria Operacional)
# ==============================================================================
class ReservaLog(models.Model):
    """
    Auditoria operacional. Loga quem marcou/desmarcou check-in ou check-out
    com carimbo de data e recepcionista logado.
    """
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='logs')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=50)  # e.g., 'checkin', 'checkout', 'desmarcar_checkin'
    detalhes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.acao} - Reserva #{self.reserva.id} em {self.criado_em}"


# ==============================================================================
# 12. ENTIDADE: VEICULO DA RESERVA (Estacionamento)
# ==============================================================================
class VeiculoReserva(models.Model):
    """Veículo registrado para a reserva (controle de estacionamento/garagem)."""
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='veiculo')
    placa = models.CharField(max_length=10)
    modelo = models.CharField(max_length=100, blank=True)
    cor = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.placa} ({self.modelo})"


# ==============================================================================
# 13. ENTIDADE: BLOQUEIO ADMINISTRATIVO DE QUARTO
# ==============================================================================
class BloqueioQuarto(models.Model):
    """Permite ao hotel bloquear datas por manutenção ou indisponibilidade"""
    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name='bloqueios')
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(db_index=True)
    motivo = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Bloqueio Q.{self.quarto.numero} ({self.data_inicio} até {self.data_fim})"


# ==============================================================================
# 14. ENTIDADE: CONFIGURAÇÃO DO SITE PÚBLICO (SiteConfig)
# ==============================================================================
class SiteConfig(models.Model):
    """
    Guarda as configurações de branding e customização do website público (Hero).
    """
    hero_titulo = models.CharField(
        max_length=255,
        default="O aconchego ideal para recarregar suas energias.",
        verbose_name="Título do Hero"
    )
    hero_subtitulo = models.TextField(
        default="Descubra a tranquilidade da serra, a calmaria bucólica do sertão ou a brisa revigorante da praia em nossas unidades de alto padrão.",
        verbose_name="Subtítulo do Hero"
    )
    hero_video_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL do Vídeo do Hero (Externo)"
    )
    hero_video_arquivo = models.FileField(
        upload_to='pousadas/videos/',
        blank=True,
        null=True,
        verbose_name="Arquivo de Vídeo do Hero (Local)"
    )

    class Meta:
        verbose_name = "Configuração do Site"
        verbose_name_plural = "Configurações do Site"

    def __str__(self):
        return "Configuração Geral do Site Público"

