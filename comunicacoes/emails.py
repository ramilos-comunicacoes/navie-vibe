import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import EmailLog

def _enviar_email_thread(reserva, destinatario, assunto, html_content, text_content):
    """
    Função interna executada em segundo plano (Thread) para realizar o envio SMTP
    e registrar o status de auditoria no EmailLog.
    """
    try:
        remetente = settings.DEFAULT_FROM_EMAIL
        email = EmailMultiAlternatives(assunto, text_content, remetente, [destinatario])
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        # Registra sucesso
        EmailLog.objects.create(
            reserva=reserva,
            destinatario=destinatario,
            assunto=assunto,
            status='sucesso'
        )
    except Exception as e:
        # Registra falha com a mensagem de erro
        EmailLog.objects.create(
            reserva=reserva,
            destinatario=destinatario,
            assunto=assunto,
            status='falha',
            erro_mensagem=str(e)
        )

def enviar_email_confirmacao_reserva(reserva):
    """
    Inicia o envio do e-mail de comprovante/voucher de confirmação de reserva
    em segundo plano (Thread) para não atrasar a resposta da requisição.
    """
    if not reserva.hospede_email:
        # Se a reserva não tem e-mail de contato do hóspede, gera um log de falha preventivo
        EmailLog.objects.create(
            reserva=reserva,
            destinatario="sem-email@cadastro.com",
            assunto=f"Comprovante de Reserva #{reserva.id}",
            status='falha',
            erro_mensagem="Hóspede não possui endereço de e-mail cadastrado."
        )
        return False
        
    assunto = f"Reserva Confirmada! Seu voucher #{str(reserva.id)[:6].upper()} - Naviê Vibe"
    
    # Renderiza o template de e-mail HTML
    try:
        html_content = render_to_string('comunicacoes/emails/confirmacao_reserva.html', {
            'reserva': reserva,
            'hotel': reserva.unidade.quarto.hotel,
        })
        text_content = strip_tags(html_content)
    except Exception as e:
        # Loga falha se der erro na renderização do template
        EmailLog.objects.create(
            reserva=reserva,
            destinatario=reserva.hospede_email,
            assunto=assunto,
            status='falha',
            erro_mensagem=f"Erro ao renderizar template de e-mail: {str(e)}"
        )
        return False

    # Dispara em segundo plano (Thread)
    thread = threading.Thread(
        target=_enviar_email_thread,
        args=(reserva, reserva.hospede_email, assunto, html_content, text_content)
    )
    thread.daemon = True
    thread.start()
    return True
