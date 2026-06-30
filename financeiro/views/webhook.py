import hashlib
import hmac
import json
import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from hoteis.models import Reserva, ReservaLog

def validar_assinatura_mp(request, secret):
    """
    Valida a assinatura x-signature enviada pelo Mercado Pago via HMAC-SHA256.
    """
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    data_id = (request.GET.get("data.id", "") or "").lower()

    if not x_signature:
        return False

    ts = None
    hash_value = None
    for part in x_signature.split(","):
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "ts":
            ts = value
        elif key == "v1":
            hash_value = value

    if not ts or not hash_value:
        return False

    parts = []
    if data_id:
        parts.append(f"id:{data_id}")
    if x_request_id:
        parts.append(f"request-id:{x_request_id}")
    parts.append(f"ts:{ts}")
    manifest = ";".join(parts) + ";"

    computed = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, hash_value)


@csrf_exempt
def view_mp_webhook(request):
    """
    Webhook assíncrono para receber notificações em tempo real do Mercado Pago (Checkout Transparente).
    """
    if request.method != 'POST':
        return HttpResponse("Método não permitido.", status=405)

    # 1. Obter a chave secreta de validação do webhook
    secret = getattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET', '')
    if not secret:
        # Fallback para o Access Token caso segredo do webhook não esteja configurado
        secret = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '')

    # 2. Validar assinatura de segurança
    if secret:
        assinatura_valida = validar_assinatura_mp(request, secret)
        if not assinatura_valida:
            print("Webhook Mercado Pago: Assinatura inválida detectada.", flush=True)
            if not settings.DEBUG:
                return HttpResponse("Assinatura inválida.", status=401)
    else:
        print("Webhook Mercado Pago: Chave secreta de validação ausente nas configurações.", flush=True)

    # 3. Carregar dados do payload
    try:
        payload = json.loads(request.body)
    except Exception as e:
        print(f"Webhook Mercado Pago: Falha ao ler JSON do body: {e}", flush=True)
        # O MP exige resposta 200/201 mesmo em falha de processamento para não retentar indefinidamente
        return HttpResponse("JSON inválido no corpo.", status=200)

    print("Webhook Mercado Pago recebido com payload:", json.dumps(payload, indent=2), flush=True)

    event_type = payload.get('type') or request.GET.get('type')
    data_id = payload.get('data', {}).get('id') or request.GET.get('data.id')

    if not event_type or not data_id:
        print("Webhook Mercado Pago: type ou data.id ausentes.", flush=True)
        return HttpResponse("Dados ausentes.", status=200)

    # 4. Tratar evento do tipo payment
    if event_type == 'payment':
        url_mp = f"https://api.mercadopago.com/v1/payments/{data_id}"
        headers = {
            "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            print(f"Webhook: Consultando pagamento {data_id} no Mercado Pago...", flush=True)
            response = requests.get(url_mp, headers=headers, timeout=15)
            if response.status_code == 200:
                resp_data = response.json()
                status_pagamento = resp_data.get('status')
                status_detail = resp_data.get('status_detail')

                print(f"Webhook: Pagamento {data_id} retornado status={status_pagamento}", flush=True)

                # Localiza a reserva correspondente no banco
                reserva = Reserva.objects.filter(pagamento_id=str(data_id)).first()
                if reserva:
                    status_antigo = reserva.status
                    novo_status = None

                    if status_pagamento in ['approved', 'accredited']:
                        novo_status = 'confirmada'
                    elif status_pagamento in ['rejected', 'cancelled', 'refunded', 'charged_back']:
                        novo_status = 'cancelada'

                    if novo_status and novo_status != status_antigo:
                        reserva.status = novo_status
                        reserva.save()

                        # Gravar logs de auditoria
                        ReservaLog.objects.create(
                            reserva=reserva,
                            acao=f'webhook_pagamento_{status_pagamento}',
                            detalhes=f"Status da reserva atualizado via Webhook do Mercado Pago. De '{status_antigo}' para '{novo_status}'. Detalhe: {status_detail}"
                        )
                        print(f"Webhook: Reserva {reserva.id} atualizada com sucesso de '{status_antigo}' para '{novo_status}'.", flush=True)
                else:
                    print(f"Webhook: Nenhuma reserva local encontrada com pagamento_id={data_id}", flush=True)
            else:
                print(f"Webhook: Erro ao consultar pagamento {data_id} no MP. Status: {response.status_code}", flush=True)
        except Exception as e:
            print(f"Webhook: Exceção ao consultar pagamento no Mercado Pago: {e}", flush=True)

    return HttpResponse("OK", status=200)
