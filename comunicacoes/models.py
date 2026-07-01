from django.db import models

class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('sucesso', 'Sucesso'),
        ('falha', 'Falha'),
    ]

    reserva = models.ForeignKey(
        'hoteis.Reserva', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='email_logs',
        help_text="Reserva associada a este e-mail (opcional)"
    )
    destinatario = models.EmailField(max_length=254, help_text="Endereço de e-mail do destinatário")
    assunto = models.CharField(max_length=255, help_text="Assunto do e-mail")
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='sucesso',
        help_text="Status do envio do e-mail"
    )
    erro_mensagem = models.TextField(
        null=True, 
        blank=True, 
        help_text="Detalhes do erro caso o envio tenha falhado"
    )
    criado_em = models.DateTimeField(auto_now_add=True, help_text="Data e hora do disparo do e-mail")

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Log de E-mail'
        verbose_name_plural = 'Logs de E-mails'

    def __str__(self):
        return f"{self.assunto} -> {self.destinatario} ({self.status})"
