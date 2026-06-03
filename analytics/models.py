from django.db import models
from django.contrib.auth.models import User

class UserInteraction(models.Model):
    """
    Rastreia visualizações de página, cliques e tempo ativo de navegação em qualquer vertical.
    """
    INTERACTION_CHOICES = [
        ('page_view', 'Visualização de Página'),
        ('item_detail', 'Visualização de Detalhe de Item'),
        ('cart_add', 'Adição ao Carrinho'),
        ('cart_remove', 'Remoção do Carrinho'),
        ('checkout_start', 'Início de Checkout'),
        ('checkout_success', 'Finalização de Compra'),
    ]

    tracker_id = models.CharField(max_length=255, db_index=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='interacoes_analytics', db_constraint=False)
    
    interaction_type = models.CharField(max_length=50, choices=INTERACTION_CHOICES, default='page_view', db_index=True)
    category = models.CharField(max_length=50, blank=True, null=True, db_index=True, help_text="Ex: hospedagem, cinema, restaurante, parque")
    item_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="ID do recurso específico (ex: ID do quarto ou filme)")
    parent_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="ID do recurso pai (ex: ID do hotel ou do cinema)")
    
    url = models.TextField(help_text="URL completa da página")
    path = models.CharField(max_length=255, help_text="Caminho relativo da requisição")
    time_spent = models.PositiveIntegerField(default=0, help_text="Tempo ativamente gasto na página em segundos")
    metadata = models.JSONField(default=dict, blank=True, help_text="Metadados extras da interação (ex: filtros de busca)")
    
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criado_em']
        db_table = 'analytics_userinteraction'

    def __str__(self):
        user_str = self.usuario.username if self.usuario else f"Tracker {self.tracker_id[:8]}"
        category_str = f" [{self.category}]" if self.category else ""
        return f"{user_str} - {self.interaction_type}{category_str} em {self.path} ({self.time_spent}s)"


class CarrinhoStatus(models.Model):
    """
    Rastreia itens adicionados ao carrinho que foram ou não recuperados (comprados).
    Serve para detecção de carrinho abandonado em qualquer vertical.
    """
    tracker_id = models.CharField(max_length=255, db_index=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='carrinhos_analytics', db_constraint=False)
    
    category = models.CharField(max_length=50, db_index=True, help_text="Ex: hospedagem, cinema, restaurante")
    item_id = models.CharField(max_length=100, db_index=True, help_text="ID do item no carrinho")
    quantidade = models.PositiveIntegerField(default=1)
    
    recuperado = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Detalhes específicos (datas de check-in, sessões, ingressos)")
    
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        db_table = 'analytics_carrinhostatus'

    def __str__(self):
        user_str = self.usuario.username if self.usuario else f"Tracker {self.tracker_id[:8]}"
        status_str = "Recuperado" if self.recuperado else "Abandonado"
        return f"Carrinho {status_str} ({self.category}) - {user_str} - Item {self.item_id}"


class RegistroConsumo(models.Model):
    """
    Registra consumos e compras locais efetuadas pelos clientes de forma unificada.
    Alimenta o motor de recomendação baseado no consumo histórico de produtos/serviços.
    """
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consumos_analytics', db_constraint=False)
    tracker_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    
    category = models.CharField(max_length=50, db_index=True, help_text="Ex: hospedagem (frigobar/quarto), cinema, restaurante")
    item_id = models.CharField(max_length=100, db_index=True, help_text="ID do produto/serviço consumido")
    nome = models.CharField(max_length=255, help_text="Nome legível do produto/serviço")
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantidade = models.PositiveIntegerField(default=1)
    
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criado_em']
        db_table = 'analytics_registroconsumo'

    def __str__(self):
        user_str = self.usuario.username if self.usuario else f"Tracker {self.tracker_id[:8]}" if self.tracker_id else "Anônimo"
        return f"Consumo {self.category} - {user_str}: {self.quantidade}x {self.nome} (R$ {self.preco})"
