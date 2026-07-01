from django.contrib import admin
from .models import EmailLog

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'assunto', 'destinatario', 'status', 'criado_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('destinatario', 'assunto', 'erro_mensagem')
    readonly_fields = ('id', 'assunto', 'destinatario', 'status', 'erro_mensagem', 'criado_em', 'reserva')
    
    def has_add_permission(self, request):
        return False  # Logs não devem ser criados manualmente no admin
