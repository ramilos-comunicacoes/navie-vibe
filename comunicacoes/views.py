from django.http import HttpResponse
from hoteis.models import Reserva
from .emails import enviar_email_confirmacao_reserva

def testar_email_reserva(request):
    """
    Endpoint de teste rápido para validar a conexão SMTP e envio de e-mails.
    Pega a reserva mais recente com e-mail e faz o disparo em segundo plano.
    """
    reserva = Reserva.objects.using('hospedagem').exclude(hospede_email__isnull=True).exclude(hospede_email='').first()
    if not reserva:
        return HttpResponse("Nenhuma reserva com e-mail cadastrado encontrada no banco para testes.", status=404)

    # Se passar um e-mail via parâmetro GET (?email=seu-email@teste.com), envia para ele
    email_destino = request.GET.get('email')
    if email_destino:
        reserva.hospede_email = email_destino
        
    # Se a reserva de teste não tiver CPF, injeta um fictício para validação do layout no e-mail
    if not reserva.hospede_cpf:
        reserva.hospede_cpf = "123.456.789-00"

    # Dispara e-mail de teste
    sucesso = enviar_email_confirmacao_reserva(reserva)
    if sucesso:
        return HttpResponse(f"E-mail de confirmação disparado com sucesso em segundo plano para: {reserva.hospede_email}!<br>Consulte a tabela EmailLog no Django Admin para ver o status do envio.")
    else:
        return HttpResponse("Erro ao disparar o e-mail. Verifique os logs do sistema.", status=500)
