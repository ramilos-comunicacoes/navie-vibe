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
    
    logo = models.ImageField(upload_to='empresas/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='empresas/banners/', null=True, blank=True)
    
    cor_primaria = models.CharField('Cor da Marca (Hex)', max_length=7, default='#1e3a8a')
    
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
    
    # Status e Datas
    ativa = models.BooleanField(default=True)
    destaque = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    visualizacoes = models.PositiveIntegerField(default=0, help_text="Total de visualizações da página da empresa")

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
