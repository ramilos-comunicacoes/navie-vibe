from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, date, timedelta
from .models import Hotel, ParceiroUsuario, Reserva, Quarto, UnidadeQuarto, Tarefa
from .utils import checar_disponibilidade_quarto, buscar_datas_proximas

def home(request):
    destaque = Hotel.objects.filter(destaque=True, status='ativo').first()
    proximos = Hotel.objects.filter(status='ativo').order_by('id')[:6]
    
    context = {
        'destaque': destaque,
        'proximos': proximos,
    }
    return render(request, 'hoteis/home.html', context)

def detalhe(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'imagens': imagens,
    }
    return render(request, 'hoteis/detalhe.html', context)

def vanity_url(request, slug):
    """
    Exibe a vitrine B2C pública do hotel a partir do seu slug customizado (vanity URL).
    """
    hotel = get_object_or_404(Hotel, slug=slug)
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'imagens': imagens,
    }
    return render(request, 'hoteis/detalhe.html', context)

def api_check_disponibilidade(request, hotel_id):
    checkin_str = request.GET.get('checkin')
    checkout_str = request.GET.get('checkout')
    
    if not checkin_str or not checkout_str:
        return JsonResponse({'error': 'Datas invalidas'}, status=400)
    
    try:
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato invalido'}, status=400)
        
    if checkout <= checkin:
        return JsonResponse({'error': 'Checkout deve ser depois de Checkin'}, status=400)
        
    noites = (checkout - checkin).days
    
    hotel = get_object_or_404(Hotel, id=hotel_id)
    resultado = []
    
    for quarto in hotel.quartos.all():
        disp = checar_disponibilidade_quarto(quarto, checkin, checkout)
        item = {
            'quarto_id': quarto.id,
            'disponivel': disp,
            'sugestao_antes': None,
            'sugestao_depois': None,
            'preco_total': float(quarto.preco * noites),
            'noites': noites
        }
        
        if not disp:
            ant, dep = buscar_datas_proximas(quarto, checkin, noites)
            if ant: item['sugestao_antes'] = ant.strftime('%Y-%m-%d')
            if dep: item['sugestao_depois'] = dep.strftime('%Y-%m-%d')
            
        resultado.append(item)
        
    return JsonResponse({'resultados': resultado})


def api_datas_ocupadas(request, hotel_id):
    """Retorna uma lista de datas em que TODOS os quartos do hotel estao indisponiveis."""
    mes_str = request.GET.get('mes')   # YYYY-MM
    if not mes_str:
        return JsonResponse({'error': 'Param mes obrigatorio'}, status=400)
    
    try:
        ano, mes = int(mes_str.split('-')[0]), int(mes_str.split('-')[1])
    except Exception:
        return JsonResponse({'error': 'Formato invalido. Use YYYY-MM'}, status=400)
    
    hotel = get_object_or_404(Hotel, id=hotel_id)
    quartos = list(hotel.quartos.all())
    
    # Primeiro e ultimo dia do mes
    primeiro = date(ano, mes, 1)
    if mes == 12:
        ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo = date(ano, mes + 1, 1) - timedelta(days=1)
    
    datas_ocupadas = []
    d = primeiro
    while d <= ultimo:
        checkout_d = d + timedelta(days=1)
        # Uma data e ocupada se nenhum quarto tem unidade livre
        todos_ocupados = all(
            not checar_disponibilidade_quarto(q, d, checkout_d)
            for q in quartos
        )
        if todos_ocupados:
            datas_ocupadas.append(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)
    
    return JsonResponse({'datas_ocupadas': datas_ocupadas})

