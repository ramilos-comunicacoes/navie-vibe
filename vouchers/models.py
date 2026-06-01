from django.db import models
from django.contrib.auth.models import User
import uuid
from core.models import Empresa

class Voucher(models.Model):
    TIPO_CHOICES = [
        ('hospedagem', 'Hospedagem (Quarto/Chalé)'),
        ('show', 'Shows & Eventos (Ingresso)'),
        ('cinema', 'Ciné Naviê (Bilhete)'),
        ('parques', 'Parques e Day Use'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_seguro = models.CharField('Código Seguro Hash', max_length=100, unique=True, db_index=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='vouchers_emitidos')
    tipo = models.CharField('Tipo de Voucher', max_length=20, choices=TIPO_CHOICES)
    
    # Chave lógica polimórfica (referencia o ID da Reserva, do Ingresso do Show ou do Cinema)
    # db_constraint=False previne erros de migração cross-database do Django
    object_id = models.CharField('ID do Objeto Relacionado', max_length=100, db_index=True)
    
    # Status e Auditoria de Uso
    utilizado = models.BooleanField('Já Utilizado?', default=False, db_index=True)
    utilizado_em = models.DateTimeField('Utilizado em', null=True, blank=True)
    utilizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_validados')
    
    # Metadados rápidos de apresentação para a portaria (Cache Blindado)
    titulo_exibicao = models.CharField('Título Principal', max_length=255) # Ex: Suite Luxo 101, Ingresso VIP Frontstage
    subtitulo_exibicao = models.CharField('Subtítulo / Empresa', max_length=255) # Ex: Pousada da Serra, Ibiapaba Rock Fest
    nome_beneficiario = models.CharField('Nome do Beneficiário', max_length=255)
    documento_beneficiario = models.CharField('Documento Ocultado', max_length=50) # Ex: ***.452.990-**
    
    # Metadados complementares (JSON flexível para acomodar datas, assentos, etc.)
    detalhes_json = models.JSONField('Metadados Adicionais', default=dict, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Voucher Universal'
        verbose_name_plural = 'Vouchers Universais'
        ordering = ['-criado_em']

    def __str__(self):
        status = "UTILIZADO" if self.utilizado else "ATIVO"
        return f"Voucher #{str(self.id)[:8].upper()} - {self.get_tipo_display()} ({status})"
