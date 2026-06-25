from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.utils import timezone
from sistema.models import Quarto, TarefaLimpeza, TarefaManutencao
from agenda.models import Atividade
from sistema.decorators import servico_required
from sistema.views.dashboard_views import obter_contexto_pousada

@servico_required
def servico_painel(request):
    """
    Painel unificado e mobile-first para a equipe de Serviço (Limpeza e Manutenção).
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if pousada_ativa:
        # Busca tarefas ativas (Pendente ou Em Andamento)
        limpezas = TarefaLimpeza.objects.filter(
            quarto__pousada=pousada_ativa,
            status__in=['PENDENTE', 'EM_ANDAMENTO']
        ).select_related('quarto', 'quarto__categoria').order_by('status', 'quarto__numero')
        
        manutencoes = TarefaManutencao.objects.filter(
            quarto__pousada=pousada_ativa,
            status__in=['PENDENTE', 'EM_ANDAMENTO']
        ).select_related('quarto', 'quarto__categoria').order_by('-prioridade', 'data_criacao')
        
        # Atividades extras atribuídas a este usuário (não concluídas)
        tarefas_extras = Atividade.objects.filter(
            usuario=request.user,
            pousada=pousada_ativa
        ).exclude(status='done').select_related('quarto', 'hospede', 'reserva').order_by('data_vencimento', '-prioridade')
    else:
        limpezas = TarefaLimpeza.objects.none()
        manutencoes = TarefaManutencao.objects.none()
        tarefas_extras = Atividade.objects.none()
        
    context = {
        **pousada_ctx,
        'limpezas': limpezas,
        'manutencoes': manutencoes,
        'tarefas_extras': tarefas_extras,
    }
    
    return render(request, 'sistema/servico_painel.html', context)

@servico_required
def servico_limpeza_status(request, tarefa_id):
    """
    Endpoint HTMX para transicionar status de limpeza:
    - PENDENTE -> EM_ANDAMENTO (atribui camareira)
    - EM_ANDAMENTO -> CONCLUIDA (define data de conclusão e libera o quarto)
    """
    tarefa = get_object_or_404(TarefaLimpeza, id=tarefa_id)
    
    if tarefa.status == 'PENDENTE':
        tarefa.status = 'EM_ANDAMENTO'
        tarefa.camareira = request.user
        tarefa.save()
        # Garante que o quarto físico está marcado como SUJO
        tarefa.quarto.status = 'SUJO'
        tarefa.quarto.save()
    elif tarefa.status == 'EM_ANDAMENTO':
        tarefa.status = 'CONCLUIDA'
        tarefa.data_conclusao = timezone.now()
        tarefa.save()
        # Libera o quarto físico
        tarefa.quarto.status = 'LIVRE'
        tarefa.quarto.save()
        
    if request.headers.get('HX-Request'):
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response
        
    return redirect('sistema:servico_painel')

@servico_required
def servico_manutencao_status(request, chamado_id):
    """
    Endpoint HTMX para transicionar status de manutenção:
    - PENDENTE -> EM_ANDAMENTO (atribui técnico, coloca quarto em MANUTENCAO)
    - EM_ANDAMENTO -> RESOLVIDA (salva a solução aplicada e libera o quarto)
    """
    chamado = get_object_or_404(TarefaManutencao, id=chamado_id)
    
    if chamado.status == 'PENDENTE':
        chamado.status = 'EM_ANDAMENTO'
        chamado.tecnico = request.user
        chamado.save()
        # Coloca o quarto físico em manutenção
        chamado.quarto.status = 'MANUTENCAO'
        chamado.quarto.save()
    elif chamado.status == 'EM_ANDAMENTO':
        solucao = request.POST.get('solucao_aplicada', '').strip()
        chamado.status = 'RESOLVIDA'
        chamado.solucao_aplicada = solucao
        chamado.save()
        # Libera o quarto de volta para LIVRE (ou SUJO se precisar de limpeza, mas LIVRE é o padrão reativo)
        chamado.quarto.status = 'LIVRE'
        chamado.quarto.save()
        
    if request.headers.get('HX-Request'):
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response
        
    return redirect('sistema:servico_painel')

@servico_required
def servico_completar_atividade(request, tarefa_id):
    """
    Marca uma atividade extra/gerencial como concluída pelo funcionário logado.
    """
    tarefa = get_object_or_404(Atividade, id=tarefa_id, usuario=request.user)
    tarefa.status = 'done'
    tarefa.save()
    
    if request.headers.get('HX-Request'):
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response
        
    return redirect('sistema:servico_painel')
