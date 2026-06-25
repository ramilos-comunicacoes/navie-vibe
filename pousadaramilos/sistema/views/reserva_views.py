from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from sistema.models import Pousada, CategoriaQuarto, Quarto, Reserva, HospedeReserva, VeiculoReserva, TarefaLimpeza, ReservaLog, BloqueioQuarto, DocumentoHospede, TransacaoFinanceira
from sistema.views.dashboard_views import obter_contexto_pousada
from sistema.decorators import portaria_required

def obter_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=None):
    """
    Retorna um dicionário JSON contendo as datas ocupadas e bloqueadas por quarto.
    Estrutura: { 'quarto_id': ['2026-06-11', '2026-06-12', ...] }
    """
    import json
    from collections import defaultdict
    from datetime import timedelta
    
    indisponibilidades = defaultdict(list)
    
    if not pousada_ativa:
        return json.dumps({})
        
    # 1. Busca todas as reservas ativas da pousada (excluindo as canceladas)
    reservas = Reserva.objects.filter(
        quarto__pousada=pousada_ativa
    ).exclude(status='CANCELADA')
    
    if reserva_id_excluir:
        reservas = reservas.exclude(id=reserva_id_excluir)
        
    for r in reservas:
        data_atual = r.data_checkin
        while data_atual < r.data_checkout:
            indisponibilidades[str(r.quarto_id)].append(data_atual.strftime('%Y-%m-%d'))
            data_atual += timedelta(days=1)
            
    # 2. Busca todos os bloqueios de quarto ativos da pousada
    bloqueios = BloqueioQuarto.objects.filter(
        quarto__pousada=pousada_ativa
    )
    
    for b in bloqueios:
        data_atual = b.data_inicio
        while data_atual <= b.data_fim:
            indisponibilidades[str(b.quarto_id)].append(data_atual.strftime('%Y-%m-%d'))
            data_atual += timedelta(days=1)
            
    return json.dumps(indisponibilidades)

@portaria_required
def partner_reserva_list(request):
    """
    Rende a página base B2B de Reservas (PMS) com filtros e KPIs iniciais.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if not pousada_ativa:
        return redirect('sistema:dashboard')
        
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    
    # Filtro padrão de período: Hoje até +30 dias
    today = timezone.localdate()
    data_inicio = today.strftime('%Y-%m-%d')
    data_fim = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    
    context = {
        **pousada_ctx,
        'categorias': categorias,
        'default_inicio': data_inicio,
        'default_fim': data_fim,
    }
    return render(request, 'sistema/reservas_list.html', context)

@portaria_required
def partner_reserva_grid(request):
    """
    Retorna o fragmento HTML (Grid PMS) contendo o mapa horizontal de ocupação de cabanas.
    Alimentado via HTMX.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    categoria_id = request.GET.get('categoria')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    
    today = timezone.localdate()
    
    # Validação de Datas
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else today
    except ValueError:
        data_inicio = today
        
    try:
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else today + timedelta(days=30)
    except ValueError:
        data_fim = today + timedelta(days=30)
        
    # Busca Categorias ativas
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    
    # Seleção de Categoria
    categoria = None
    if categoria_id and categoria_id != 'todas':
        try:
            categoria = CategoriaQuarto.objects.get(id=categoria_id, pousada=pousada_ativa)
        except CategoriaQuarto.DoesNotExist:
            pass
        
    # Busca quartos físicos correspondentes
    if categoria:
        quartos = Quarto.objects.filter(categoria=categoria, pousada=pousada_ativa)
    else:
        quartos = Quarto.objects.filter(pousada=pousada_ativa)
        
    # Mapeia quartos com suas reservas no período
    unidades_data = []
    for q in quartos:
        reservas = Reserva.objects.filter(
            quarto=q,
            data_checkin__lt=data_fim,
            data_checkout__gt=data_inicio
        ).exclude(status='CANCELADA').order_by('data_checkin')
        
        unidades_data.append({
            'unidade': q,
            'reservas': reservas
        })
        
    # Calcula KPIs Operacionais
    reservas_periodo = Reserva.objects.filter(
        quarto__pousada=pousada_ativa,
        data_checkin__lt=data_fim,
        data_checkout__gt=data_inicio
    )
    
    ativos_qtd = reservas_periodo.filter(status__in=['CONFIRMADA', 'HOSPEDADO']).count()
    hospedados_qtd = reservas_periodo.filter(status='HOSPEDADO').count()
    pendentes_qtd = reservas_periodo.filter(status='CONFIRMADA').count()
    
    context = {
        'ativos_qtd': ativos_qtd,
        'hospedados_qtd': hospedados_qtd,
        'pendentes_qtd': pendentes_qtd,
        'unidades_data': unidades_data,
        'selected_quarto': categoria,  # Maps to 'selected_quarto' in the template
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'sistema/partials/reservas_grid.html', context)

