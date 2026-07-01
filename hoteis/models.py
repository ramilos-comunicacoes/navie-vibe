from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid
import unicodedata
import re

class Produtor(models.Model):
    nome_publico = models.CharField(max_length=255)
    
    def __str__(self):
        return self.nome_publico

class Local(models.Model):
    nome = models.CharField(max_length=255)
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    
    def __str__(self):
        return f"{self.nome} - {self.cidade}/{self.estado}"

from core.models import Empresa

class Hotel(models.Model): # Representa a operação de Hospedagem de uma Empresa
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='hoteis',
        null=True, blank=True,
        db_constraint=False,
        help_text="A entidade comercial dona desta hospedagem"
    )
    nome = models.CharField(max_length=255) # Pode ser diferente do Nome Fantasia se desejar
    descricao = models.TextField()
    banner = models.ImageField(upload_to='hoteis/banners/', null=True, blank=True)
    
    # Relações
    local = models.ForeignKey(Local, on_delete=models.CASCADE, related_name='hoteis')
    produtor = models.ForeignKey(Produtor, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=50, default='ativo', choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')], db_index=True)
    destaque = models.BooleanField(default=False)
    
    data_inicio = models.DateField(null=True, blank=True) # Prazo de estadia/evento se houver
    horario_inicio = models.TimeField(null=True, blank=True)
    
    # Configurações & Branding do Site/Sistema
    cor_primaria = models.CharField(max_length=7, default='#f97316', help_text="Cor primária em formato Hexadecimal (ex: #f97316)")
    cor_secundaria = models.CharField(max_length=7, default='#2563eb', help_text="Cor secundária em formato Hexadecimal (ex: #2563eb)")
    imagem_compartilhamento = models.ImageField(upload_to='hoteis/compartilhamento/', null=True, blank=True, help_text="Imagem para miniatura de compartilhamento (WhatsApp, Instagram, etc.)")
    whatsapp = models.CharField(max_length=20, blank=True, null=True, help_text="WhatsApp de contato do hotel")
    hero_tipo = models.CharField(
        max_length=10, 
        default='imagem', 
        choices=[('imagem', 'Imagem'), ('video', 'Vídeo')],
        help_text="Tipo de mídia a ser exibida no cabeçalho/Hero do site"
    )
    hero_video = models.FileField(upload_to='hoteis/videos/', null=True, blank=True, help_text="Vídeo curto em loop (MP4 de até 8MB)")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Coordenada geográfica de latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Coordenada geográfica de longitude")
    endereco_completo = models.CharField(max_length=500, blank=True, null=True, help_text="Endereço legível para o mapa")
    como_chegar = models.TextField(blank=True, null=True, help_text="Instruções de como chegar, pontos de referência, etc.")

    # Seção Sobre da Pousada Individual (Vitrine do Site)
    sobre_titulo = models.CharField('Título da Seção Sobre', max_length=255, blank=True, null=True)
    sobre_texto = models.TextField('Texto da Seção Sobre', blank=True, null=True)
    sobre_midia_tipo = models.CharField(
        'Tipo de Mídia do Sobre',
        max_length=10,
        default='imagem',
        choices=[('imagem', 'Imagem'), ('video', 'Vídeo')]
    )
    sobre_banner = models.ImageField('Imagem do Sobre', upload_to='hoteis/sobre/', null=True, blank=True)
    sobre_video = models.FileField(
        'Vídeo do Sobre',
        upload_to='hoteis/sobre_videos/',
        null=True,
        blank=True,
        help_text="Vídeo curto em loop (MP4 de até 8MB)"
    )
    sobre_cor_fundo = models.CharField('Cor de Fundo do Sobre (Hex)', max_length=7, default='#f8fafc')
    sobre_cor_texto = models.CharField('Cor do Texto do Sobre (Hex)', max_length=7, default='#0f172a')
    logo = models.ImageField(upload_to='hoteis/logos/', null=True, blank=True, help_text="Logo oficial da pousada")
    favicon = models.ImageField(
        'Favicon da Pousada',
        upload_to='hoteis/favicons/',
        null=True,
        blank=True,
        help_text='Ícone que aparece na aba do navegador para esta pousada específica. Recomenda-se imagem quadrada (ex: 32x32 ou 64x64px).'
    )
    imagem_card = models.ImageField(
        'Imagem do Card (Vitrine)',
        upload_to='hoteis/cards/',
        null=True,
        blank=True,
        help_text='Imagem que aparece no card de listagem desta pousada na página inicial. Se não informada, será usado o banner.'
    )
    foto_fundo = models.ImageField(upload_to='hoteis/fundos/', null=True, blank=True, help_text="Imagem de fundo para o modo Glassmorphism")
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, help_text="Slug da URL customizada (ex: pousadaramilostiangua)")
    visualizacoes = models.PositiveIntegerField(default=0, help_text="Total de visualizações da página do hotel")
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição no portal unificado do grupo")
    venda_online = models.BooleanField(default=False, help_text="Se ativado, permite reservas e pagamentos online pelo site. Se desativado, o botão de reserva direciona para contato via WhatsApp.")

    # Configurações Administrativas do Marketplace (Naviê Vibe)
    taxa_fixa_navie = models.DecimalField(max_digits=10, decimal_places=2, default=15.00, help_text="Taxa fixa cobrada pelo Naviê por reserva (R$)")
    taxa_percentual_navie = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Comissão percentual cobrada pelo Naviê (%)")
    limite_trafego_gb = models.PositiveIntegerField(default=100, help_text="Limite de tráfego mensal alocado em GB")
    consumo_trafego_gb = models.DecimalField(max_digits=10, decimal_places=2, default=14.20, help_text="Consumo atual de tráfego no mês em GB")
    usar_tarifas_faixa = models.BooleanField(default=False, help_text="Se ativado, utiliza a tabela de faixas de valor para calcular a taxa da diária")


    
    def __str__(self):
        return self.nome