def partner_auth(request):
    """
    Controla o login e a solicitação de parceria para donos e equipes de hotéis/pousadas.
    Usa HTMX para transições fluidas de tela inteira sem recarregamento.
    """
    from django.http import HttpResponse
    from django.urls import reverse
    
    is_htmx = request.headers.get('HX-Request') == 'true' or 'form' in request.GET
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_parceiro'):
            if is_htmx:
                response = HttpResponse()
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
        # Usuários logados como cliente comum não são redirecionados mais para poderem se logar como parceiros!

    # Se for requisição HTMX do tipo GET para trocar de formulário
    if request.method == 'GET' and is_htmx:
        form_type = request.GET.get('form', 'login')
        if form_type == 'register':
            return render(request, 'hoteis/partner_register_form.html')
        return render(request, 'hoteis/partner_login_form.html')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'login':
            username_or_email = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            # Tenta autenticar pelo username direto
            user = authenticate(request, username=username_or_email, password=password)
            
            # Se falhar, tenta autenticar buscando pelo e-mail
            if user is None and '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
                    
            if user is not None:
                # Checa se o usuário possui perfil de parceiro
                if hasattr(user, 'perfil_parceiro'):
                    perfil = user.perfil_parceiro
                    if perfil.ativo:
                        auth_login(request, user)
                        messages.success(request, f"Bem-vindo de volta, {user.first_name or user.username}!")
                        if is_htmx:
                            response = HttpResponse()
                            response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                            return response
                        return redirect('hoteis:partner_dashboard')
                    else:
                        msg = "Sua conta de parceiro está aguardando aprovação dos administradores."
                else:
                    msg = "Este portal é exclusivo para parceiros de hospedagem. Acesse a área de Clientes Comuns."
            else:
                msg = "Credenciais inválidas. Verifique seu login e senha."
                
            if is_htmx:
                # Retorna apenas o formulário com a mensagem de erro injetada
                context = {'error_message': msg, 'username_entered': username_or_email}
                return render(request, 'hoteis/partner_login_form.html', context)
            else:
                messages.error(request, msg)
                
        elif action == 'register':
            nome_hotel = request.POST.get('nome_hotel', '').strip()
            tipo_hotel = request.POST.get('tipo_hotel', '').strip()
            cnpj = request.POST.get('cnpj', '').strip()
            responsavel = request.POST.get('responsavel_nome', '').strip()
            cpf = request.POST.get('responsavel_cpf', '').strip()
            email = request.POST.get('responsavel_email', '').strip()
            telefone = request.POST.get('responsavel_telefone', '').strip()
            username = request.POST.get('username_solicitado', '').strip()
            
            if nome_hotel and responsavel and email and telefone:
                if is_htmx:
                    context = {
                        'nome_hotel': nome_hotel,
                        'responsavel': responsavel,
                        'email': email,
                    }
                    return render(request, 'hoteis/partner_register_success.html', context)
                else:
                    messages.success(request, "Solicitação de parceria enviada com sucesso! Nossa equipe analisará seus dados.")
            else:
                msg = "Preencha todos os campos obrigatórios para enviar a solicitação."
                if is_htmx:
                    context = {'error_message': msg}
                    return render(request, 'hoteis/partner_register_form.html', context)
                else:
                    messages.error(request, msg)

    return render(request, 'hoteis/partner_login.html')