@portaria_required
def partner_reserva_detalhe(request, reserva_id=None):
    """
    Modal assíncrono exibindo dados cadastrais FNRH e garagem de uma reserva específica.
    Se reserva_id for None, exibe o modal em modo de criação.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    from decimal import Decimal
    
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
        
        # Auto-cria registros vazios de acompanhantes até a capacidade máxima do quarto
        capacidade = reserva.quarto.capacidade_maxima
        for i in range(1, capacidade + 1):
            if i == 1:
                HospedeReserva.objects.get_or_create(
                    reserva=reserva,
                    ordem=1,
                    defaults={
                        'nome': reserva.hospede_nome or '',
                        'cpf': reserva.hospede_cpf or '',
                        'email': reserva.hospede_email or '',
                        'telefone': reserva.hospede_telefone or '',
                        'rg': reserva.hospede_rg or '',
                        'nacionalidade': reserva.hospede_nacionalidade or 'Brasileira',
                        'profissao': reserva.hospede_profissao or '',
                        'endereco': reserva.hospede_endereco or '',
                    }
                )
            else:
                HospedeReserva.objects.get_or_create(
                    reserva=reserva,
                    ordem=i,
                    defaults={
                        'nome': '',
                        'cpf': '',
                        'email': '',
                        'telefone': '',
                        'rg': '',
                        'nacionalidade': 'Brasileira',
                        'profissao': '',
                        'endereco': '',
                    }
                )
                
        hospedes = reserva.hospedes.all().order_by('ordem')
        try:
            veiculo = reserva.veiculo
        except Exception:
            veiculo = None
    else:
        # Reserva fictícia em memória para criação
        reserva = Reserva(
            status='PENDENTE',
            data_checkin=timezone.now().date(),
            data_checkout=timezone.now().date() + timedelta(days=1),
            valor_total=Decimal('0.00'),
            valor_pago=Decimal('0.00'),
        )
        # Hóspedes fictícios em memória (ordem de 1 a 8)
        hospedes = [
            HospedeReserva(ordem=i, nome='', cpf='', email='', telefone='', rg='', nacionalidade='Brasileira', profissao='', endereco='')
            for i in range(1, 9)
        ]
        veiculo = None
        
    import json
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', {
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
    })

@portaria_required
@require_POST
def partner_salvar_estadia_veiculo(request, reserva_id):
    """
    Salva as alterações de estadia (datas, quarto, valores) e garagem (veículo) diretamente do modal de detalhes.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    quarto_id = request.POST.get('quarto')
    data_checkin_str = request.POST.get('data_checkin')
    hora_checkin_str = request.POST.get('hora_checkin', '14:00')
    data_checkout_str = request.POST.get('data_checkout')
    hora_checkout_str = request.POST.get('hora_checkout', '12:00')
    
    valor_total_str = request.POST.get('valor_total', '0.00').strip()
    valor_pago_str = request.POST.get('valor_pago', '0.00').strip()
    
    if ',' in valor_total_str:
        valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
    if ',' in valor_pago_str:
        valor_pago_str = valor_pago_str.replace('.', '').replace(',', '.')
        
    if not all([quarto_id, data_checkin_str, data_checkout_str]):
        return HttpResponse('Os campos Quarto, Entrada e Saída são obrigatórios.', status=400)
        
    try:
        data_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
        data_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('Formato de datas inválido.', status=400)
        
    if data_checkout <= data_checkin:
        return HttpResponse('A data de saída deve ser posterior à data de entrada.', status=400)
        
    quarto = get_object_or_404(Quarto, id=quarto_id, pousada=pousada_ativa)
    
    # Conflitos de reservas (excluindo a própria reserva)
    reservas_conflito = Reserva.objects.filter(
        quarto=quarto,
        data_checkin__lt=data_checkout,
        data_checkout__gt=data_checkin
    ).exclude(status='CANCELADA').exclude(id=reserva.id)
    
    if reservas_conflito.exists():
        return HttpResponse(f'O quarto {quarto.numero} já está ocupado ou reservado no período selecionado.', status=400)
        
    # Bloqueios administrativos
    bloqueios_conflito = BloqueioQuarto.objects.filter(
        quarto=quarto,
        data_inicio__lt=data_checkout,
        data_fim__gt=data_checkin
    )
    if bloqueios_conflito.exists():
        return HttpResponse(f'O quarto {quarto.numero} está sob bloqueio administrativo nesse período.', status=400)
        
    try:
        valor_total = Decimal(valor_total_str)
    except (ValueError, InvalidOperation):
        valor_total = reserva.valor_total
        
    try:
        valor_pago = Decimal(valor_pago_str)
    except (ValueError, InvalidOperation):
        valor_pago = Decimal('0.00')
        
    # Veículo
    v_placa = request.POST.get('veiculo_placa', '').strip().upper()
    v_modelo = request.POST.get('veiculo_modelo', '').strip()
    v_cor = request.POST.get('veiculo_cor', '').strip()
    
    with transaction.atomic():
        quarto_anterior = reserva.quarto
        reserva.quarto = quarto
        reserva.data_checkin = data_checkin
        reserva.hora_checkin = hora_checkin_str
        reserva.data_checkout = data_checkout
        reserva.hora_checkout = hora_checkout_str
        reserva.subtotal = valor_total
        reserva.valor_total = valor_total
        reserva.valor_pago = valor_pago
        reserva.repasse_parceiro = valor_total
        
        # Sincroniza status físico do quarto
        if quarto_anterior != quarto:
            if quarto_anterior.status == 'OCUPADO':
                quarto_anterior.status = 'LIVRE'
                quarto_anterior.save()
            if reserva.status == 'HOSPEDADO':
                quarto.status = 'OCUPADO'
                quarto.save()
                
        reserva.save()
        
        # Sincroniza Veículo
        if v_placa:
            VeiculoReserva.objects.update_or_create(
                reserva=reserva,
                defaults={
                    'placa': v_placa,
                    'modelo': v_modelo,
                    'cor': v_cor,
                }
            )
        else:
            VeiculoReserva.objects.filter(reserva=reserva).delete()
            
        ip = obter_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='editar',
            detalhes=(
                f"Estadia e garagem atualizados diretamente no modal de detalhes por {request.user.username}.\n"
                f"IP: {ip} | Aparelho/UA: {user_agent}"
            )
        )
        
    hospedes = reserva.hospedes.all().order_by('ordem')
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    import json
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
        'trigger_grid_update': True,
        'save_success': True,
        'success_message': "Edições Salvas com Sucesso!"
    }
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

