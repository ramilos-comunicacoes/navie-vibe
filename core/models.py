from django.db import models
from django.core.exceptions import ValidationError


class Empresa(models.Model):
    CATEGORIA_CHOICES = [
        ('hospedagem', 'Hospedagem (Hotel/Pousada)'),
        ('cinema', 'Cinema'),
        ('eventos', 'Shows & Eventos'),
        ('parques', 'Parques e Atrações'),
    ]

    nome_fantasia = models.CharField('Nome Fantasia', max_length=255)
    razao_social = models.CharField('Razão Social', max_length=255)
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    
    categoria = models.CharField('Categoria Principal', max_length=20, choices=CATEGORIA_CHOICES)
    
    # Roteamento e Modalidade de Rede (Exclusivo do Admin do Sistema)
    slug = models.SlugField('Subdomínio da Rede', unique=True, blank=True, null=True, help_text='Subdomínio para o portal unificado da empresa. Ex: pousadasramilos')
    
    MODALIDADE_PORTAL_CHOICES = [
        ('individual', 'Páginas Individuais por Pousada'),
        ('unificado', 'Portal de Rede Unificado (Uma única página para o grupo)'),
    ]
    modalidade_portal = models.CharField(
        'Modalidade do Portal',
        max_length=20,
        choices=MODALIDADE_PORTAL_CHOICES,
        default='individual',
        help_text='Define se a empresa exibe um portal único com todos os hotéis ou páginas independentes.'
    )
    
    logo = models.ImageField(upload_to='empresas/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='empresas/banners/', null=True, blank=True)
    hero_tipo = models.CharField(
        'Tipo de Mídia do Hero',
        max_length=10, 
        default='imagem', 
        choices=[('imagem', 'Imagem'), ('video', 'Vídeo')],
        help_text="Tipo de mídia a ser exibida no cabeçalho/Hero do site"
    )
    hero_video = models.FileField(
        'Vídeo do Hero',
        upload_to='empresas/videos/', 
        null=True, 
        blank=True, 
        help_text="Vídeo curto em loop (MP4 de até 8MB)"
    )
    
    cor_primaria = models.CharField('Cor da Marca (Hex)', max_length=7, default='#1e3a8a')
    cor_secundaria = models.CharField('Cor Secundária (Hex)', max_length=7, default='#2563eb')
    imagem_compartilhamento = models.ImageField(
        'Imagem de Compartilhamento (16:9)', 
        upload_to='empresas/compartilhamento/', 
        null=True, 
        blank=True, 
        help_text='Imagem para miniatura de compartilhamento nas redes sociais (WhatsApp, Facebook, etc.)'
    )
    descricao_portal = models.TextField('Descrição/Slogan do Portal', blank=True, null=True, help_text='Slogan ou descrição principal da rede que aparecerá no topo do portal unificado.')
    
    # Seção Sobre (Portal de Rede Unificado)
    sobre_titulo = models.CharField('Título da Seção Sobre', max_length=255, blank=True, null=True)
    sobre_texto = models.TextField('Texto da Seção Sobre', blank=True, null=True)
    sobre_midia_tipo = models.CharField(
        'Tipo de Mídia do Sobre',
        max_length=10,
        default='imagem',
        choices=[('imagem', 'Imagem'), ('video', 'Vídeo')]
    )
    sobre_banner = models.ImageField('Imagem do Sobre', upload_to='empresas/sobre/', null=True, blank=True)
    sobre_video = models.FileField(
        'Vídeo do Sobre',
        upload_to='empresas/sobre_videos/',
        null=True,
        blank=True,
        help_text="Vídeo curto em loop (MP4 de até 8MB)"
    )
    sobre_cor_fundo = models.CharField('Cor de Fundo do Sobre (Hex)', max_length=7, default='#f8fafc')
    sobre_cor_texto = models.CharField('Cor do Texto do Sobre (Hex)', max_length=7, default='#0f172a')
    
    # Endereço e Localização
    endereco = models.CharField('Endereço', max_length=255)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2)
    cep = models.CharField('CEP', max_length=9)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Contato
    email_contato = models.EmailField('E-mail de Contato')
    telefone_contato = models.CharField('Telefone / WhatsApp', max_length=20)
    
    ativa = models.BooleanField(default=True)
    destaque = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    visualizacoes = models.PositiveIntegerField(default=0, help_text="Total de visualizações da página da empresa")

    @property
    def hoteis_ativos_ordenados(self):
        return self.hoteis.filter(status='ativo').order_by('ordem', 'id')

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return f"{self.nome_fantasia} ({self.get_categoria_display()})"


class PlataformaConfig(models.Model):
    """
    Configurações globais do Naviê Vibe (Singleton).
    """
    titulo_site = models.CharField(max_length=100, default='Naviê Vibe')
    
    # Chaves de API (Serão tratadas com criptografia futuramente)
    google_maps_key = models.CharField('Google Maps API Key', max_length=255, blank=True)
    cloudinary_url = models.CharField('Cloudinary URL', max_length=255, blank=True)
    
    # Financeiro
    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('mercado_pago', 'Mercado Pago'),
    ]
    gateway_ativo = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='stripe')
    
    # Chaves de Pagamento (Secretas)
    payment_public_key = models.CharField('Chave Pública de Pagamento', max_length=255, blank=True)
    payment_secret_key = models.CharField('Chave Secreta de Pagamento', max_length=255, blank=True)
    
    # Comissões (Porcentagem)
    taxa_hospedagem = models.DecimalField('Taxa Hospedagem (%)', max_digits=5, decimal_places=2, default=10.00)
    taxa_cinema = models.DecimalField('Taxa Cinema (%)', max_digits=5, decimal_places=2, default=5.00)
    taxa_eventos = models.DecimalField('Taxa Eventos (%)', max_digits=5, decimal_places=2, default=12.00)
    taxa_parques = models.DecimalField('Taxa Parques (%)', max_digits=5, decimal_places=2, default=8.00)
    taxa_gateway_percentual = models.DecimalField('Taxa de Cobrança do Gateway (%)', max_digits=4, decimal_places=2, default=3.00, help_text='Percentual cobrado pelo gateway de pagamento (ex: 3.00 para 3%).')
    visualizacoes = models.PositiveIntegerField(default=0, help_text="Total de visualizações da página principal do Naviê Vibe")

    def save(self, *args, **kwargs):
        if not self.pk and PlataformaConfig.objects.exists():
            raise ValidationError('Só pode existir uma configuração de plataforma.')
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = 'Configuração da Plataforma'
        verbose_name_plural = 'Configurações da Plataforma'