class HotelImagem(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='imagens')
    url_imagem = models.ImageField(upload_to='hoteis/galeria/')
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordem']

class Quarto(models.Model): # Antigo 'Tipos de Ingresso'
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='quartos')
    nome = models.CharField(max_length=150) # Ex: Suite Master
    slug = models.SlugField(max_length=180, blank=True, help_text="URL amigável gerada automaticamente pelo nome")
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Novos campos para gestão avançada, SEO e IA
    video_url = models.CharField(max_length=500, blank=True, null=True, help_text="Link para vídeo MP4 ou embed")
    video_arquivo = models.FileField(upload_to='quartos/videos/', blank=True, null=True, help_text="Arquivo de vídeo local do tour")
    capacidade_pessoas = models.IntegerField(default=2, help_text="Capacidade de hóspedes")
    tags = models.CharField(max_length=255, blank=True, default="", help_text="Categorização (ex: Família, Romântico)")
    comodidades = models.CharField(max_length=255, blank=True, default="", help_text="Comodidades (ex: Ar Condicionado, Wi-Fi)")
    
    # Descontos progressivos
    tem_desconto_multidias = models.BooleanField(default=False)
    dias_minimos_desconto = models.IntegerField(default=3, help_text="Mínimo de dias para ativar desconto")
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Desconto em percentual (ex: 10.00 para 10%)")
    
    # Otimização SEO e Assistentes IA (ex: Google Gemini)
    seo_titulo = models.CharField(max_length=150, blank=True, null=True, help_text="Título customizado para buscadores/IA")
    seo_descricao = models.TextField(blank=True, null=True, help_text="Descrição customizada para buscadores/IA")
    visualizacoes = models.PositiveIntegerField(default=0, help_text="Total de visualizações do quarto")
    
    class Meta:
        # Garante que o slug é único dentro de cada hotel (não globalmente)
        unique_together = [('hotel', 'slug')]
    
    @staticmethod
    def _normalizar_slug(texto):
        """Converte caracteres acentuados para ASCII antes de slugify."""
        nfkd = unicodedata.normalize('NFKD', texto)
        ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
        return slugify(ascii_str)
    
    def _gerar_slug_unico(self):
        """Gera slug único por hotel, adicionando sufixo numérico se necessário."""
        base_slug = self._normalizar_slug(self.nome) or f'acomodacao-{self.id or 0}'
        candidato = base_slug
        num = 2
        while True:
            conflito = Quarto.objects.filter(hotel=self.hotel, slug=candidato)
            if self.pk:
                conflito = conflito.exclude(pk=self.pk)
            if not conflito.exists():
                return candidato
            candidato = f'{base_slug}-{num}'
            num += 1
    
    def save(self, *args, **kwargs):
        # Regera slug sempre que o nome mudar ou slug estiver vazio
        if not self.slug or (self.pk and Quarto.objects.filter(pk=self.pk).values_list('nome', flat=True).first() != self.nome):
            self.slug = self._gerar_slug_unico()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"

