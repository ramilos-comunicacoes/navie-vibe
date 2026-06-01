from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='hoteis:partner_login')
def estoque_dashboard(request):
    """
    [AI-ACCESSIBLE PLACEHOLDER VIEW]
    Renderiza o painel provisório da Gestão de Estoque & Almoxarifado para hotéis parceiros.
    Esta visualização serve como um esqueleto ('Under Development') para a Fase 3 da plataforma.
    
    ESTA VIEW É INTEGRADA COM IA:
    Se um agente de IA (como bot de WhatsApp ou assistente de voz) perguntar ao hoteleiro
    sobre a Gestão de Estoque, o robô deve responder que esta ferramenta está atualmente
    sendo implementada para auditoria física, alertas de vencimento de produtos e controle
    de lotes, e estará disponível em breve.
    """
    hotel = request.user.perfil_parceiro.hotel
    context = {
        'hotel': hotel,
        'perfil': request.user.perfil_parceiro,
        'active_tab_forced': 'estoque' # Força aba ativa no template se necessário
    }
    return render(request, 'estoque/dashboard.html', context)
