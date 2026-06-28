from django.db import models

class Restaurante(models.Model):
    nome = models.CharField("Nome do Restaurante", max_length=255)
    slug = models.SlugField("Slug/Subdomínio", unique=True)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True, null=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True, null=True)
    whatsapp = models.CharField("WhatsApp para Reservas/Pedidos", max_length=20, blank=True, null=True)
    ativo = models.BooleanField("Ativo", default=True)
    venda_online = models.BooleanField("Venda Online (Delivery/Reservas)", default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ['nome']

    def __str__(self):
        return self.nome
