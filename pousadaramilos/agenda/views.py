from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db import models
import datetime

from sistema.views.dashboard_views import obter_contexto_pousada
from sistema.decorators import portaria_required
from .models import Atividade
from .forms import AtividadeForm

@login_required(login_url='sistema:login')
def painel_atividades(request):
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if not pousada_ativa:
        return render(request, 'agenda/index.html', {
            **pousada_ctx,
            'erro': 'Nenhuma pousada ativa selecionada.'
        })
        
    periodo = request.GET.get('periodo', 'tudo')
    atividades = Atividade.objects.filter(pousada=pousada_ativa)
    
    now = timezone.now()
    today = now.date()
    
    # Filtragem por período
    if periodo == 'hoje':
        atividades = atividades.filter(data_vencimento__date=today)
    elif periodo == 'semana':
        proximos_7_dias = today + datetime.timedelta(days=7)
        atividades = atividades.filter(data_vencimento__date__range=[today, proximos_7_dias])
    elif periodo == 'mes':
        proximos_30_dias = today + datetime.timedelta(days=30)
        atividades = atividades.filter(data_vencimento__date__range=[today, proximos_30_dias])
        
    # Separação das colunas
    # Atrasadas: não concluídas e data limite < agora
    atrasadas = atividades.filter(data_vencimento__lt=now).exclude(status='done')
    
    # A Fazer: status 'todo' e (data limite nula ou >= agora)
    todo = atividades.filter(status='todo').filter(
        models.Q(data_vencimento__isnull=True) | models.Q(data_vencimento__gte=now)
    )
    
    # Em Andamento: status 'doing' e (data limite nula ou >= agora)
    doing = atividades.filter(status='doing').filter(
        models.Q(data_vencimento__isnull=True) | models.Q(data_vencimento__gte=now)
    )
    
    # Concluído: status 'done'
    done = atividades.filter(status='done')
    
    context = {
        **pousada_ctx,
        'periodo': periodo,
        'atrasadas': atrasadas,
        'todo': todo,
        'doing': doing,
        'done': done,
        'total_atividades': atividades.count()
    }
    
    if request.headers.get('HX-Request') and not request.headers.get('HX-Target') == 'modal-container':
        context['is_htmx'] = True
        return render(request, 'agenda/partials/kanban.html', context)
        
    return render(request, 'agenda/index.html', context)

@login_required(login_url='sistema:login')
def nova_tarefa(request):
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if request.method == 'POST':
        form = AtividadeForm(request.POST, pousada=pousada_ativa)
        if form.is_valid():
            atividade = form.save(commit=False)
            atividade.pousada = pousada_ativa
            if not form.cleaned_data.get('usuario'):
                atividade.usuario = request.user
            atividade.save()
            
            response = HttpResponse()
            response['HX-Trigger'] = 'tarefaModificada'
            return response
        else:
            return render(request, 'agenda/partials/modal_tarefa.html', {
                'form': form,
                'pousada': pousada_ativa
            })
            
    form = AtividadeForm(pousada=pousada_ativa)
    return render(request, 'agenda/partials/modal_tarefa.html', {
        'form': form,
        'pousada': pousada_ativa
    })

@login_required(login_url='sistema:login')
def editar_tarefa(request, pk):
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    atividade = get_object_or_404(Atividade, pk=pk, pousada=pousada_ativa)
    
    if request.method == 'POST':
        form = AtividadeForm(request.POST, instance=atividade, pousada=pousada_ativa)
        if form.is_valid():
            form.save()
            response = HttpResponse()
            response['HX-Trigger'] = 'tarefaModificada'
            return response
        else:
            return render(request, 'agenda/partials/modal_tarefa.html', {
                'form': form,
                'atividade': atividade,
                'pousada': pousada_ativa
            })
            
    form = AtividadeForm(instance=atividade, pousada=pousada_ativa)
    return render(request, 'agenda/partials/modal_tarefa.html', {
        'form': form,
        'atividade': atividade,
        'pousada': pousada_ativa
    })

@login_required(login_url='sistema:login')
@require_POST
def mudar_status(request, pk):
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    atividade = get_object_or_404(Atividade, pk=pk, pousada=pousada_ativa)
    
    novo_status = request.POST.get('status')
    if novo_status in dict(Atividade.STATUS_CHOICES):
        atividade.status = novo_status
        # Se for movido de ou para atrasado, recalcula/salva de acordo
        atividade.save()
        
        if request.headers.get('HX-Request'):
            return render(request, 'agenda/partials/card_tarefa.html', {'atividade': atividade})
            
    return HttpResponse(status=200)

@login_required(login_url='sistema:login')
@require_POST
def deletar_tarefa(request, pk):
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    atividade = get_object_or_404(Atividade, pk=pk, pousada=pousada_ativa)
    atividade.delete()
    
    response = HttpResponse()
    response['HX-Trigger'] = 'tarefaModificada'
    return response
