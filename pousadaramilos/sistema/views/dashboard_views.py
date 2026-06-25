from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from sistema.models import Pousada, Quarto, Reserva, TransacaoFinanceira

# ==============================================================================
# HELPER: CONTEXTO MULTI-POUSADA & BRANDING
# Determina qual das 3 pousadas é a ativa no momento para fins de branding (YIQ)
# e filtragem de dados com base nas permissões e sessões de usuário.
# ==============================================================================
def obter_contexto_pousada(request):
    """
    Função utilitária compartilhada para obter a pousada ativa e a lista de pousadas.
    Admins podem alternar entre unidades. Funcionários normais ficam travados na sua unidade.
    """
    pousadas = Pousada.objects.filter(ativo=True)
    pousada_ativa = None
    
    # Regra 1: Funcionários (Gerentes, Recepcionistas, etc.) sempre usam a pousada vinculada
    if request.user.pousada_vinculada:
        pousada_ativa = request.user.pousada_vinculada
    else:
        # Regra 2: Admin global pode alternar via query string ?set_pousada=ID
        set_pousada_id = request.GET.get('set_pousada')
        if set_pousada_id:
            try:
                pousada_ativa = Pousada.objects.get(id=set_pousada_id, ativo=True)
                request.session['active_pousada_id'] = pousada_ativa.id
            except Pousada.DoesNotExist:
                pass
        
        # Regra 3: Se não informou na URL, tenta buscar da sessão
        if not pousada_ativa:
            session_pousada_id = request.session.get('active_pousada_id')
            if session_pousada_id:
                try:
                    pousada_ativa = Pousada.objects.get(id=session_pousada_id, ativo=True)
                except Pousada.DoesNotExist:
                    pass
        
        # Regra 4: Fallback - pega a primeira pousada cadastrada no banco
        if not pousada_ativa and pousadas.exists():
            pousada_ativa = pousadas.first()
            if pousada_ativa:
                request.session['active_pousada_id'] = pousada_ativa.id

    return {
        'active_pousada': pousada_ativa,
        'pousadas_list': pousadas if (request.user.role == 'DIRECAO' or request.user.is_superuser) else []
    }


# ==============================================================================
# VIEW: DASHBOARD PRINCIPAL
# Ponto de entrada operacional (/sistema/). Exibe métricas de ocupação em tempo real.
# ==============================================================================
@login_required(login_url='sistema:login')
def dashboard_view(request):
    """
    Renderiza a visão geral do sistema interno (PMS).
    Calcula taxas de ocupação, quartos por status e reservas ativas na pousada atual.
    """
    # Se for da equipe de serviço/operacional, vai direto pro painel de atividades (Kanban)
    if request.user.role == 'SERVICO':
        return redirect('agenda:painel_atividades')
    # Obtém a pousada de branding e escopo territorial
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']

    # Filtra quartos e dados pela pousada ativa
    if pousada_ativa:
        quartos_qs = Quarto.objects.filter(pousada=pousada_ativa)
        reservas_qs = Reserva.objects.filter(quarto__pousada=pousada_ativa)
        financeiro_qs = TransacaoFinanceira.objects.filter(pousada=pousada_ativa)
    else:
        quartos_qs = Quarto.objects.none()
        reservas_qs = Reserva.objects.none()
        financeiro_qs = TransacaoFinanceira.objects.none()

    # Métricas de Quartos
    total_quartos = quartos_qs.count()
    quartos_livres = quartos_qs.filter(status='LIVRE').count()
    quartos_ocupados = quartos_qs.filter(status='OCUPADO').count()
    quartos_sujos = quartos_qs.filter(status='SUJO').count()
    quartos_manutencao = quartos_qs.filter(status='MANUTENCAO').count()

    # Cálculo percentual de ocupação em tempo real
    taxa_ocupacao = 0
    if total_quartos > 0:
        taxa_ocupacao = round((quartos_ocupados / total_quartos) * 100, 1)

    # Últimas 5 reservas registradas
    ultimas_reservas = reservas_qs.select_related('cliente', 'quarto').order_by('-data_criacao')[:5]

    # Contexto unificado
    context = {
        **pousada_ctx, # Inclui active_pousada e pousadas_list
        'quartos_qs': quartos_qs, # Adicionado para corrigir a VariableDoesNotExist no template
        'total_quartos': total_quartos,
        'quartos_livres': quartos_livres,
        'quartos_ocupados': quartos_ocupados,
        'quartos_sujos': quartos_sujos,
        'quartos_manutencao': quartos_manutencao,
        'taxa_ocupacao': taxa_ocupacao,
        'ultimas_reservas': ultimas_reservas,
    }

    return render(request, 'sistema/dashboard.html', context)
