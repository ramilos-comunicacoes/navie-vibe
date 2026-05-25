from django.db import models
from django.contrib.auth.models import User
import uuid

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
    empresa = models.OneToOneField(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='perfil_hospedagem',
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
    
    status = models.CharField(max_length=50, default='ativo', choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')])
    destaque = models.BooleanField(default=False)
    
    data_inicio = models.DateField(null=True, blank=True) # Prazo de estadia/evento se houver
    horario_inicio = models.TimeField(null=True, blank=True)
    
    # Configurações & Branding do Site/Sistema
    cor_primaria = models.CharField(max_length=7, default='#f97316', help_text="Cor primária em formato Hexadecimal (ex: #f97316)")
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
    logo = models.ImageField(upload_to='hoteis/logos/', null=True, blank=True, help_text="Logo oficial da pousada")
    foto_fundo = models.ImageField(upload_to='hoteis/fundos/', null=True, blank=True, help_text="Imagem de fundo para o modo Glassmorphism")
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, help_text="Slug da URL customizada (ex: pousadaramilostiangua)")


    
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
    descricao = models.CharField(max_length=255, blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    
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
    """Representa a sala física real de uma categoria de quarto, ex: Quarto 101, Chale 2"""
    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE, related_name='unidades')
    identificador = models.CharField(max_length=50, help_text="Ex: 101, Chale 01, Deck Master")
    ativa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.identificador} ({self.quarto.nome})"

class Reserva(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reservas', db_constraint=False)
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.PROTECT, related_name='reservas')
    data_checkin = models.DateField()
    data_checkout = models.DateField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Reserva #{self.id} - {self.unidade.identificador}"

class BloqueioQuarto(models.Model):
    """Permite ao hotel bloquear datas por manutenção ou indisponibilidade"""
    unidade = models.ForeignKey(UnidadeQuarto, on_delete=models.CASCADE, related_name='bloqueios')
    data_inicio = models.DateField()
    data_fim = models.DateField()
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='todo')
    data_vencimento = models.DateField(blank=True, null=True)
    
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