@portaria_required
@require_POST
def partner_reserva_checkin(request, reserva_id):
    """
    Efetua a confirmação de check-in na portaria (ou desmarcação), alterando status operacional do quarto físico e gerando logs.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    ip = obter_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
    
    if reserva.status in ['HOSPEDADO', 'FINALIZADA']:
        # Desmarcar Check-in
        reserva.status = 'CONFIRMADA'
        reserva.checkin_realizado_em = None
        reserva.checkout_realizado_em = None
        reserva.save()
        
        # Sincroniza status do Quarto Físico
        reserva.quarto.status = 'LIVRE'
        reserva.quarto.save()
        
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkin',
            detalhes=f"Check-in desmarcado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
        )
    else:
        # Realizar Check-in
        reserva.status = 'HOSPEDADO'
        reserva.checkin_realizado_em = timezone.now()
        reserva.save()
        
        # Sincroniza status do Quarto Físico
        reserva.quarto.status = 'OCUPADO'
        reserva.quarto.save()
        
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkin',
            detalhes=f"Check-in realizado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
        )
        
    # Prepara contexto para re-renderizar o modal mantendo o estado
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    veiculo = getattr(reserva, 'veiculo', None)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    titular = next((h for h in hospedes if h.ordem == 1), None)
    acompanhantes = [h for h in hospedes if h.ordem > 1]
    
    import json
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'veiculo': veiculo,
        'titular': titular,
        'acompanhantes': acompanhantes,
        'hospedes': hospedes,
        'logs': reserva.logs.all(),
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
        'trigger_grid_update': True  # Custom trigger to reload the PMS map
    }
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

@portaria_required
@require_POST
def partner_reserva_checkout(request, reserva_id):
    """
    Efetua a confirmação de checkout na portaria (ou desmarcação), gerando tarefa de faxina e auditoria.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    ip = obter_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
    
    if reserva.status == 'FINALIZADA':
        # Desmarcar Checkout
        reserva.status = 'HOSPEDADO'
        reserva.checkout_realizado_em = None
        reserva.save()
        
        # Sincroniza status do Quarto Físico
        reserva.quarto.status = 'OCUPADO'
        reserva.quarto.save()
        
        # Remove tarefas de limpeza pendentes associadas
        TarefaLimpeza.objects.filter(quarto=reserva.quarto, status='PENDENTE').delete()
        
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkout',
            detalhes=f"Check-out desmarcado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
        )
    else:
        # Realizar Checkout
        reserva.status = 'FINALIZADA'
        reserva.checkout_realizado_em = timezone.now()
        reserva.save()
        
        # Sincroniza status do Quarto Físico
        reserva.quarto.status = 'SUJO'
        reserva.quarto.save()
        
        # Automação de Limpeza e Faxina
        TarefaLimpeza.objects.get_or_create(
            quarto=reserva.quarto,
            status='PENDENTE',
            defaults={'observacoes': f"Faxina Geral pós Checkout. Reserva localizadora #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}."}
        )
        
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkout',
            detalhes=f"Check-out realizado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
        )
        
    # Prepara contexto para re-renderizar o modal
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    veiculo = getattr(reserva, 'veiculo', None)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    titular = next((h for h in hospedes if h.ordem == 1), None)
    acompanhantes = [h for h in hospedes if h.ordem > 1]
    
    import json
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'veiculo': veiculo,
        'titular': titular,
        'acompanhantes': acompanhantes,
        'hospedes': hospedes,
        'logs': reserva.logs.all(),
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
        'trigger_grid_update': True
    }
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

@portaria_required
@require_POST
def partner_reserva_cancelar(request, reserva_id):
    """
    Cancela uma reserva e fecha o modal via HTMX.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    reserva.status = 'CANCELADA'
    reserva.save()
    
    # Se o quarto constava ocupado por esta reserva, libera
    if reserva.quarto.status == 'OCUPADO':
        reserva.quarto.status = 'LIVRE'
        reserva.quarto.save()
        
    ReservaLog.objects.create(
        reserva=reserva,
        usuario=request.user,
        acao='cancelar',
        detalhes=f"Reserva cancelada por {request.user.username}."
    )
    
    return HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            const filtro = document.getElementById('filtro-periodo');
            if (filtro) { htmx.trigger(filtro, 'change'); } else { window.location.reload(); }
        </script>
    """)

import json
from decimal import Decimal, InvalidOperation
from django.db import transaction
from sistema.models import Cliente

