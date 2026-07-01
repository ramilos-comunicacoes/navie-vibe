from django.db import models
from django.contrib.auth.models import User

class Restaurante(models.Model):
    nome = models.CharField("Nome do Restaurante", max_length=255)
    slug = models.SlugField("Slug/Subdomínio", unique=True)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True, null=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True, null=True)
    whatsapp = models.CharField("WhatsApp para Reservas/Pedidos (Público)", max_length=20, blank=True, null=True)
    whatsapp_privado = models.CharField("WhatsApp Privado (Contato Naviê)", max_length=20, blank=True, null=True)
    email_contato = models.EmailField("E-mail Público / Contato", blank=True, null=True)
    instagram = models.CharField("Instagram (URL)", max_length=255, blank=True, null=True)
    especialidade = models.CharField("Especialidade Culinária", max_length=150, blank=True, null=True, help_text="Ex: Pizzaria, Massas, Regional")
    imagem = models.ImageField("Foto Principal", upload_to='restaurantes/', blank=True, null=True)
    cidade_nome = models.CharField("Nome da Cidade", max_length=100, blank=True, null=True)
    ativo = models.BooleanField("Ativo", default=True)
    venda_online = models.BooleanField("Venda Online (Delivery/Reservas)", default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Branding
    descricao = models.TextField("Descrição / Slogan", blank=True, null=True, help_text="Aparece no Hero da página pública")
    logo = models.ImageField("Logo", upload_to='restaurantes/logos/', blank=True, null=True)
    banner = models.ImageField("Banner / Hero", upload_to='restaurantes/banners/', blank=True, null=True)
    cor_primaria = models.CharField("Cor Primária (Hex)", max_length=7, default='#e11d48', blank=True)
    cor_secundaria = models.CharField("Cor Secundária (Hex)", max_length=7, default='#f97316', blank=True)

    # Hero
    hero_tipo = models.CharField("Tipo do Hero", max_length=10, choices=[('imagem','Imagem'),('video','Vídeo')], default='imagem')
    hero_video = models.FileField("Vídeo do Hero", upload_to='restaurantes/videos/', blank=True, null=True)

    # Geolocalização
    latitude = models.FloatField("Latitude", blank=True, null=True)
    longitude = models.FloatField("Longitude", blank=True, null=True)

    # Seção Sobre
    sobre_titulo = models.CharField("Título da Seção Sobre", max_length=150, blank=True, null=True)
    sobre_texto = models.TextField("Texto da Seção Sobre", blank=True, null=True)
    sobre_banner = models.ImageField("Imagem/Foto da Seção Sobre", upload_to='restaurantes/sobre/', blank=True, null=True)
    sobre_video = models.FileField("Vídeo da Seção Sobre", upload_to='restaurantes/sobre/', blank=True, null=True)
    sobre_midia_tipo = models.CharField("Tipo de Mídia do Sobre", max_length=10, choices=[('imagem','Imagem'),('video','Vídeo')], default='imagem')
    sobre_cor_fundo = models.CharField("Cor de Fundo da Seção Sobre (Hex)", max_length=7, default='#f8fafc', blank=True)
    sobre_cor_texto = models.CharField("Cor do Texto da Seção Sobre (Hex)", max_length=7, default='#0f172a', blank=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ['nome']

    @property
    def slug_normalized(self):
        return self.slug.replace('-', '').replace('_', '')

    def save(self, *args, **kwargs):
        # Só extrai e define cores automaticamente se for a primeira criação (cor_primaria default)
        # ou se cor_primaria estiver em branco.
        if self.logo and (not self.cor_primaria or self.cor_primaria == '#e11d48'):
            try:
                from PIL import Image
                import math
                
                # Abre e converte a imagem
                img = Image.open(self.logo)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img = img.copy()
                img.thumbnail((60, 60))
                
                # Coleta cores válidas
                pixels = list(img.getdata())
                valid_colors = []
                for r, g, b in pixels:
                    yiq = (r * 299 + g * 587 + b * 114) / 1000
                    avg = (r + g + b) / 3
                    variance = ((r - avg)**2 + (g - avg)**2 + (b - avg)**2) / 3
                    std = math.sqrt(variance)
                    
                    # Evita brancos, pretos e cinzas puros para obter cores vivas
                    if 35 < yiq < 220 and std > 15:
                        valid_colors.append((r, g, b, std))
                
                if valid_colors:
                    # Ordena por maior desvio padrão (cor mais viva/saturada)
                    valid_colors.sort(key=lambda item: item[3], reverse=True)
                    prim = valid_colors[0]
                    self.cor_primaria = '#{:02x}{:02x}{:02x}'.format(prim[0], prim[1], prim[2])
                    
                    # Acha secundária que seja diferente da primária
                    sec = None
                    for r, g, b, std in valid_colors:
                        dist = math.sqrt((prim[0] - r)**2 + (prim[1] - g)**2 + (prim[2] - b)**2)
                        if dist > 80:
                            sec = (r, g, b)
                            break
                    if sec:
                        self.cor_secundaria = '#{:02x}{:02x}{:02x}'.format(sec[0], sec[1], sec[2])
                    else:
                        self.cor_secundaria = '#{:02x}{:02x}{:02x}'.format(255 - prim[0], 255 - prim[1], 255 - prim[2])
            except Exception as e:
                print("Erro ao extrair cores da logo:", str(e))
                
        super().save(*args, **kwargs)

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


class RestauranteAtracao(models.Model):
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name='atracoes', db_constraint=False)
    dia = models.CharField("Dia da Atração", max_length=100, help_text="Ex: Sábado, 28/06, Todos os dias")
    titulo = models.CharField("Título da Atração", max_length=255)
    texto = models.TextField("Descrição da Atração")
    imagem = models.ImageField("Imagem da Atração", upload_to='restaurantes/atracoes/', blank=True, null=True)
    video = models.FileField("Vídeo da Atração", upload_to='restaurantes/atracoes/', blank=True, null=True)
    midia_tipo = models.CharField("Tipo de Mídia", max_length=10, choices=[('imagem','Imagem'),('video','Vídeo')], default='imagem')
    cor_fundo = models.CharField("Cor de Fundo (Hex)", max_length=7, default='#0f172a', blank=True)
    cor_texto = models.CharField("Cor do Texto (Hex)", max_length=7, default='#ffffff', blank=True)
    data = models.DateField("Data da Atração", null=True, blank=True)
    horario = models.TimeField("Horário da Atração", null=True, blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Atração do Restaurante"
        verbose_name_plural = "Atrações do Restaurante"
        ordering = ['data', 'horario', '-criado_em']

    def __str__(self):
        return f"{self.titulo} ({self.dia}) - {self.restaurante.nome}"