class QuartoImagem(models.Model):
    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name='imagens')
    url_imagem = models.ImageField(upload_to='quartos/galeria/')
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordem']

    def __str__(self):
        return f"Img {self.ordem} - {self.quarto.nome}"

class UnidadeQuarto(models.Model):
    """
    Representa a sala física real (unidade individual/quarto específico) de uma categoria de quarto.
    Exemplo: Quarto 101, Chale 2, Deck Master.
    
    Campos e Relacionamentos para Assistentes de IA:
    - quarto (ForeignKey -> Quarto): A categoria do quarto (ex: Suíte Executiva), que define preço base e capacidade.
    - identificador (CharField): O número ou nome visível da unidade física (ex: '101', 'Chalé 05').
    - ativa (BooleanField): Indica se a unidade física está ativa e operante no sistema de vendas.
    - disponivel (BooleanField): Status operacional do quarto para fins de check-in imediato ou estadia.
    - motivo_indisponivel (CharField): Se disponivel for False, define a causa ('limpeza', 'manutencao', 'outro').
    - justificativa_indisponivel (TextField): Observações ou detalhes adicionais da indisponibilidade.
    
    Propriedades Úteis para IA:
    - status_mapa: Retorna o status consolidado da unidade em tempo real ('ocupado', 'limpeza', 'indisponivel', 'livre').
    - reserva_ativa: Retorna o objeto Reserva ativo (hospedado) se o quarto estiver ocupado.
    """
    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name='unidades')
    identificador = models.CharField(max_length=50, help_text="Ex: 101, Chale 01, Deck Master")
    ativa = models.BooleanField(default=True, db_index=True)
    
    # Novos campos para gestão de disponibilidade operacional
    disponivel = models.BooleanField(default=True, db_index=True)
    motivo_indisponivel = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        choices=[('limpeza', 'Limpeza'), ('manutencao', 'Manutenção'), ('outro', 'Outro')]
    )
    justificativa_indisponivel = models.TextField(blank=True, null=True)
    
    @property
    def status_mapa(self):
        from hoteis.models import Reserva, Tarefa
        if Reserva.objects.filter(unidade=self, status='hospedado').exists():
            return 'ocupado'
        if not self.disponivel:
            if self.motivo_indisponivel == 'limpeza':
                return 'limpeza'
            return 'indisponivel'
        if Tarefa.objects.filter(unidade=self, status__in=['todo', 'doing'], titulo__icontains='Limpeza').exists():
            return 'limpeza'
        return 'livre'

    @property
    def reserva_ativa(self):
        from hoteis.models import Reserva
        return Reserva.objects.filter(unidade=self, status='hospedado').first()

    def __str__(self):
        return f"{self.identificador} ({self.quarto.nome})"