@login_required(login_url='hoteis:partner_login')
def partner_dashboard(request):
    """
    O painel B2B adaptativo do parceiro hoteleiro.
    Renderiza informações financeiras, quartos, equipe, reservas e o módulo reativo de Atividades (Kanban & Calendário).
    """
    from django.db.models import Q
    import calendar as pycalendar
    
    if not hasattr(request.user, 'perfil_parceiro'):
        messages.error(request, "Acesso negado. Portal exclusivo para parceiros.")
        return redirect('clientes:painel')
        
    perfil = request.user.perfil_parceiro
    if not perfil.ativo:
        messages.error(request, "Sua conta está inativa ou pendente de aprovação.")
        return redirect('hoteis:partner_login')
        
    hotel = perfil.hotel
    hoje = date.today()
    
    # Coleta de dados operacionais
    quartos = hotel.quartos.all()
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    
    # Tarefas Reais
    tarefas_qs = Tarefa.objects.filter(hotel=hotel).select_related('responsavel', 'unidade', 'unidade__quarto').prefetch_related('responsavel__user')
    
    # Divisão por colunas Kanban
    overdue = tarefas_qs.filter(data_vencimento__lt=hoje).exclude(status='done').order_by('data_vencimento')
    todo = tarefas_qs.filter(status='todo').filter(Q(data_vencimento__gte=hoje) | Q(data_vencimento__isnull=True)).order_by('prioridade')
    doing = tarefas_qs.filter(status='doing').filter(Q(data_vencimento__gte=hoje) | Q(data_vencimento__isnull=True)).order_by('prioridade')
    done = tarefas_qs.filter(status='done').order_by('-atualizado_em')
    
    # Geração de Calendário
    try:
        mes_atual = int(request.GET.get('mes', hoje.month))
        ano_atual = int(request.GET.get('ano', hoje.year))
    except ValueError:
        mes_atual = hoje.month
        ano_atual = hoje.year
        
    if mes_atual == 1:
        mes_ant, ano_ant = 12, ano_atual - 1
    else:
        mes_ant, ano_ant = mes_atual - 1, ano_atual
        
    if mes_atual == 12:
        mes_prox, ano_prox = 1, ano_atual + 1
    else:
        mes_prox, ano_prox = mes_atual + 1, ano_atual
        
    meses_nomes = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    nome_mes = meses_nomes.get(mes_atual, "Mês")
    
    cal = pycalendar.Calendar(firstweekday=6) # Domingo
    semanas_matriz = cal.monthdatescalendar(ano_atual, mes_atual)
    
    dias_calendario = []
    for semana in semanas_matriz:
        semana_dias = []
        for d in semana:
            tarefas_do_dia = [t for t in tarefas_qs if t.data_vencimento == d]
            semana_dias.append({
                'dia': d.day,
                'data': d,
                'is_current_month': d.month == mes_atual,
                'is_today': d == hoje,
                'tarefas_preview': tarefas_do_dia[:2],
                'mais_tarefas': max(0, len(tarefas_do_dia) - 2)
            })
        dias_calendario.append(semana_dias)
        
    # Lançamentos simulados de caixa (Proprietário e Gerente vêem)
    financeiro_lancamentos = [
        {'id': 1, 'tipo': 'receita', 'desc': 'Reserva Suite 101 - Tiago', 'valor': 550.00, 'data': '2026-05-24'},
        {'id': 2, 'tipo': 'despesa', 'desc': 'Compra de enxoval (Toalhas)', 'valor': 350.00, 'data': '2026-05-23'},
        {'id': 3, 'tipo': 'receita', 'desc': 'Frigobar Consumo Chalé 02', 'valor': 75.00, 'data': '2026-05-23'},
        {'id': 4, 'tipo': 'despesa', 'desc': 'Reparo Chuveiro Elétrico 104', 'valor': 120.00, 'data': '2026-05-22'},
    ]
    
    faturamento_total = sum(l['valor'] for l in financeiro_lancamentos if l['tipo'] == 'receita')
    despesas_total = sum(l['valor'] for l in financeiro_lancamentos if l['tipo'] == 'despesa')
    
    context = {
        'perfil': perfil,
        'hotel': hotel,
        'quartos': quartos,
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        'financeiro': financeiro_lancamentos,
        'faturamento_total': faturamento_total,
        'despesas_total': despesas_total,
        'lucro_total': faturamento_total - despesas_total,
        
        # Atividades Kanban & Calendário:
        'overdue': overdue,
        'todo': todo,
        'doing': doing,
        'done': done,
        'nome_mes': nome_mes,
        'ano_atual': ano_atual,
        'mes_ant': mes_ant,
        'ano_ant': ano_ant,
        'mes_prox': mes_prox,
        'ano_prox': ano_prox,
        'dias_calendario': dias_calendario,
    }
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    view_type = request.GET.get('view')
    
    if is_htmx and view_type == 'calendario':
        return render(request, 'hoteis/partials/calendario.html', context)
    elif is_htmx and view_type == 'kanban':
        return render(request, 'hoteis/partials/kanban.html', context)
        
    return render(request, 'hoteis/partner_dashboard.html', context)


