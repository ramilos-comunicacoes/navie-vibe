import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from hoteis.models import Hotel, Reserva, UnidadeQuarto
from datetime import date

def get_anexo_upload_path(instance, filename):
    """Gera o caminho físico organizado para anexos contábeis do hotel."""
    hotel = instance.transacao.hotel
    if hotel.empresa:
        empresa_slug = getattr(hotel.empresa, 'slug', None) or slugify(hotel.empresa.nome_fantasia)
    else:
        empresa_slug = getattr(hotel, 'slug', None) or slugify(hotel.nome) or 'default'
    
    # Pasta organizada por data de vencimento (Ano/Mês/Dia) e código da transação
    data_ref = instance.transacao.data_vencimento or date.today()
    ano = data_ref.strftime('%Y')
    mes = data_ref.strftime('%m')
    dia = data_ref.strftime('%d')
    tx_codigo = instance.transacao.codigo or f"TX_{instance.transacao.id}"
    return f"{empresa_slug}/financeiro/anexos/{ano}/{mes}/{dia}/{tx_codigo}/{filename}"

class TransacaoFinanceira(models.Model):
    """
    [IA-COMPATIBLE MODEL]
    Representa uma transação financeira real (receita ou despesa) vinculada a um hotel parceiro.
    Projetado com metadados detalhados para permitir que agentes de IA autônomos, robôs de chat
    de WhatsApp ou assistentes de voz possam ler, criar e interpretar lançamentos contábeis.
    """
    
    TIPO_CHOICES = [
        ('receita', 'Receita (Entrada de Caixa)'),
        ('despesa', 'Despesa (Saída de Caixa)'),
    ]
    
    CATEGORIA_CHOICES = [
        # Receitas (Entradas)
        ('diarias', 'Diárias e Hospedagens (Marketplace Naviê)'),
        ('walk_in', 'Balcão / Reservas Diretas (Hóspede walk-in sem comissão)'),
        ('frigobar', 'Consumos de Frigobar (Bebidas/Comidas consumidas no quarto)'),
        ('room_service', 'Serviço de Quarto / Copa (Pedidos de refeição/serviços)'),
        ('spa_lazer', 'Lazer & Experiências (Massagens, passeios, aluguéis)'),
        ('eventos_espaco', 'Eventos & Aluguel de Espaços (Salas, casamentos, reuniões)'),
        ('estacionamento', 'Taxa de Estacionamento / Garagem'),
        ('lavanderia', 'Serviços de Lavanderia (Passar, lavar roupas)'),
        ('cancelamentos_multas', 'Multas de Cancelamento & No-show'),
        ('outro_receita', 'Outras Receitas e Ajustes Positivos'),
        # Despesas (Saídas)
        ('salarios', 'Folha de Pagamento (Salários e comissões da equipe)'),
        ('manutencao', 'Manutenção Predial / Infraestrutura (Reparos, pintura, limpeza)'),
        ('energia_agua', 'Contas de Consumo (Energia elétrica, água, internet, gás)'),
        ('amenities', 'Amenities e Brindes (Shampoos, sabonetes, mimos)'),
        ('taxa_marketplace', 'Comissões Naviê / OTAs (Taxa da plataforma)'),
        ('marketing_anuncios', 'Publicidade & Marketing (Google Ads, redes sociais, impressos)'),
        ('impostos_taxas', 'Tributos, Impostos & Licenças (IPTU, DAS, taxas municipais)'),
        ('ti_escritorio', 'Tecnologia & Escritório (Softwares, papéis, computadores)'),
        ('enxoval_lavanderia', 'Enxoval & Lavanderia Externa (Lençóis, toalhas, higienização)'),
        ('tarifas_bancarias', 'Tarifas Bancárias & Taxas de Cartão'),
        ('outro_despesa', 'Outras Despesas e Perdas de Caixa'),
    ]
    
    hotel = models.ForeignKey(
        Hotel, 
        on_delete=models.CASCADE, 
        related_name='transacoes_financeiras',
        help_text="O estabelecimento hoteleiro multitenant proprietário desta transação contábil."
    )
    reserva = models.ForeignKey(
        Reserva, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transacoes_financeiras',
        help_text="Opcional. A reserva de hospedagem associada a este lançamento (útil para auditoria de estadias)."
    )
    unidade = models.ForeignKey(
        UnidadeQuarto, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transacoes_financeiras',
        help_text="Opcional. O quarto físico (unidade) associado a esta despesa ou receita."
    )
    
    tipo = models.CharField(
        'Tipo', 
        max_length=15, 
        choices=TIPO_CHOICES, 
        db_index=True,
        help_text="Determina a direção do fluxo de caixa: 'receita' aumenta o saldo, 'despesa' reduz o saldo."
    )
    categoria = models.CharField(
        'Categoria', 
        max_length=30, 
        choices=CATEGORIA_CHOICES, 
        db_index=True,
        help_text="A categorização contábil exata da transação para geração de DRE operacional."
    )
    valor = models.DecimalField(
        'Valor (R$)', 
        max_digits=10, 
        decimal_places=2,
        help_text="O valor financeiro nominal em reais (R$) associado à transação."
    )
    descricao = models.CharField(
        'Descrição', 
        max_length=255,
        help_text="Uma descrição curta explicando a natureza do lançamento (ex: 'Compra de toalhas novas')."
    )
    
    # Campo legado (para compatibilidade contábil e de queries anteriores)
    data = models.DateField(
        'Data Competência (Legado)', 
        null=True, 
        blank=True, 
        db_index=True,
        help_text="A data contábil de competência. Mantida para compatibilidade legada."
    )
    
    # Novos Campos de Data da Dupla Entrada Contábil
    data_vencimento = models.DateField(
        'Data de Vencimento', 
        default=date.today, 
        db_index=True,
        help_text="Data obrigatória em que o compromisso financeiro deve ser quitado."
    )
    data_pagamento = models.DateField(
        'Data de Pagamento', 
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Data opcional em que a transação foi efetivamente paga/compensada."
    )
    
    codigo = models.CharField(
        'Código da Transação', 
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="Código único semântico gerado automaticamente para rastreabilidade de auditoria."
    )
    
    criado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_constraint=False, # Cross-database relation to 'default' DB
        related_name='financeiro_lancamentos',
        help_text="O atendente, recepcionista ou gerente humano que cadastrou a transação no sistema."
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora exata em que o registro físico foi inserido no banco de dados."
    )

    class Meta:
        ordering = ['-data_vencimento', '-criado_em']
        verbose_name = 'Transação Financeira'
        verbose_name_plural = 'Transações Financeiras'

    def save(self, *args, **kwargs):
        # 1. Manter campo legado data sincronizado para evitar quebra de queries
        if not self.data:
            self.data = self.data_vencimento
            
        # 2. Gerar Código Único Semântico
        if not self.codigo:
            CATEGORIA_CODES = {
                'diarias': 'DIA', 'walk_in': 'WLK', 'frigobar': 'FRG', 'room_service': 'RMS', 
                'spa_lazer': 'SPA', 'outro_receita': 'REC', 'salarios': 'SAL', 'manutencao': 'MNT', 
                'energia_agua': 'CNS', 'amenities': 'AMN', 'taxa_marketplace': 'TXM', 'outro_despesa': 'DSP',
                'eventos_espaco': 'EVE', 'estacionamento': 'EST', 'lavanderia': 'LAV', 'cancelamentos_multas': 'MUL',
                'marketing_anuncios': 'MKT', 'impostos_taxas': 'TAX', 'ti_escritorio': 'TEC', 'enxoval_lavanderia': 'ENX',
                'tarifas_bancarias': 'BNK'
            }
            cat_code = CATEGORIA_CODES.get(self.categoria, 'GEN')
            res_short = str(self.reserva.id)[:8].upper() if self.reserva else 'GEN'
            data_str = (self.data_vencimento or date.today()).strftime('%Y%m%d')
            rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            self.codigo = f"TX-{self.hotel.id}-{cat_code}-{res_short}-{data_str}-{rand_str}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.get_tipo_display()} - R$ {self.valor}"

    @property
    def ai_summary(self):
        """
        [IA-INTERPRETATION LAYER]
        Retorna uma frase natural contendo um resumo completo da transação contábil.
        Projetada especificamente para que LLMs, agentes autônomos ou bots de WhatsApp
        possam ler e responder perguntas em áudio ou texto de forma humanizada.
        """
        tipo_str = "entrada (receita)" if self.tipo == 'receita' else "saída (despesa)"
        cliente_nome = "N/A"
        if self.reserva:
            cliente_nome = self.reserva.hospede_nome or (self.reserva.usuario.get_full_name() if self.reserva.usuario else None) or "N/A"
        origem = f" vinculada à reserva do cliente {cliente_nome}" if self.reserva else ""
        quarto_str = f" no quarto {self.unidade.identificador}" if self.unidade else ""
        criador = f" por {self.criado_por.get_full_name() or self.criado_por.username}" if self.criado_por else ""
        pagamento_str = f" pago em {self.data_pagamento.strftime('%d/%m/%Y')}" if self.data_pagamento else " (pendente de pagamento)"
        
        return (
            f"Transação {self.codigo} de {tipo_str} registrada com vencimento em {self.data_vencimento.strftime('%d/%m/%Y')}{pagamento_str}. "
            f"Valor: R$ {self.valor:.2f}. Categoria contábil: {self.get_categoria_display()}. "
            f"Descrição: '{self.descricao}'. Lançamento inserido no sistema{criador}{quarto_str}{origem}."
        )

class AnexoTransacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transacao = models.ForeignKey(TransacaoFinanceira, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to=get_anexo_upload_path)
    codigo = models.CharField('Código do Anexo', max_length=60, unique=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'financeiro_anexotransacao'
        verbose_name = 'Anexo de Transação'
        verbose_name_plural = 'Anexos de Transações'

    def save(self, *args, **kwargs):
        if not self.codigo:
            rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            self.codigo = f"ANX-{self.transacao.codigo}-{rand_str}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} ({self.arquivo.name})"


from core.models import Empresa

class MercadoPagoConexao(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='mp_conexao', db_constraint=False)
    mp_user_id = models.CharField("ID da Conta Mercado Pago do Hoteleiro", max_length=100)
    access_token = models.CharField("Access Token do Parceiro", max_length=255)
    refresh_token = models.CharField("Refresh Token para Renovação", max_length=255)
    token_expira_em = models.DateTimeField("Data de Expiração do Token")
    data_conexao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MP Conexão - {self.empresa.nome}"
