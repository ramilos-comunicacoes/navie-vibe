from django.db import models
from django.conf import settings

class Atividade(models.Model):
    STATUS_CHOICES = (
        ('todo', 'A Fazer'),
        ('doing', 'Em Andamento'),
        ('done', 'Concluído'),
    )
    
    PRIORIDADE_CHOICES = (
        ('baixa', 'Baixa'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
    )

    titulo = models.CharField(max_length=200, verbose_name="Título da Atividade")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição/Anotações")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='normal')
    
    data_vencimento = models.DateTimeField(blank=True, null=True, verbose_name="Data e Hora limite")
    lembrete = models.DateTimeField(blank=True, null=True, verbose_name="Lembrar em")
    
    # Responsável
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='atividades',
        verbose_name="Responsável"
    )
    
    # Tenants e Vínculos específicos da Pousada
    pousada = models.ForeignKey(
        'sistema.Pousada', 
        on_delete=models.CASCADE, 
        related_name='atividades',
        verbose_name="Pousada"
    )
    quarto = models.ForeignKey(
        'sistema.Quarto', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='atividades',
        verbose_name="Quarto / Chalé"
    )
    hospede = models.ForeignKey(
        'sistema.Cliente', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='atividades',
        verbose_name="Hóspede"
    )
    reserva = models.ForeignKey(
        'sistema.Reserva', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='atividades',
        verbose_name="Reserva"
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'atividades_atividade'
        ordering = ['data_vencimento', '-prioridade']
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'

    def __str__(self):
        return f"{self.titulo} - {self.get_status_display()}"
        
    @property
    def is_atrasada(self):
        from django.utils import timezone
        if self.data_vencimento and self.status != 'done':
            return timezone.now() > self.data_vencimento
        return False