class Reserva(models.Model):
    """
    Representa uma reserva de hospedagem (booking) efetuada para uma unidade de quarto física específica.
    Pode ter origem no marketplace (venda online) ou ser uma reserva direta criada na recepção (walk-in).
    
    Campos e Relacionamentos para Assistentes de IA:
    - id (UUIDField): Chave primária única da reserva.
    - usuario (ForeignKey -> User): Hóspede registrado no portal (opcional para walk-in).
    - unidade (ForeignKey -> UnidadeQuarto): A unidade física de quarto reservada.
    - data_checkin (DateField): Data agendada de chegada/entrada.
    - data_checkout (DateField): Data agendada de partida/saída.
    - subtotal (DecimalField): Valor bruto total das diárias.
    - taxas (DecimalField): Taxas gerais incidentes.
    - valor_total (DecimalField): Valor total pago/a pagar pelo hóspede.
    - status (CharField): Estado atual da reserva:
        * 'pendente': Aguardando confirmação ou pagamento.
        * 'confirmada': Confirmada e aguardando check-in do hóspede.
        * 'hospedado': Hóspede realizou check-in e está ocupando o quarto.
        * 'concluido': Checkout realizado com sucesso. Estadia finalizada.
        * 'cancelada': Reserva cancelada e unidade liberada.
    - canal_venda (CharField): Origem da venda ('marketplace' ou 'walk-in').
    - checkin_realizado_em (DateTimeField): Data e hora reais do check-in físico efetuado.
    - checkout_realizado_em (DateTimeField): Data e hora reais do check-out físico efetuado.
    - hospede_nome (CharField): Nome completo do hóspede titular da estadia.
    - hospede_cpf, hospede_email, hospede_telefone, hospede_rg (CharField/EmailField): Dados pessoais de contato do hóspede.
    - hospede_nacionalidade, hospede_profissao, hospede_endereco: Informações adicionais do hóspede para a FNRH.
    - quantidade_hospedes (PositiveIntegerField): Quantidade total de pessoas inclusas na reserva.
    - taxa_servico_plataforma, taxa_gateway, repasse_parceiro, ganho_liquido_plataforma: Métricas financeiras de controle administrativo.
    
    Propriedades Úteis para IA:
    - noites: Retorna o número calculado de noites/diárias com base no checkin e checkout.
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('hospedado', 'Hospedado'),
        ('concluido', 'Concluído'),
        ('cancelada', 'Cancelada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reservas', db_constraint=False)
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.PROTECT, related_name='reservas')
    data_checkin = models.DateField(db_index=True)
    data_checkout = models.DateField(db_index=True)
    
    # Valores financeiros
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    taxas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
    canal_venda = models.CharField(max_length=50, default='marketplace', help_text="marketplace ou walk-in")
    pagamento_id = models.CharField("ID do Pagamento no Gateway", max_length=100, blank=True, null=True, db_index=True)
    
    # Datas de execução reais de portaria
    checkin_realizado_em = models.DateTimeField(null=True, blank=True)
    checkout_realizado_em = models.DateTimeField(null=True, blank=True)
    
    # Ficha de Registro Nacional de Hóspedes (FNRH) histórica da reserva
    hospede_nome = models.CharField(max_length=255, blank=True, null=True)
    hospede_cpf = models.CharField(max_length=20, blank=True, null=True)
    hospede_email = models.EmailField(blank=True, null=True)
    hospede_telefone = models.CharField(max_length=20, blank=True, null=True)
    hospede_rg = models.CharField(max_length=50, blank=True, null=True)
    hospede_nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    hospede_profissao = models.CharField(max_length=100, blank=True, null=True)
    hospede_endereco = models.TextField(blank=True, null=True)
    quantidade_hospedes = models.PositiveIntegerField(default=1)
    taxa_servico_plataforma = models.DecimalField('Taxa de Serviço Naviê', max_digits=10, decimal_places=2, default=0.00)
    taxa_gateway = models.DecimalField('Taxa Gateway Absorvida', max_digits=10, decimal_places=2, default=0.00)
    repasse_parceiro = models.DecimalField('Repasse Líquido ao Parceiro', max_digits=10, decimal_places=2, default=0.00)
    ganho_liquido_plataforma = models.DecimalField('Ganho Líquido Naviê', max_digits=10, decimal_places=2, default=0.00)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    @property
    def noites(self):
        if self.data_checkin and self.data_checkout:
            return (self.data_checkout - self.data_checkin).days
        return 1

    @property
    def consumo_acumulado(self):
        from django.db.models import Sum
        total = self.pedidos_servico.exclude(status='cancelado').aggregate(total=Sum('valor_total'))['total']
        return total or 0.00
        
    def __str__(self):
        return f"Reserva #{str(self.id)[:8].upper()} - {self.unidade.identificador}"

class BloqueioQuarto(models.Model):
    """
    Permite ao hotel/pousada bloquear datas específicas de uma unidade física para reservas futuras,
    seja por motivos de manutenção prolongada, reformas ou bloqueio estratégico.
    
    Campos para Assistentes de IA:
    - unidade (ForeignKey -> UnidadeQuarto): A unidade física bloqueada.
    - data_inicio (DateField): Data inicial do bloqueio.
    - data_fim (DateField): Data final do bloqueio.
    - motivo (CharField): Justificativa/motivo do bloqueio.
    """
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.CASCADE, related_name='bloqueios')
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(db_index=True)
    motivo = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Bloqueio {self.unidade.identificador} ({self.data_inicio} até {self.data_fim})"

class ParceiroUsuario(models.Model):
    ROLE_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('gerente', 'Gerente'),
        ('portaria', 'Portaria / Recepção'),
        ('camareira', 'Camareira / Limpeza'),
        ('manutencao', 'Manutenção'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_parceiro', db_constraint=False)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='equipe', db_constraint=False)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='portaria')
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True, help_text="Formato: 000.000.000-00")
    ativo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} ({self.hotel.nome})"


class Tarefa(models.Model):
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
    ]
    STATUS_CHOICES = [
        ('todo', 'A Fazer'),
        ('doing', 'Em Progresso'),
        ('done', 'Concluído'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='tarefas')
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='normal')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='todo', db_index=True)
    data_vencimento = models.DateField(blank=True, null=True, db_index=True)
    
    # Mapeamentos para Hospedagem:
    responsavel = models.ForeignKey(ParceiroUsuario, on_delete=models.SET_NULL, blank=True, null=True, related_name='tarefas_atribuidas')
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.SET_NULL, blank=True, null=True, related_name='tarefas')
    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, blank=True, null=True, related_name='tarefas')
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titulo} - {self.get_status_display()}"
        
    @property
    def is_atrasada(self):
        from datetime import date
        if self.data_vencimento and self.data_vencimento < date.today() and self.status != 'done':
            return True
        return False


def get_hospede_upload_path(instance, filename):
    """Gera o caminho físico organizado para documentos do hóspede na pasta clientes/hospedes."""
    empresa_slug = 'default'
    try:
        hotel = instance.reserva.unidade.quarto.hotel
        if hotel.empresa:
            empresa_slug = hotel.empresa.slug or slugify(hotel.empresa.nome_fantasia)
        else:
            empresa_slug = hotel.slug or 'default'
    except Exception:
        pass
        
    # Limpar nome e CPF/RG para criar uma pasta organizada e segura
    cliente_nome = slugify(instance.nome) or 'sem_nome'
    cliente_cpf = re.sub(r'\D', '', instance.cpf) or instance.rg or 'sem_documento'
    
    cliente_nome = cliente_nome.replace('-', '_')
    pasta_cliente = f"{cliente_nome}_{cliente_cpf}"
    
    return f"{empresa_slug}/clientes/hospedes/{pasta_cliente}/{filename}"


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
    
    # Documentos anexados (Identidade frente e verso)
    documento_frente = models.FileField(upload_to=get_hospede_upload_path, null=True, blank=True)
    documento_verso = models.FileField(upload_to=get_hospede_upload_path, null=True, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordem']
        unique_together = ['reserva', 'ordem']


class VeiculoReserva(models.Model):
    """Veículo registrado para a reserva (controle de estacionamento)."""
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='veiculo')
    placa = models.CharField(max_length=10)
    modelo = models.CharField(max_length=100, blank=True)
    cor = models.CharField(max_length=50, blank=True)


class ReservaLog(models.Model):
    """Log de auditoria de check-in e check-out de reservas."""
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='logs')
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reserva_logs', db_constraint=False)
    acao = models.CharField(max_length=100) # 'checkin', 'checkout', 'desmarcar_checkin', 'desmarcar_checkout'
    data_hora = models.DateTimeField(auto_now_add=True)
    detalhes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_hora']
        db_table = 'hoteis_reservalog'


class ProdutoConsumo(models.Model):
    """Itens e produtos disponíveis para Room Service, Frigobar ou Consumo Geral."""
    TIPO_CHOICES = [
        ('bebida', 'Bebida'),
        ('comida', 'Comida'),
        ('servico', 'Serviço'),
        ('cortesia', 'Cortesia/Apoio'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='cardapio_consumo')
    estoque_produto = models.ForeignKey('estoque.Produto', on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos_consumo_vinculados', help_text="Vincular ao estoque físico para dedução automática ao consumir.")
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='bebida')
    disponivel = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        db_table = 'hoteis_produtoconsumo'

    def __str__(self):
        return f"{self.nome} - R$ {self.preco} ({self.get_tipo_display()})"


class PedidoServico(models.Model):
    """Solicitações de serviços de quarto, copa ou recepção feitas pelo hóspede."""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('preparo', 'Em Preparo'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='pedidos_servico')
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.CASCADE, related_name='pedidos_servico')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='pedidos_servico')
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendente', db_index=True)
    observacoes = models.TextField(blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        db_table = 'hoteis_pedidoservico'

    def __str__(self):
        return f"Pedido #{self.id} ({self.unidade.identificador}) - {self.get_status_display()}"


class ItemPedidoServico(models.Model):
    """Item individual cobrado e associado a um pedido/solicitação."""
    pedido = models.ForeignKey(PedidoServico, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(ProdutoConsumo, on_delete=models.PROTECT, related_name='itens_pedido')
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'hoteis_itempedidoservico'

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} no Pedido #{self.pedido.id}"


class HomeSlide(models.Model):
    MEDIA_CHOICES = [
        ('imagem', 'Imagem'),
        ('video', 'Vídeo'),
    ]
    
    titulo = models.CharField("Título Principal", max_length=200)
    subtitulo = models.TextField("Subtítulo / Descrição", blank=True)
    tipo_midia = models.CharField("Tipo de Mídia", max_length=10, choices=MEDIA_CHOICES, default='imagem')
    imagem = models.ImageField("Imagem do Slide", upload_to='slides/', blank=True, null=True)
    video = models.FileField("Vídeo do Slide", upload_to='slides/videos/', blank=True, null=True)
    
    data_texto = models.CharField("Texto de Data", max_length=100, blank=True, help_text="Ex: 15 a 18 de Junho")
    local_texto = models.CharField("Texto de Localização", max_length=150, blank=True, help_text="Ex: Tianguá, CE")
    
    texto_cta = models.CharField("Texto do Botão", max_length=50, default="Ver Detalhes")
    link_cta = models.CharField("Link do Botão", max_length=255, blank=True, help_text="URL de destino")
    
    ordem = models.PositiveIntegerField("Ordem de Exibição", default=0)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Slide da Home"
        verbose_name_plural = "Slides da Home"
        ordering = ['ordem', 'id']

    def __str__(self):
        return self.titulo


class Cidade(models.Model):
    nome = models.CharField("Nome da Cidade", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=120, unique=True)
    imagem = models.ImageField("Imagem do Card", upload_to='cidades/')
    banner = models.ImageField("Banner do Hero", upload_to='cidades/banners/', blank=True, null=True)
    descricao = models.TextField("Descrição / Slogan", blank=True)
    
    class Meta:
        verbose_name = "Cidade"
        verbose_name_plural = "Cidades"
        ordering = ['nome']
        
    def __str__(self):
        return self.nome


class Restaurante(models.Model):
    nome = models.CharField("Nome do Restaurante", max_length=255)
    especialidade = models.CharField("Especialidade Culinária", max_length=150, help_text="Ex: Pizzaria, Massas, Regional")
    imagem = models.ImageField("Foto Principal", upload_to='restaurantes/')
    cidade_nome = models.CharField("Nome da Cidade", max_length=100, db_index=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    whatsapp = models.CharField("WhatsApp de Contato", max_length=20, blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    
    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ['nome']
        
    def __str__(self):
        return self.nome


class ConfigSistema(models.Model):
    taxa_fixa_padrao = models.DecimalField(max_digits=10, decimal_places=2, default=15.00, help_text="Taxa fixa padrão do sistema por reserva (R$)")
    taxa_percentual_padrao = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Comissão percentual padrão do sistema (%)")
    limite_trafego_padrao = models.PositiveIntegerField(default=100, help_text="Limite padrão de tráfego em GB")

    class Meta:
        verbose_name = "Configuração Geral do Sistema"
        verbose_name_plural = "Configurações Gerais do Sistema"

    def __str__(self):
        return "Configurações Gerais do Sistema"


class HotelTarifaFaixa(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='tarifas_faixa')
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor mínimo da diária")
    valor_maximo = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor máximo da diária")
    taxa_fixa = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Taxa fixa em R$")
    taxa_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Taxa em %")

    class Meta:
        verbose_name = "Faixa de Tarifa"
        verbose_name_plural = "Faixas de Tarifas"
        ordering = ['valor_minimo']

    def __str__(self):
        return f"{self.hotel.nome}: R$ {self.valor_minimo} a R$ {self.valor_maximo} -> R$ {self.taxa_fixa} + {self.taxa_percentual}%"


class HotelDocumento(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='documentos')
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='hoteis/documentos/')
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento do Hotel"
        verbose_name_plural = "Documentos do Hotel"
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.nome} ({self.hotel.nome})"


class HotelTermoAdesao(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='termos_adesao')
    versao_termo = models.CharField(max_length=50, default='1.0')
    data_aceite = models.DateTimeField(auto_now_add=True)
    ip_origem = models.GenericIPAddressField()
    dispositivo = models.TextField()
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False)

    class Meta:
        verbose_name = "Aceite de Termo"
        verbose_name_plural = "Aceites de Termos"
        ordering = ['-data_aceite']

    def __str__(self):
        return f"{self.hotel.nome} aceitou v{self.versao_termo} em {self.data_aceite}"


class HotelAuditLog(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='audit_logs')
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False)
    data_alteracao = models.DateTimeField(auto_now_add=True)
    ip_origem = models.GenericIPAddressField()
    dispositivo = models.TextField()
    campo_alterado = models.CharField(max_length=100)
    valor_antigo = models.TextField(null=True, blank=True)
    valor_novo = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Log de Alteração do Hotel"
        verbose_name_plural = "Logs de Alteração de Hotéis"
        ordering = ['-data_alteracao']

    def __str__(self):
        return f"{self.hotel.nome} - {self.campo_alterado} por {self.usuario.username if self.usuario else 'Sistema'}"


class HotelSecao(models.Model):
    TIPO_CHOICES = [
        ('texto_imagem', 'Texto com Imagem'),
        ('galeria', 'Galeria de Fotos'),
        ('atracoes', 'Grade de Atrações / Atividades'),
        ('video', 'Vídeo em Destaque'),
        ('destaques', 'Carrossel de Destaques'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='secoes')
    titulo = models.CharField('Título da Seção', max_length=200)
    subtitulo = models.CharField('Subtítulo', max_length=255, blank=True, null=True)
    tipo = models.CharField('Tipo de Layout', max_length=20, choices=TIPO_CHOICES, default='texto_imagem')
    
    # Campos para tipo 'texto_imagem' ou 'video'
    texto = models.TextField('Texto / Descrição', blank=True, null=True)
    imagem = models.ImageField('Imagem de Destaque', upload_to='hoteis/secoes/', blank=True, null=True)
    video = models.FileField('Vídeo da Seção', upload_to='hoteis/secoes/videos/', blank=True, null=True)
    video_url = models.CharField('URL de Vídeo (YouTube/Vimeo ou MP4)', max_length=500, blank=True, null=True)
    link_cta = models.CharField('Link de Ação', max_length=255, blank=True, null=True)
    preco = models.DecimalField('Preço/Valor', max_digits=10, decimal_places=2, null=True, blank=True)
    
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    ativa = models.BooleanField('Ativa?', default=True)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = 'Seção do Hotel'
        verbose_name_plural = 'Seções do Hotel'

    @property
    def is_internal_link(self):
        if not self.link_cta:
            return False
        link = self.link_cta.strip().lower()
        if link.startswith('/') or 'localhost' in link or 'navievibe' in link or 'navie.com' in link:
            return True
        return False

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()}) - {self.hotel.nome}"


class HotelSecaoItem(models.Model):
    """
    Itens específicos para seções de tipo repetitivo (Galeria de Fotos ou Grade de Atrações)
    """
    secao = models.ForeignKey(HotelSecao, on_delete=models.CASCADE, related_name='itens')
    titulo = models.CharField('Título/Legenda', max_length=200)
    descricao = models.TextField('Descrição/Detalhes', blank=True, null=True)
    preco = models.DecimalField('Preço Individual (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    imagem = models.ImageField('Foto do Item', upload_to='hoteis/secoes/itens/', blank=True, null=True)
    video = models.FileField('Vídeo do Item', upload_to='hoteis/secoes/itens/videos/', blank=True, null=True)
    link_cta = models.CharField('Link de Ação / Compras', max_length=255, blank=True, null=True, help_text="Link para compra de ingresso ou WhatsApp")
    ordem = models.PositiveIntegerField('Ordem', default=0)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = 'Item da Seção'
        verbose_name_plural = 'Itens da Seção'

    @property
    def is_internal_link(self):
        if not self.link_cta:
            return False
        link = self.link_cta.strip().lower()
        if link.startswith('/') or 'localhost' in link or 'navievibe' in link or 'navie.com' in link:
            return True
        return False

    def __str__(self):
        return f"{self.titulo} - {self.secao.titulo}"




