from django.db import models
from django.contrib.auth.models import User
import uuid

class ClientePerfil(models.Model):
    """
    Database model extending the standard Django User model to store detailed customer profile data
    and legally binding audit records for Terms of Use acceptance.

    PURPOSE FOR AI AGENTS:
    - This model acts as the single source of truth for customer identities on the platform.
    - It holds custom user contact info, address details, and vital legal audit fields.
    - AI systems should query this model when retrieving user-scoped contact details, address strings for mailing/routing,
      or verifying whether a user has legally agreed to the active Terms of Use.

    FIELDS SCHEMA & MEANING:
    - user (OneToOneField -> auth.User): The authenticable Django system user. Related name is 'perfil'.
    - cpf (CharField, 14 chars): Brazilian national tax ID, stored with punctuation (format: XXX.XXX.XXX-XX). Must be unique.
    - telefone (CharField, 20 chars): Contact number / WhatsApp including DDD (format: (XX) XXXXX-XXXX).
    - cep (CharField, 9 chars): Brazilian postal code (format: XXXXX-XXX).
    - endereco (CharField, 255 chars): Street name and type (Avenida, Rua, etc.).
    - numero (CharField, 20 chars): House or apartment number.
    - bairro (CharField, 100 chars): Neighborhood name.
    - cidade (CharField, 100 chars): City name.
    - estado (CharField, 2 chars): State code abbreviation (e.g. CE, SP).
    
    LEGAL AUDITING FIELDS (Read-only after creation):
    - aceite_termos (BooleanField): Explicit consent state of the customer. Must be True for active profiles.
    - data_aceite_termos (DateTimeField): Exact datetime stamp when the user clicked 'Register' and accepted terms.
    - registro_ip (GenericIPAddressField): Captures the client IP (IPv4 or IPv6) at the moment of registration.
    - registro_user_agent (TextField): Device and browser signature string (HTTP_USER_AGENT) collected during registration.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='perfil',
        help_text="O usuário de sistema Django proprietário deste perfil."
    )
    cpf = models.CharField(
        'CPF', 
        max_length=14, 
        unique=True,
        help_text="Cadastro de Pessoas Físicas do cliente. Formato: 000.000.000-00"
    )
    telefone = models.CharField(
        'Telefone / WhatsApp', 
        max_length=20,
        help_text="Número de telefone principal do cliente. Formato: (00) 00000-0000"
    )
    
    # Endereço
    cep = models.CharField(
        'CEP', 
        max_length=9,
        help_text="Código de Endereçamento Postal do local de residência. Formato: 00000-000"
    )
    endereco = models.CharField(
        'Endereço', 
        max_length=255,
        help_text="Nome da rua/avenida e logradouro."
    )
    numero = models.CharField(
        'Número', 
        max_length=20,
        help_text="Número residencial, comercial ou complemento."
    )
    bairro = models.CharField(
        'Bairro', 
        max_length=100,
        help_text="Bairro correspondente do endereço."
    )
    cidade = models.CharField(
        'Cidade', 
        max_length=100,
        help_text="Cidade de residência do cliente."
    )
    estado = models.CharField(
        'Estado (UF)', 
        max_length=2,
        help_text="Sigla de duas letras correspondente ao estado brasileiro (ex: CE)."
    )
 
    # Auditoria Legal
    aceite_termos = models.BooleanField(
        'Aceita Termos de Uso', 
        default=False,
        help_text="Define se o cliente manifestou concordância ativa com os Termos de Uso do Naviê Vibe."
    )
    data_aceite_termos = models.DateTimeField(
        'Data de Aceite', 
        null=True, blank=True,
        help_text="Carimbo de data/hora oficial e imutável registrando quando o aceite ocorreu."
    )
    registro_ip = models.GenericIPAddressField(
        'IP do Registro', 
        null=True, blank=True,
        help_text="Endereço IP (IPv4 ou IPv6) de onde partiu a requisição de cadastro."
    )
    registro_user_agent = models.TextField(
        'User Agent do Registro', 
        null=True, blank=True,
        help_text="Assinatura técnica do navegador e sistema operacional do cliente coletada no cadastro."
    )
 
    class Meta:
        verbose_name = 'Perfil de Cliente'
        verbose_name_plural = 'Perfis de Clientes'
 
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (CPF: {self.cpf})"

class PostMomento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='momentos')
    reserva = models.ForeignKey('hoteis.Reserva', on_delete=models.SET_NULL, null=True, blank=True, related_name='momentos', db_constraint=False)
    estabelecimento_nome = models.CharField(max_length=255, blank=True, null=True) # Ex: Pousada Ramilos Tianguá
    imagem = models.ImageField(upload_to='clientes/momentos/', null=True, blank=True)
    texto = models.TextField(blank=True, null=True)
    avaliacao = models.PositiveSmallIntegerField(default=5, help_text="Nota de 1 a 5 estrelas")
    likes = models.ManyToManyField(User, related_name='momentos_curtidos', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Momento'
        verbose_name_plural = 'Momentos'

    def __str__(self):
        return f"Momento {self.id.hex[:8].upper()} por {self.usuario.username}"

class ComentarioMomento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(PostMomento, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios_momentos')
    texto = models.TextField(max_length=500)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
        verbose_name = 'Comentário de Momento'
        verbose_name_plural = 'Comentários de Momentos'

    def __str__(self):
        return f"Comentário de {self.usuario.username} no Post {self.post.id.hex[:8].upper()}"