def partner_logout(request):
    """
    Desloga o parceiro de hospedagem.
    """
    auth_logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('hoteis:partner_login')


def hotelaria(request):
    """
    Portal B2C dinâmico de Hotelaria do Naviê Vibe.
    Lista todas as pousadas, hotéis, chalés e resorts, com busca e filtros de categoria.
    """
    busca = request.GET.get('busca', '').strip()
    tipo = request.GET.get('tipo', '').strip()  # 'hotel', 'pousada', 'chale', 'resort'
    
    # 1. Busca estabelecimentos ativos
    hoteis_qs = Hotel.objects.filter(status='ativo').select_related('local')
    
    # 2. Filtro de pesquisa textual (Nome, Cidade ou Descrição)
    if busca:
        from django.db.models import Q
        hoteis_qs = hoteis_qs.filter(
            Q(nome__icontains=busca) | 
            Q(local__cidade__icontains=busca) | 
            Q(descricao__icontains=busca)
        )
        
    # 3. Classificação dinâmica de tipo e busca por preço mínimo
    hoteis_list = []
    for hotel in hoteis_qs:
        name_lower = hotel.nome.lower()
        desc_lower = hotel.descricao.lower()
        
        # Classificação por heurística textual de alta precisão
        if 'pousada' in name_lower or 'pousada' in desc_lower:
            h_type = 'pousada'
            h_type_label = 'Pousada'
        elif 'chalé' in name_lower or 'chale' in name_lower or 'chalé' in desc_lower or 'chale' in desc_lower:
            h_type = 'chale'
            h_type_label = 'Chalé'
        elif 'resort' in name_lower or 'resort' in desc_lower:
            h_type = 'resort'
            h_type_label = 'Resort'
        else:
            h_type = 'hotel'
            h_type_label = 'Hotel'
            
        # Filtro de tipo por parâmetro de URL
        if tipo and h_type != tipo:
            continue
            
        # Encontra a menor diária cadastrada para este hotel
        preco_minimo = None
        quartos = hotel.quartos.all()
        if quartos.exists():
            preco_minimo = min(q.preco for q in quartos)
            
        hoteis_list.append({
            'object': hotel,
            'tipo': h_type,
            'tipo_label': h_type_label,
            'preco_minimo': preco_minimo,
        })
        
    context = {
        'hoteis': hoteis_list,
        'busca': busca,
        'tipo': tipo,
    }
    return render(request, 'hoteis/hotelaria.html', context)


