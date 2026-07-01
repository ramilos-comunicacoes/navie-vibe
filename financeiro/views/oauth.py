from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import requests
from django.conf import settings
from financeiro.models import MercadoPagoConexao

@login_required
def view_mp_conectar(request):
    """
    Inicia o fluxo OAuth com o Mercado Pago redirecionando o hoteleiro para autorizar o Naviê.
    """
    if not hasattr(request.user, 'perfil_parceiro') or not request.user.perfil_parceiro.hotel:
        messages.error(request, "Acesso restrito apenas para hotéis parceiros.")
        return redirect('hoteis:partner_dashboard')
        
    client_id = getattr(settings, 'MERCADOPAGO_CLIENT_ID', '')
    if not client_id:
        messages.error(request, "Integração do Mercado Pago temporariamente indisponível (client_id ausente).")
        return redirect('hoteis:partner_dashboard')
        
    # Obtém o host de forma dinâmica
    host = request.get_host()
    scheme = 'https' if request.is_secure() else 'http'
    redirect_uri = f"{scheme}://{host}/hospedagens/financeiro/mp/callback/"
    
    # URL de autorização oficial do Mercado Pago
    url_auth = (
        f"https://auth.mercadopago.com/authorization"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&platform_id=mp"
        f"&redirect_uri={redirect_uri}"
    )
    return redirect(url_auth)


@login_required
def view_mp_callback(request):
    """
    Callback do OAuth do Mercado Pago. Recebe o 'code' da autorização e obtém os tokens permanentes.
    """
    if not hasattr(request.user, 'perfil_parceiro') or not request.user.perfil_parceiro.hotel:
        messages.error(request, "Acesso negado.")
        return redirect('hoteis:partner_dashboard')
        
    hotel = request.user.perfil_parceiro.hotel
    empresa = hotel.empresa
    if not empresa:
        messages.error(request, "Nenhuma empresa associada ao hotel logado.")
        return redirect('hoteis:partner_dashboard')
        
    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error_description') or request.GET.get('error') or "Autorização cancelada ou inválida."
        messages.error(request, f"Conexão com Mercado Pago recusada: {error}")
        return redirect('hoteis:partner_dashboard')
        
    client_id = getattr(settings, 'MERCADOPAGO_CLIENT_ID', '')
    client_secret = getattr(settings, 'MERCADOPAGO_CLIENT_SECRET', '')
    
    host = request.get_host()
    scheme = 'https' if request.is_secure() else 'http'
    redirect_uri = f"{scheme}://{host}/hospedagens/financeiro/mp/callback/"
    
    # Solicita token ao Mercado Pago
    url_token = "https://api.mercadopago.com/oauth/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    try:
        response = requests.post(url_token, headers=headers, data=data_payload, timeout=15)
        resp_data = response.json()
        
        if response.status_code != 200:
            error_msg = resp_data.get('message') or resp_data.get('error_description') or 'Erro desconhecido.'
            messages.error(request, f"Erro ao tokenizar conta com Mercado Pago: {error_msg}")
            return redirect('hoteis:partner_dashboard')
            
        access_token = resp_data.get('access_token')
        refresh_token = resp_data.get('refresh_token')
        mp_user_id = resp_data.get('user_id')
        expires_in = resp_data.get('expires_in', 15552000) # Expira em 180 dias por padrão
        
        # Salva ou atualiza a conexão no banco
        conexao, created = MercadoPagoConexao.objects.update_or_create(
            empresa=empresa,
            defaults={
                'mp_user_id': str(mp_user_id),
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_expira_em': timezone.now() + timedelta(seconds=int(expires_in))
            }
        )
        
        messages.success(request, f"Sucesso! Sua conta Mercado Pago foi vinculada ao Naviê Vibe (ID: {mp_user_id}).")
    except Exception as e:
        messages.error(request, f"Falha de comunicação com o Mercado Pago: {str(e)}")
        
    return redirect('hoteis:partner_dashboard')


@login_required
def view_mp_conectar_sandbox(request):
    """
    Simula uma conexão de sandbox Mercado Pago sem passar pelo fluxo real do OAuth (Útil em ambiente de testes/debug)
    """
    # Permite a simulação de sandbox em desenvolvimento (DEBUG=True) ou para superusuários em produção
    if not settings.DEBUG and not request.user.is_superuser:
        messages.error(request, "A conexão simulada só é permitida em ambiente de desenvolvimento ou para administradores (superusuários).")
        return redirect('hoteis:partner_dashboard')
        
    if not hasattr(request.user, 'perfil_parceiro') or not request.user.perfil_parceiro.hotel:
        messages.error(request, "Acesso restrito.")
        return redirect('hoteis:partner_dashboard')
        
    hotel = request.user.perfil_parceiro.hotel
    empresa = hotel.empresa
    if not empresa:
        messages.error(request, "Nenhuma empresa associada ao hotel logado.")
        return redirect('hoteis:partner_dashboard')
        
    # Se as chaves reais estiverem vazias ou ausentes nas configurações do .env da VPS,
    # injeta automaticamente chaves de teste fallback para permitir a simulação do sandbox
    client_id = getattr(settings, 'MERCADOPAGO_CLIENT_ID', '') or '3252967423173872'
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '') or 'TEST-3252967423173872-062915-c69216809f66d9897f68e2949a16c235-1158819914'
        
    expires_in = 15552000 # 180 dias
    
    conexao, created = MercadoPagoConexao.objects.update_or_create(
        empresa=empresa,
        defaults={
            'mp_user_id': str(client_id),
            'access_token': access_token,
            'refresh_token': 'sandbox_refresh_token',
            'token_expira_em': timezone.now() + timedelta(seconds=expires_in)
        }
    )
    
    messages.success(request, "Conexão de testes do Mercado Pago simulada com sucesso!")
    
    if request.headers.get('HX-Request') == 'true':
        from django.http import HttpResponse
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=financeiro&financeiro_tab=mp'
        return response
    return redirect('/hospedagens/sistema/?tab=financeiro&financeiro_tab=mp')
