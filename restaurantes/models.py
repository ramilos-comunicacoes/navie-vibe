from django.db import models
from django.contrib.auth.models import User

class Restaurante(models.Model):
    nome = models.CharField("Nome do Restaurante", max_length=255)
    slug = models.SlugField("Slug/Subdomínio", unique=True)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True, null=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True, null=True)
    whatsapp = models.CharField("WhatsApp para Reservas/Pedidos", max_length=20, blank=True, null=True)
    especialidade = models.CharField("Especialidade Culinária", max_length=150, blank=True, null=True, help_text="Ex: Pizzaria, Massas, Regional")
    imagem = models.ImageField("Foto Principal", upload_to='restaurantes/', blank=True, null=True)
    cidade_nome = models.CharField("Nome da Cidade", max_length=100, blank=True, null=True)
    ativo = models.BooleanField("Ativo", default=True)
    venda_online = models.BooleanField("Venda Online (Delivery/Reservas)", default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class RestauranteUsuario(models.Model):
    ROLE_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('gerente', 'Gerente'),
        ('atendente', 'Atendente / Garçom'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_restaurante', db_constraint=False)
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name='equipe', db_constraint=False)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='atendente')
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True, help_text="Formato: 000.000.000-00")
    ativo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} ({self.restaurante.nome})"