def ia_enviar_chat(request):
    """
    Simula uma resposta inteligente da IA para gestão hoteleira.
    Retorna um fragmento HTML compatível com HTMX.
    """
    if request.method != 'POST':
        return redirect('hoteis:partner_dashboard')
        
    mensagem = request.POST.get('mensagem', '').strip().lower()
    
    # Respostas inteligentes e hoteleiras baseadas em palavras-chave
    if 'olá' in mensagem or 'oi' in mensagem or 'bom dia' in mensagem or 'boa tarde' in mensagem or 'boa noite' in mensagem:
        resposta = "Olá! Como posso ajudar você na gestão do estabelecimento hoje? Posso relatar faxinas, consultar faturamento ou listar as tarefas operacionais pendentes."
    elif 'quarto' in mensagem or 'limp' in mensagem or 'faxina' in mensagem or 'limpeza' in mensagem:
        resposta = "Atualmente, a Suíte 101 e o Chalé 02 requerem atenção operacional de limpeza. Posso atribuir uma nova tarefa de higienização ou troca de enxoval para a Maria Camareira se desejar."
    elif 'faturamento' in mensagem or 'financeiro' in mensagem or 'lucro' in mensagem or 'caixa' in mensagem or 'despesa' in mensagem:
        resposta = "De acordo com os registros de caixa, o faturamento deste mês está em R$ 625,00 contra R$ 470,00 de despesas operacionais, gerando um lucro líquido de R$ 155,00. Gostaria de registrar uma nova entrada ou saída de caixa?"
    elif 'ajuda' in mensagem or 'como usar' in mensagem or 'funciona' in mensagem:
        resposta = "Você pode utilizar este assistente virtual para consultar dados operacionais em tempo real. Digite termos como 'faturamento' para ver relatórios, 'limpeza' para acompanhar cronogramas de quartos, ou pergunte sobre check-ins."
    else:
        resposta = "Entendido! Posso ajudar você a simplificar as tarefas diárias da pousada. Gostaria de gerenciar os quartos, planejar o cronograma da equipe ou revisar as reservas pendentes?"
        
    context = {'resposta_ia': resposta}
    return render(request, 'hoteis/ia_chat_response.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_criar_tarefa(request):
    """
    Abre o modal de criação de tarefas.
    No POST, salva e recarrega o painel principal.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        prioridade = request.POST.get('prioridade', 'normal')
        status = request.POST.get('status', 'todo')
        data_vencimento_str = request.POST.get('data_vencimento', '').strip()
        responsavel_id = request.POST.get('responsavel_id')
        unidade_id = request.POST.get('unidade_id')
        reserva_id = request.POST.get('reserva_id')
        
        data_vencimento = None
        if data_vencimento_str:
            try:
                data_vencimento = datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        responsavel = None
        if responsavel_id:
            responsavel = get_object_or_404(ParceiroUsuario, id=responsavel_id, hotel=hotel)
            
        unidade = None
        if unidade_id:
            unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
            
        reserva = None
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
            
        if titulo:
            Tarefa.objects.create(
                hotel=hotel,
                titulo=titulo,
                descricao=descricao,
                prioridade=prioridade,
                status=status,
                data_vencimento=data_vencimento,
                responsavel=responsavel,
                unidade=unidade,
                reserva=reserva
            )
            messages.success(request, "Nova atividade operacional adicionada!")
            
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse()
                from django.urls import reverse
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
            
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    
    data_inicial = request.GET.get('data', '')
    
    context = {
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        'data_inicial': data_inicial,
        'tarefa': None
    }
    return render(request, 'hoteis/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_editar_tarefa(request, tarefa_id):
    """
    Abre o modal de edição de tarefas preenchido.
    No POST, salva as alterações e recarrega o painel.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=hotel)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        prioridade = request.POST.get('prioridade', 'normal')
        status = request.POST.get('status', 'todo')
        data_vencimento_str = request.POST.get('data_vencimento', '').strip()
        responsavel_id = request.POST.get('responsavel_id')
        unidade_id = request.POST.get('unidade_id')
        reserva_id = request.POST.get('reserva_id')
        
        data_vencimento = None
        if data_vencimento_str:
            try:
                data_vencimento = datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        responsavel = None
        if responsavel_id:
            responsavel = get_object_or_404(ParceiroUsuario, id=responsavel_id, hotel=hotel)
            
        unidade = None
        if unidade_id:
            unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
            
        reserva = None
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
            
        if titulo:
            tarefa.titulo = titulo
            tarefa.descricao = descricao
            tarefa.prioridade = prioridade
            tarefa.status = status
            tarefa.data_vencimento = data_vencimento
            tarefa.responsavel = responsavel
            tarefa.unidade = unidade
            tarefa.reserva = reserva
            tarefa.save()
            
            messages.success(request, "Atividade atualizada com sucesso!")
            
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse()
                from django.urls import reverse
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
            
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    
    context = {
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        'tarefa': tarefa,
        'data_inicial': ''
    }
    return render(request, 'hoteis/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_deletar_tarefa(request, tarefa_id):
    """
    Exclui a tarefa e recarrega o dashboard B2B.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=perfil.hotel)
    tarefa.delete()
    
    messages.success(request, "Atividade operacional excluída permanentemente.")
    
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        from django.urls import reverse
        response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
        return response
    return redirect('hoteis:partner_dashboard')


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_mudar_status_tarefa(request, tarefa_id):
    """
    Atualiza assincronamente o status da tarefa via drag-and-drop do SortableJS.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=perfil.hotel)
    
    novo_status = request.POST.get('status')
    if novo_status in ['overdue', 'todo', 'doing', 'done']:
        if novo_status == 'overdue':
            tarefa.status = 'todo'
            tarefa.data_vencimento = date.today() - timedelta(days=1)
        else:
            tarefa.status = novo_status
            
        tarefa.save()
        return HttpResponse(status=200)
    return HttpResponse(status=400)


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_salvar_configuracoes(request):
    """
    Grava as configurações de personalização visual, contatos e geolocalização do hotel.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        messages.error(request, "Acesso negado.")
        return redirect('clientes:painel')
        
    perfil = request.user.perfil_parceiro
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente para alterar as configurações.")
        return redirect('hoteis:partner_dashboard')
        
    hotel = perfil.hotel
    
    # Atualização dos campos de texto e branding
    hotel.nome = request.POST.get('nome', hotel.nome)
    hotel.descricao = request.POST.get('descricao', hotel.descricao)
    hotel.whatsapp = request.POST.get('whatsapp', hotel.whatsapp)
    hotel.cor_primaria = request.POST.get('cor_primaria', hotel.cor_primaria)
    hotel.hero_tipo = request.POST.get('hero_tipo', hotel.hero_tipo)
    
    # URL Customizada (Slug) com verificador de colisão e termos reservados
    slug = request.POST.get('slug', '').strip().lower().replace(' ', '-')
    if slug:
        colisao = Hotel.objects.filter(slug=slug).exclude(id=hotel.id).exists()
        reservado = slug in ['admin', 'accounts', 'api', 'clientes', 'hospedagens', 'hotelaria', 'static', 'media']
        if colisao or reservado:
            messages.error(request, f"O link '/{slug}' já está em uso ou é um termo reservado do sistema. Por favor, escolha outro link.")
            return redirect('hoteis:partner_dashboard')
        hotel.slug = slug
    
    # Geolocalização
    lat = request.POST.get('latitude', '').strip().replace(',', '.')
    lon = request.POST.get('longitude', '').strip().replace(',', '.')
    if lat and lat.lower() != 'none' and lat.lower() != 'nan':
        try:
            hotel.latitude = float(lat)
        except ValueError:
            pass
    if lon and lon.lower() != 'none' and lon.lower() != 'nan':
        try:
            hotel.longitude = float(lon)
        except ValueError:
            pass
            
    # Upload de arquivos
    if 'banner' in request.FILES:
        hotel.banner = request.FILES['banner']
        
    if 'logo' in request.FILES:
        hotel.logo = request.FILES['logo']
        
    if 'foto_fundo' in request.FILES:
        hotel.foto_fundo = request.FILES['foto_fundo']
        
    if 'hero_video' in request.FILES:
        video_file = request.FILES['hero_video']
        # Limitar a 8MB
        if video_file.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo em loop ultrapassa o limite de 8MB permitido.")
            return redirect('hoteis:partner_dashboard')
        hotel.hero_video = video_file
        
    hotel.save()
    messages.success(request, "Configurações do estabelecimento gravadas com sucesso!")
    return redirect('hoteis:partner_dashboard')