@portaria_required
def partner_reserva_formulario(request, reserva_id=None):
    """
    Rende o modal unificado de formulário de reserva para criação ou edição.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    
    reserva = None
    veiculo = None
    titular = None
    acompanhantes = []
    logs = []
    
    if reserva_id:
        reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
        veiculo = getattr(reserva, 'veiculo', None)
        hospedes = list(reserva.hospedes.all().order_by('ordem'))
        titular = next((h for h in hospedes if h.ordem == 1), None)
        acompanhantes = [h for h in hospedes if h.ordem > 1]
        logs = reserva.logs.all()
        
    # Serialização de dados para AlpineJS
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'veiculo': veiculo,
        'titular': titular,
        'acompanhantes': acompanhantes,
        'logs': logs,
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id if reserva else None),
    }
    return render(request, 'sistema/partials/modal_reserva_formulario.html', context)


@portaria_required
def partner_reserva_salvar(request):
    """
    Cria ou atualiza uma reserva manualmente (BALCAO).
    """
    if request.method != 'POST':
        return HttpResponse('Método não permitido.', status=405)
        
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    reserva_id = request.POST.get('reserva_id')
    
    # Helper para retornar formulário com erro
    def retornar_erro(msg):
        categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
        quartos = Quarto.objects.filter(pousada=pousada_ativa)
        
        categorias_list = [
            {
                'id': cat.id,
                'nome': cat.nome,
                'preco_base': float(cat.preco_base),
                'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
            }
            for cat in categorias
        ]
        
        quartos_list = [
            {
                'id': q.id,
                'numero': q.numero,
                'categoria_id': q.categoria_id,
                'capacidade_maxima': q.capacidade_maxima,
                'status': q.status
            }
            for q in quartos
        ]
        
        reserva = None
        veiculo = None
        titular = None
        acompanhantes = []
        logs = []
        
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
            veiculo = getattr(reserva, 'veiculo', None)
            hospedes = list(reserva.hospedes.all().order_by('ordem'))
            titular = next((h for h in hospedes if h.ordem == 1), None)
            acompanhantes = [h for h in hospedes if h.ordem > 1]
            logs = reserva.logs.all()
        else:
            from decimal import Decimal
            reserva = Reserva(
                status='PENDENTE',
                data_checkin=timezone.now().date(),
                data_checkout=timezone.now().date() + timedelta(days=1),
                valor_total=Decimal('0.00'),
                valor_pago=Decimal('0.00'),
            )
            hospedes = [
                HospedeReserva(ordem=i, nome='', cpf='', email='', telefone='', rg='', nacionalidade='Brasileira', profissao='', endereco='')
                for i in range(1, 9)
            ]
            veiculo = None
            titular = hospedes[0]
            acompanhantes = hospedes[1:]
            logs = []
            
        submitted_data = {
            'data_checkin': request.POST.get('data_checkin', ''),
            'hora_checkin': request.POST.get('hora_checkin', '14:00'),
            'data_checkout': request.POST.get('data_checkout', ''),
            'hora_checkout': request.POST.get('hora_checkout', '12:00'),
        }
        context = {
            'reserva': reserva,
            'veiculo': veiculo,
            'titular': titular,
            'acompanhantes': acompanhantes,
            'hospedes': hospedes,
            'logs': logs,
            'categorias': categorias,
            'quartos': quartos,
            'categorias_json': json.dumps(categorias_list),
            'quartos_json': json.dumps(quartos_list),
            'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva_id),
            'error_message': msg,
            'submitted_data': submitted_data
        }
        return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

    # Captura dados da Estadia
    quarto_id = request.POST.get('quarto')
    data_checkin_str = request.POST.get('data_checkin')
    hora_checkin_str = request.POST.get('hora_checkin', '14:00')
    data_checkout_str = request.POST.get('data_checkout')
    hora_checkout_str = request.POST.get('hora_checkout', '12:00')
    status_reserva = request.POST.get('status', 'PENDENTE')
    valor_total_str = request.POST.get('valor_total', '0.00').strip()
    if ',' in valor_total_str:
        valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
        
    valor_pago_str = request.POST.get('valor_pago', '0.00').strip()
    if ',' in valor_pago_str:
        valor_pago_str = valor_pago_str.replace('.', '').replace(',', '.')
    
    # Validações Básicas de Estadia
    if not all([quarto_id, data_checkin_str, data_checkout_str, hora_checkin_str, hora_checkout_str]):
        return retornar_erro('Preencha todos os campos da estadia (Datas, Horários e Quarto).')
        
    try:
        data_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
        data_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return retornar_erro('Formato de datas inválido.')

    try:
        datetime.strptime(hora_checkin_str, '%H:%M')
        datetime.strptime(hora_checkout_str, '%H:%M')
    except ValueError:
        return retornar_erro('Formato de horários inválido. Use o formato HH:MM.')
        
    if data_checkout <= data_checkin:
        return retornar_erro('A data de saída deve ser posterior à data de entrada.')
        
    quarto = get_object_or_404(Quarto, id=quarto_id, pousada=pousada_ativa)
    
    # Verifica Overlaps (conflitos) excluindo a própria reserva em caso de edição
    reservas_conflito = Reserva.objects.filter(
        quarto=quarto,
        data_checkin__lt=data_checkout,
        data_checkout__gt=data_checkin
    ).exclude(status='CANCELADA')
    
    if reserva_id:
        reservas_conflito = reservas_conflito.exclude(id=reserva_id)
        
    if reservas_conflito.exists():
        return retornar_erro(f'O quarto {quarto.numero} já está ocupado ou reservado no período selecionado.')

    # Verifica se há bloqueios administrativos no período
    bloqueios_conflito = BloqueioQuarto.objects.filter(
        quarto=quarto,
        data_inicio__lt=data_checkout,
        data_fim__gt=data_checkin
    )
    if bloqueios_conflito.exists():
        bloqueio = bloqueios_conflito.first()
        motivo_str = f" (Motivo: {bloqueio.motivo})" if bloqueio.motivo else ""
        return retornar_erro(f'O quarto {quarto.numero} está sob bloqueio administrativo nesse período{motivo_str}.')
        
    # Captura Hóspede 1 (Titular) - OBRIGATÓRIO
    h_nome_1 = request.POST.get('hospede_nome_1', '').strip()
    h_cpf_1 = request.POST.get('hospede_cpf_1', '').strip()
    h_email_1 = request.POST.get('hospede_email_1', '').strip()
    h_telefone_1 = request.POST.get('hospede_telefone_1', '').strip()
    
    if not all([h_nome_1, h_cpf_1, h_email_1, h_telefone_1]):
        return retornar_erro('Os dados do Hóspede 1 (Titular) são estritamente obrigatórios (Nome, CPF, E-mail e Telefone).')
        
    h_rg_1 = request.POST.get('hospede_rg_1', '').strip()
    h_nacionalidade_1 = request.POST.get('hospede_nacionalidade_1', 'Brasileira').strip()
    h_profissao_1 = request.POST.get('hospede_profissao_1', '').strip()
    h_endereco_1 = request.POST.get('hospede_endereco_1', '').strip()
    
    # Captura Acompanhantes dinamicamente de acordo com a capacidade do quarto
    acompanhantes_dados = []
    for i in range(2, quarto.capacidade_maxima + 1):
        nome = request.POST.get(f'hospede_nome_{i}', '').strip()
        if nome:
            acompanhantes_dados.append({
                'ordem': i,
                'nome': nome,
                'cpf': request.POST.get(f'hospede_cpf_{i}', '').strip(),
                'email': request.POST.get(f'hospede_email_{i}', '').strip(),
                'telefone': request.POST.get(f'hospede_telefone_{i}', '').strip(),
                'rg': request.POST.get(f'hospede_rg_{i}', '').strip(),
                'nacionalidade': request.POST.get(f'hospede_nacionalidade_{i}', 'Brasileira').strip(),
                'profissao': request.POST.get(f'hospede_profissao_{i}', '').strip(),
                'endereco': request.POST.get(f'hospede_endereco_{i}', '').strip(),
            })
            
    # Veículo
    v_placa = request.POST.get('veiculo_placa', '').strip().upper()
    v_modelo = request.POST.get('veiculo_modelo', '').strip()
    v_cor = request.POST.get('veiculo_cor', '').strip()
    
    # Financeiro
    noites = (data_checkout - data_checkin).days or 1
    from sas.financeiro import calcular_taxas_reserva
    fin_padrao = calcular_taxas_reserva(quarto.categoria, noites)
    
    try:
        valor_total = Decimal(valor_total_str)
    except (ValueError, InvalidOperation):
        valor_total = fin_padrao['total_cliente']
        
    try:
        valor_pago = Decimal(valor_pago_str)
    except (ValueError, InvalidOperation):
        valor_pago = Decimal('0.00')
        
    # Split (sem comissões ou taxas administrativas)
    subtotal = valor_total
    taxas = Decimal('0.00')
    taxa_gateway = Decimal('0.00')
    repasse_parceiro = valor_total
    ganho_liquido = Decimal('0.00')
        
    with transaction.atomic():
        # Cria ou atualiza o Cliente unificado pelo CPF
        cliente, _ = Cliente.objects.update_or_create(
            cpf_passaporte=h_cpf_1,
            defaults={
                'nome': h_nome_1,
                'telefone_whatsapp': h_telefone_1,
                'email': h_email_1,
            }
        )
        
        # Cria/Atualiza a Reserva
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
            quarto_anterior = reserva.quarto
            reserva.quarto = quarto
            reserva.cliente = cliente
            reserva.data_checkin = data_checkin
            reserva.hora_checkin = hora_checkin_str
            reserva.data_checkout = data_checkout
            reserva.hora_checkout = hora_checkout_str
            reserva.status = status_reserva
            reserva.subtotal = subtotal
            reserva.taxas = taxas
            reserva.valor_total = valor_total
            reserva.valor_pago = valor_pago
            reserva.taxa_servico_plataforma = taxas
            reserva.taxa_gateway = taxa_gateway
            reserva.repasse_parceiro = repasse_parceiro
            reserva.ganho_liquido_plataforma = ganho_liquido
            
            # Titular FNRH
            reserva.hospede_nome = h_nome_1
            reserva.hospede_cpf = h_cpf_1
            reserva.hospede_email = h_email_1
            reserva.hospede_telefone = h_telefone_1
            reserva.hospede_rg = h_rg_1
            reserva.hospede_nacionalidade = h_nacionalidade_1
            reserva.hospede_profissao = h_profissao_1
            reserva.hospede_endereco = h_endereco_1
            reserva.quantidade_hospedes = 1 + len(acompanhantes_dados)
            reserva.save()
            
            # Sincroniza quarto anterior se mudou
            if quarto_anterior != quarto:
                if quarto_anterior.status == 'OCUPADO':
                    quarto_anterior.status = 'LIVRE'
                    quarto_anterior.save()
        else:
            reserva = Reserva.objects.create(
                quarto=quarto,
                cliente=cliente,
                usuario=request.user,
                data_checkin=data_checkin,
                hora_checkin=hora_checkin_str,
                data_checkout=data_checkout,
                hora_checkout=hora_checkout_str,
                status=status_reserva,
                subtotal=subtotal,
                taxas=taxas,
                valor_total=valor_total,
                valor_pago=valor_pago,
                taxa_servico_plataforma=taxas,
                taxa_gateway=taxa_gateway,
                repasse_parceiro=repasse_parceiro,
                ganho_liquido_plataforma=ganho_liquido,
                hospede_nome=h_nome_1,
                hospede_cpf=h_cpf_1,
                hospede_email=h_email_1,
                hospede_telefone=h_telefone_1,
                hospede_rg=h_rg_1,
                hospede_nacionalidade=h_nacionalidade_1,
                hospede_profissao=h_profissao_1,
                hospede_endereco=h_endereco_1,
                quantidade_hospedes=1 + len(acompanhantes_dados),
                canal_origem='BALCAO'
            )
            
        # Sincroniza status do Quarto Físico
        if status_reserva == 'HOSPEDADO':
            quarto.status = 'OCUPADO'
            quarto.save()
        elif status_reserva == 'FINALIZADA':
            quarto.status = 'SUJO'
            quarto.save()
            TarefaLimpeza.objects.get_or_create(
                quarto=quarto,
                status='PENDENTE',
                defaults={'observacoes': f"Faxina Geral pós Checkout. Reserva localizadora #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}."}
            )
            
        # Salva/Atualiza HospedeReserva do Titular
        hospede_1, _ = HospedeReserva.objects.update_or_create(
            reserva=reserva,
            ordem=1,
            defaults={
                'nome': h_nome_1,
                'cpf': h_cpf_1,
                'email': h_email_1,
                'telefone': h_telefone_1,
                'rg': h_rg_1,
                'nacionalidade': h_nacionalidade_1,
                'profissao': h_profissao_1,
                'endereco': h_endereco_1,
            }
        )
        
        # Documentos Titular
        if request.POST.get('delete_doc_frente_1') == 'true':
            hospede_1.documento_frente = None
        if request.POST.get('delete_doc_verso_1') == 'true':
            hospede_1.documento_verso = None
            
        docs_list_1 = request.FILES.getlist('documentos_1')
        if len(docs_list_1) > 0:
            hospede_1.documento_frente = docs_list_1[0]
        if len(docs_list_1) > 1:
            hospede_1.documento_verso = docs_list_1[1]
        hospede_1.save()
        
        # Também salva na tabela de anexos gerais (DocumentoHospede)
        for doc in docs_list_1:
            DocumentoHospede.objects.get_or_create(
                hospede=hospede_1,
                arquivo=doc,
                defaults={'nome': doc.name}
            )
        
        # Sincroniza Acompanhantes
        acompanhantes_salvos_ids = []
        for ac in acompanhantes_dados:
            h_ac, _ = HospedeReserva.objects.update_or_create(
                reserva=reserva,
                ordem=ac['ordem'],
                defaults={
                    'nome': ac['nome'],
                    'cpf': ac['cpf'],
                    'email': ac['email'],
                    'telefone': ac['telefone'],
                    'rg': ac['rg'],
                    'nacionalidade': ac['nacionalidade'],
                    'profissao': ac['profissao'],
                    'endereco': ac['endereco'],
                }
            )
            
            o = ac['ordem']
            if request.POST.get(f'delete_doc_frente_{o}') == 'true':
                h_ac.documento_frente = None
            if request.POST.get(f'delete_doc_verso_{o}') == 'true':
                h_ac.documento_verso = None
                
            docs_list_ac = request.FILES.getlist(f'documentos_{o}')
            if len(docs_list_ac) > 0:
                h_ac.documento_frente = docs_list_ac[0]
            if len(docs_list_ac) > 1:
                h_ac.documento_verso = docs_list_ac[1]
            h_ac.save()
            
            # Também salva na tabela de anexos gerais (DocumentoHospede)
            for doc in docs_list_ac:
                DocumentoHospede.objects.get_or_create(
                    hospede=h_ac,
                    arquivo=doc,
                    defaults={'nome': doc.name}
                )
            acompanhantes_salvos_ids.append(h_ac.id)
            
        HospedeReserva.objects.filter(reserva=reserva, ordem__gt=1).exclude(id__in=acompanhantes_salvos_ids).delete()
        
        # Log de Auditoria
        ip = obter_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
        acao_log = 'editar' if reserva_id else 'criar'
        detalhes_log = (
            f"Reserva {'atualizada' if reserva_id else 'criada'} manualmente por {request.user.username}.\n"
            f"IP: {ip} | Aparelho/UA: {user_agent}"
        )
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao=acao_log,
            detalhes=detalhes_log
        )
            
        # Sincroniza Veículo
        if v_placa:
            VeiculoReserva.objects.update_or_create(
                reserva=reserva,
                defaults={
                    'placa': v_placa,
                    'modelo': v_modelo,
                    'cor': v_cor,
                }
            )
        else:
            VeiculoReserva.objects.filter(reserva=reserva).delete()
            
    # Contexto para retornar no modal de detalhes com animação de sucesso
    hospedes = reserva.hospedes.all().order_by('ordem')
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    import json
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
        'trigger_grid_update': True,
        'save_success': True,
        'success_message': "Edições Salvas com Sucesso!" if reserva_id else "Lançamento Salvo com Sucesso!"
    }
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

@portaria_required
@require_POST
def partner_salvar_hospede_fnrh(request, hospede_id):
    """
    Atualiza individualmente a ficha FNRH (dados e documentos) de um hóspede de uma reserva ativa.
    Utilizado no modal side-by-side de detalhes.
    """
    hospede = get_object_or_404(HospedeReserva, id=hospede_id)
    reserva = hospede.reserva
    
    nome = request.POST.get('nome', '').strip()
    cpf = request.POST.get('cpf', '').strip()
    email = request.POST.get('email', '').strip()
    telefone = request.POST.get('telefone', '').strip()
    rg = request.POST.get('rg', '').strip()
    nacionalidade = request.POST.get('nacionalidade', 'Brasileira').strip()
    profissao = request.POST.get('profissao', '').strip()
    endereco = request.POST.get('endereco', '').strip()
    
    if not nome:
        return partner_reserva_detalhe(request, reserva.id)
        
    hospede.nome = nome
    hospede.cpf = cpf
    hospede.email = email
    hospede.telefone = telefone
    hospede.rg = rg
    hospede.nacionalidade = nacionalidade
    hospede.profissao = profissao
    hospede.endereco = endereco
    hospede.save()
    
    # Processa múltiplos anexos novos adicionados na lista geral
    novos_docs = request.FILES.getlist('novos_documentos')
    for doc in novos_docs:
        DocumentoHospede.objects.create(
            hospede=hospede,
            arquivo=doc,
            nome=doc.name
        )
        
    # Sincroniza dados do titular se for ordem 1
    if hospede.ordem == 1:
        reserva.hospede_nome = nome
        reserva.hospede_cpf = cpf
        reserva.hospede_email = email
        reserva.hospede_telefone = telefone
        reserva.hospede_rg = rg
        reserva.hospede_nacionalidade = nacionalidade
        reserva.hospede_profissao = profissao
        reserva.hospede_endereco = endereco
        reserva.save()
        
    # Auditoria
    ReservaLog.objects.create(
        reserva=reserva,
        usuario=request.user,
        acao='editar_hospede',
        detalhes=f"Hóspede {hospede.ordem} ({nome}) atualizado por {request.user.username}."
    )
    
    # Retorna o detalhe da reserva atualizado
    return partner_reserva_detalhe(request, reserva.id)


@portaria_required
@require_POST
def partner_deletar_documento_hospede(request, documento_id):
    """
    Deleta individualmente um documento/anexo de um hóspede de forma imediata via HTMX.
    """
    doc = get_object_or_404(DocumentoHospede, id=documento_id)
    reserva_id = doc.hospede.reserva.id
    nome_doc = doc.nome or doc.arquivo.name
    hospede_nome = doc.hospede.nome
    
    # Remove o arquivo físico e o registro
    doc.arquivo.delete(save=False)
    doc.delete()
    
    # Auditoria
    ReservaLog.objects.create(
        reserva_id=reserva_id,
        usuario=request.user,
        acao='deletar_documento',
        detalhes=f"Documento '{nome_doc}' do hóspede {hospede_nome} deletado por {request.user.username}."
    )
    
    return partner_reserva_detalhe(request, reserva_id)


@portaria_required
@require_POST
def partner_reserva_excluir(request, reserva_id):
    """
    Exclui permanentemente uma reserva do banco de dados, exigindo validação de senha.
    Grava logs operacionais em arquivo de log local para auditoria.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    if not pousada_ativa:
        return HttpResponse('Nenhuma pousada selecionada.', status=400)
        
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    password = request.POST.get('password')
    if not password:
        return HttpResponse('<span class="text-red-500 font-bold text-xs">A senha é obrigatória.</span>')
        
    # Valida senha do usuário logado
    if not request.user.check_password(password):
        return HttpResponse('<span class="text-red-500 font-bold text-[10px] uppercase tracking-wider">Senha incorreta. Não foi possível autorizar a exclusão.</span>')
        
    import os
    from django.conf import settings
    from django.utils import timezone
    
    # 1. Obter metadados
    ip = obter_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
    data_hora = timezone.now().strftime('%Y-%m-%d %H:%M:%S %z')
    hospedes_nomes = ", ".join([h.nome for h in reserva.hospedes.all() if h.nome])
    
    # 1.1. Obter logs operacionais antigos
    logs_anteriores = reserva.logs.all().order_by('data_hora')
    logs_str = ""
    for log in logs_anteriores:
        data_hora_log = log.data_hora.strftime('%Y-%m-%d %H:%M:%S')
        usuario_log = log.usuario.username if log.usuario else "Sistema"
        detalhes_clean = log.detalhes.strip().replace('\n', ' | ')
        logs_str += f"   - [{data_hora_log}] AÇÃO: {log.acao.upper()} | OPERADOR: {usuario_log} | DETALHES: {detalhes_clean}\n"
    
    # 2. Gravar no arquivo físico
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'auditoria_reservas.log')
    
    log_line = (
        f"[{data_hora}] AÇÃO: EXCLUSÃO FÍSICA | "
        f"RESERVA ID: {reserva.id} | "
        f"POUSADA: {reserva.quarto.pousada.nome} | "
        f"QUARTO: {reserva.quarto.numero} | "
        f"HÓSPEDES: {hospedes_nomes if hospedes_nomes else 'Sem nomes salvos'} | "
        f"VALOR TOTAL: R$ {reserva.valor_total} | "
        f"EXCLUÍDO POR: {request.user.username} ({request.user.nome_completo}) | "
        f"IP: {ip} | "
        f"APARELHO/UA: {user_agent}\n"
    )
    if logs_str:
        log_line += "LOGS DE OPERAÇÃO ANTERIORES À EXCLUSÃO:\n" + logs_str + "\n"
    
    try:
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"Erro ao salvar arquivo de auditoria física: {e}")
        
    # 3. Liberar o quarto se o status estava ocupado por esta reserva
    if reserva.quarto.status == 'OCUPADO':
        outras_hospedadas = Reserva.objects.filter(
            quarto=reserva.quarto, 
            status='HOSPEDADO'
        ).exclude(id=reserva.id)
        if not outras_hospedadas.exists():
            reserva.quarto.status = 'LIVRE'
            reserva.quarto.save()
            
    # 4. Deleta física
    reserva.delete()
    
    # 5. Script para fechar o modal e recarregar o grid
    return HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            const filtro = document.getElementById('filtro-periodo');
            if (filtro) { htmx.trigger(filtro, 'change'); } else { window.location.reload(); }
        </script>
    """)

@portaria_required
@require_POST
def partner_reserva_toggle_pagamento(request, reserva_id):
    """
    Alterna o status de pagamento de uma reserva.
    Se a reserva estiver marcada como paga, atualiza valor_pago = valor_total e lança a TransacaoFinanceira.
    Se estiver não paga, zera o valor_pago e remove as transações associadas.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    reserva = get_object_or_404(Reserva, id=reserva_id, quarto__pousada=pousada_ativa)
    
    ip = obter_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Desconhecido')
    
    is_currently_paid = (reserva.valor_pago >= reserva.valor_total and reserva.valor_total > 0) or (reserva.valor_pago > 0 and reserva.valor_total == 0)
    
    with transaction.atomic():
        if is_currently_paid:
            reserva.valor_pago = Decimal('0.00')
            reserva.save()
            
            # Remove transação financeira associada à diária
            TransacaoFinanceira.objects.filter(reserva=reserva, categoria='DIARIA').delete()
            
            ReservaLog.objects.create(
                reserva=reserva,
                usuario=request.user,
                acao='estorno_pagamento',
                detalhes=f"Lançamento de pagamento estornado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
            )
        else:
            reserva.valor_pago = reserva.valor_total
            reserva.save()
            
            # Cria ou atualiza transação financeira
            TransacaoFinanceira.objects.update_or_create(
                reserva=reserva,
                categoria='DIARIA',
                defaults={
                    'pousada': reserva.quarto.pousada,
                    'tipo': 'RECEITA',
                    'valor': reserva.valor_total,
                    'metodo_pagamento': 'PIX',
                    'descricao': f"Faturamento de Diárias - Reserva #{reserva.id}",
                    'data_pagamento': timezone.now().date(),
                }
            )
            
            ReservaLog.objects.create(
                reserva=reserva,
                usuario=request.user,
                acao='pagamento',
                detalhes=f"Pagamento total de R$ {reserva.valor_total} confirmado por {request.user.username}.\nIP: {ip} | Aparelho/UA: {user_agent}"
            )
            
    # Prepara contexto para re-renderizar o modal mantendo o estado
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True)
    quartos = Quarto.objects.filter(pousada=pousada_ativa)
    veiculo = getattr(reserva, 'veiculo', None)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    titular = next((h for h in hospedes if h.ordem == 1), None)
    acompanhantes = [h for h in hospedes if h.ordem > 1]
    
    import json
    categorias_list = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'preco_base': float(cat.preco_base),
            'capacidade': cat.capacidade_adultos + cat.capacidade_criancas
        }
        for cat in categorias
    ]
    
    quartos_list = [
        {
            'id': q.id,
            'numero': q.numero,
            'categoria_id': q.categoria_id,
            'capacidade_maxima': q.capacidade_maxima,
            'status': q.status
        }
        for q in quartos
    ]
    
    context = {
        'reserva': reserva,
        'veiculo': veiculo,
        'titular': titular,
        'acompanhantes': acompanhantes,
        'hospedes': hospedes,
        'logs': reserva.logs.all(),
        'categorias': categorias,
        'quartos': quartos,
        'categorias_json': json.dumps(categorias_list),
        'quartos_json': json.dumps(quartos_list),
        'indisponibilidades_json': obter_datas_indisponiveis_json(pousada_ativa, reserva_id_excluir=reserva.id),
        'trigger_grid_update': True
    }
    return render(request, 'sistema/partials/modal_reserva_detalhe.html', context)

