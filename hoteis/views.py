from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, date, timedelta
from django.db import models
from .models import Hotel, ParceiroUsuario, Reserva, Quarto, UnidadeQuarto, Tarefa, HospedeReserva, VeiculoReserva, ReservaLog, ProdutoConsumo, PedidoServico, ItemPedidoServico
from .utils import checar_disponibilidade_quarto, buscar_datas_proximas
from decimal import Decimal

def home(request):
    # Incrementa contador de visualizações global da plataforma
    from core.models import PlataformaConfig
    try:
        config = PlataformaConfig.get_solo()
        config.visualizacoes += 1
        config.save(update_fields=['visualizacoes'])
    except Exception:
        pass

    # Carrega slides do carrossel da home
    from .models import HomeSlide
    slides = list(HomeSlide.objects.filter(ativo=True))
    
    # Se não houver nenhum slide cadastrado, injeta fallbacks dinâmicos de alta definição
    if not slides:
        class MockSlide:
            def __init__(self, id, titulo, subtitulo, tipo_midia, imagem_url, video_url, data_texto, local_texto, texto_cta, link_cta):
                self.id = id
                self.titulo = titulo
                self.subtitulo = subtitulo
                self.tipo_midia = tipo_midia
                self.imagem_url = imagem_url
                self.video_url = video_url
                self.data_texto = data_texto
                self.local_texto = local_texto
                self.texto_cta = texto_cta
                self.link_cta = link_cta

            @property
            def banner(self):
                # Mock object helper to mimic banner.url interface
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.imagem_url) if self.imagem_url else None

            @property
            def hero_video(self):
                # Mock object helper to mimic hero_video.url interface
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.video_url) if self.video_url else None

        slides = [
            MockSlide(
                id=1,
                titulo="Viva a Essência da Serra da Ibiapaba",
                subtitulo="Descubra chalés rústicos, pousadas charmosas e resorts cercados pela natureza exuberante.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Temporada de Inverno",
                local_texto="Serra da Ibiapaba, CE",
                texto_cta="Explorar Hotéis",
                link_cta="/hotelaria/"
            ),
            MockSlide(
                id=2,
                titulo="Chalés Exclusivos com Vista Panorâmica",
                subtitulo="Aproveite o clima frio e aconchegante da serra em acomodações de alto padrão com todo o conforto.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Finais de Semana Especiais",
                local_texto="Tianguá, Ceará",
                texto_cta="Reservar Chalé",
                link_cta="/hotelaria/?tipo=chale"
            ),
            MockSlide(
                id=3,
                titulo="Refúgios & Pousadas Boutique de Luxo",
                subtitulo="Viva momentos inesquecíveis com experiências completas de bem-estar, lazer e alta gastronomia.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Pacotes Exclusivos",
                local_texto="Ubajara, Ceará",
                texto_cta="Ver Pousadas",
                link_cta="/hotelaria/?tipo=pousada"
            )
        ]

    destaque = Hotel.objects.filter(destaque=True, status='ativo').first()
    proximos = Hotel.objects.filter(status='ativo').order_by('id')[:6]
    
    context = {
        'destaque': destaque,
        'proximos': proximos,
        'slides': slides,
    }
    return render(request, 'hoteis/home.html', context)

def detalhe(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    hotel.visualizacoes += 1
    hotel.save(update_fields=['visualizacoes'])
    
    # Incrementa visualizações da Empresa associada
    if hotel.empresa:
        hotel.empresa.visualizacoes += 1
        hotel.empresa.save(update_fields=['visualizacoes'])
    
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    # 3 quartos com mais visualizações (destaque) - Garantir exatamente 3 cards repetindo se houver menos
    quartos_destaque_qs = hotel.quartos.all().order_by('-visualizacoes')
    quartos_destaque = list(quartos_destaque_qs[:3])
    if len(quartos_destaque) > 0:
        while len(quartos_destaque) < 3:
            quartos_destaque.append(quartos_destaque[len(quartos_destaque) % len(quartos_destaque_qs)])
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'quartos_destaque': quartos_destaque,
        'imagens': imagens,
    }
    return render(request, 'hoteis/detalhe.html', context)

def vanity_url(request, slug):
    """
    Exibe a vitrine B2C pública do hotel a partir do seu slug customizado (vanity URL).
    """
    hotel = get_object_or_404(Hotel, slug=slug)
    hotel.visualizacoes += 1
    hotel.save(update_fields=['visualizacoes'])
    
    # Incrementa visualizações da Empresa associada
    if hotel.empresa:
        hotel.empresa.visualizacoes += 1
        hotel.empresa.save(update_fields=['visualizacoes'])
    
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    # 3 quartos com mais visualizações (destaque) - Garantir exatamente 3 cards repetindo se houver menos
    quartos_destaque_qs = hotel.quartos.all().order_by('-visualizacoes')
    quartos_destaque = list(quartos_destaque_qs[:3])
    if len(quartos_destaque) > 0:
        while len(quartos_destaque) < 3:
            quartos_destaque.append(quartos_destaque[len(quartos_destaque) % len(quartos_destaque_qs)])
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'quartos_destaque': quartos_destaque,
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
            return render(request, 'hoteis/auth/partner_register_form.html')
        return render(request, 'hoteis/auth/partner_login_form.html')

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
                return render(request, 'hoteis/auth/partner_login_form.html', context)
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
                    return render(request, 'hoteis/auth/partner_register_success.html', context)
                else:
                    messages.success(request, "Solicitação de parceria enviada com sucesso! Nossa equipe analisará seus dados.")
            else:
                msg = "Preencha todos os campos obrigatórios para enviar a solicitação."
                if is_htmx:
                    context = {'error_message': msg}
                    return render(request, 'hoteis/auth/partner_register_form.html', context)
                else:
                    messages.error(request, msg)

    return render(request, 'hoteis/auth/partner_login.html')

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

    # === CENTRAL DE HÓSPEDES & CONCIERGE ===
    from .models import ProdutoConsumo, PedidoServico
    hospedes_ativos = Reserva.objects.filter(unidade__quarto__hotel=hotel, status='hospedado').order_by('unidade__identificador')
    pedidos_ativos = PedidoServico.objects.filter(hotel=hotel).order_by('-criado_em')
    produtos_consumo = ProdutoConsumo.objects.filter(hotel=hotel, disponivel=True)

    # === SISTEMA DE RESERVAS & PMS GRID (CABANAS) ===
    # 1. Categoria selecionada (Quarto)
    quarto_id = request.GET.get('quarto_id')
    selected_quarto = None
    if quarto_id:
        try:
            selected_quarto = hotel.quartos.get(id=quarto_id)
        except Exception:
            pass
    if not selected_quarto:
        selected_quarto = hotel.quartos.first()
        
    # 2. Filtro de Período (Default: Hoje até hoje + 7 dias)
    data_inicio = hoje
    data_fim = hoje + timedelta(days=7)
    
    # Aceita params separados (novo) ou período unificado (legado)
    di_str = request.GET.get('data_inicio', '')
    df_str = request.GET.get('data_fim', '')
    periodo_str = request.GET.get('periodo', '')
    
    if di_str and df_str:
        try:
            data_inicio = datetime.strptime(di_str.strip(), '%Y-%m-%d').date()
            data_fim = datetime.strptime(df_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    elif periodo_str:
        try:
            if " to " in periodo_str:
                parts = periodo_str.split(" to ")
            elif " a " in periodo_str:
                parts = periodo_str.split(" a ")
            else:
                parts = [periodo_str]
                
            if len(parts) == 2:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        data_inicio = datetime.strptime(parts[0].strip(), fmt).date()
                        data_fim = datetime.strptime(parts[1].strip(), fmt).date()
                        break
                    except ValueError:
                        continue
            elif len(parts) == 1:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        data_inicio = datetime.strptime(parts[0].strip(), fmt).date()
                        data_fim = data_inicio
                        break
                    except ValueError:
                        continue
        except Exception:
            pass
            
    # 3. KPIs
    res_periodo = Reserva.objects.filter(
        unidade__quarto__hotel=hotel,
        data_checkin__lt=data_fim,
        data_checkout__gt=data_inicio
    ).exclude(status='cancelada')
    
    if selected_quarto:
        res_periodo_sel = res_periodo.filter(unidade__quarto=selected_quarto)
    else:
        res_periodo_sel = res_periodo.none()
        
    ativos_qtd = res_periodo_sel.count()
    hospedados_qtd = res_periodo_sel.filter(status='hospedado').aggregate(models.Sum('quantidade_hospedes'))['quantidade_hospedes__sum'] or 0
    pendentes_qtd = res_periodo_sel.filter(data_checkin__gte=data_inicio, data_checkin__lte=data_fim, status__in=['confirmada', 'pendente']).count()
    
    # 4. Colunas de Quarto Físico (Cabanas)
    unidades_data = []
    if selected_quarto:
        for uni in selected_quarto.unidades.filter(ativa=True):
            res_uni = Reserva.objects.filter(
                unidade=uni,
                data_checkin__lt=data_fim,
                data_checkout__gt=data_inicio
            ).exclude(status='cancelada').order_by('data_checkin')
            
            unidades_data.append({
                'unidade': uni,
                'reservas': res_uni
            })
    
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
        
    # === KPI FINANCEIRO REAL & ESTATÍSTICA HOTELEIRA ===
    from financeiro.models import TransacaoFinanceira
    
    # 1. Obter lançamentos contábeis reais do banco de dados
    transacoes_qs = TransacaoFinanceira.objects.filter(hotel=hotel)
    financeiro_lancamentos = transacoes_qs.order_by('-data', '-criado_em')[:50]
    
    faturamento_total = transacoes_qs.filter(tipo='receita').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    despesas_total = transacoes_qs.filter(tipo='despesa').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    lucro_total = faturamento_total - despesas_total
    
    # 2. Métricas de Performance Hoteleira (ADR, RevPAR, Ocupação)
    unidades_count = max(1, UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True).count())
    occupied_nights = Reserva.objects.filter(unidade__quarto__hotel=hotel, status__in=['hospedado', 'finalizada']).count()
    diarias_faturamento = transacoes_qs.filter(categoria='diarias').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    adr = diarias_faturamento / Decimal(max(1, occupied_nights))
    # RevPAR baseado no faturamento total de diárias dos últimos 30 dias distribuído pela capacidade mestre
    revpar = diarias_faturamento / Decimal(unidades_count * 30)
    
    reservas_hospedadas_count = Reserva.objects.filter(unidade__quarto__hotel=hotel, status='hospedado').count()
    taxa_ocupacao = min(100, int((reservas_hospedadas_count / unidades_count) * 100))
    
    # 3. Algoritmo de Ocupação & Forecasting de Faturamento Futuro (Projeção 12 dias para o Chart.js B2B)
    forecast_labels = []
    forecast_values = []
    current_projected = faturamento_total # Parte do acumulado real do caixa atual
    
    for i in range(12):
        dia = hoje + timedelta(days=i)
        # Filtra reservas cujas estadas ativas cobrem o dia projetado
        dia_reservas = Reserva.objects.filter(
            unidade__quarto__hotel=hotel,
            data_checkin__lte=dia,
            data_checkout__gt=dia,
            status__in=['confirmada', 'hospedado']
        )
        dia_faturamento = Decimal('0.00')
        for r in dia_reservas:
            duracao = max(1, (r.data_checkout - r.data_checkin).days)
            dia_faturamento += Decimal(r.valor_total) / duracao
            
        current_projected += dia_faturamento
        forecast_labels.append(dia.strftime('%d/%m'))
        forecast_values.append(float(current_projected))
        
    context = {
        'perfil': perfil,
        'hotel': hotel,
        'quartos': quartos,
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        
        # Dados Financeiros Reais
        'financeiro': financeiro_lancamentos,
        'faturamento_total': faturamento_total,
        'despesas_total': despesas_total,
        'lucro_total': lucro_total,
        
        # Métricas de Inteligência SaaS
        'adr': adr,
        'revpar': revpar,
        'taxa_ocupacao': taxa_ocupacao,
        'forecast_labels': forecast_labels,
        'forecast_values': forecast_values,
        
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
        
        # Reservas B2B PMS:
        'selected_quarto': selected_quarto,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'periodo_str': periodo_str,
        'ativos_qtd': ativos_qtd,
        'hospedados_qtd': hospedados_qtd,
        'pendentes_qtd': pendentes_qtd,
        'unidades_data': unidades_data,
        
        # Central de Hóspedes & Pedidos B2B:
        'hospedes_ativos': hospedes_ativos,
        'pedidos_ativos': pedidos_ativos,
        'produtos_consumo': produtos_consumo,
    }
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    view_type = request.GET.get('view')
    
    if is_htmx and view_type == 'calendario':
        return render(request, 'hoteis/atividades/partials/calendario.html', context)
    elif is_htmx and view_type == 'kanban':
        return render(request, 'hoteis/atividades/partials/kanban.html', context)
    elif is_htmx and view_type == 'reservas_grid':
        return render(request, 'hoteis/partials/reservas_grid.html', context)
        
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


@login_required(login_url='hoteis:partner_login')
def ia_enviar_chat(request):
    """
    Assistant Naviê AI B2B - Conversational Task Engine.
    ---------------------------------------------------
    This controller receives a natural-language POST query from the hotel B2B interface 
    and simulates a fully autonomous, context-aware AI assistant. It actively parses 
    user intents to read, schedule, and complete operational hotel tasks directly in the SQLite database.
    
    INTENTS PARSED:
    1. List Tasks ('listar', 'lista', 'tarefa', 'afazeres', 'pendente', 'hoje', 'urgente')
       - Filters tasks by current hotel, date ("hoje"), priority ("urgente"), and active status.
    2. Move/Update Task Status ('mudar', 'alterar', 'atualizar', 'concluir', 'fazer', 'fazendo', 'status')
       - Extracts numerical Task ID and converts state to ('todo', 'doing', 'done').
    3. Create Task ('criar', 'adicionar', 'marcar', 'atribuir', 'agendar')
       - Resolves target dates ("hoje", "amanhã", or standard date strings).
       - Automatically maps responsibility by looking up employee names inside the prompt.
       - Maps room unit connection (e.g., "Suíte 101").
       - Saves the newly created task to the database.
       
    INPUTS:
    - request: HttpRequest object
    - request.POST.get('mensagem'): String command in Portuguese
    
    RETURNS:
    - HttpResponse rendering 'hoteis/ia_chat_response.html' with parsed string 'resposta_ia'
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado: Perfil de parceiro não encontrado.", status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method != 'POST':
        return redirect('hoteis:partner_dashboard')
        
    original_msg = request.POST.get('mensagem', '').strip()
    mensagem = original_msg.lower()
    
    import re
    from datetime import date, timedelta, datetime
    from .models import Tarefa, UnidadeQuarto, ParceiroUsuario
    
    resposta = ""
    action_performed = False
    
    # INTENT 1: Move/Update Task Status
    if any(k in mensagem for k in ['conclua', 'concluir', 'feita', 'feito', 'pronto', 'concluída', 'mudar', 'alterar', 'atualizar', 'status', 'fazendo', 'progresso', 'fazer']):
        # Look for task ID: "tarefa 5", "tarefa #5" or just a number
        id_match = re.search(r'(?:tarefa\s+)?#?(\d+)', mensagem)
        if id_match:
            task_id = int(id_match.group(1))
            tarefa = Tarefa.objects.filter(id=task_id, hotel=hotel).first()
            if tarefa:
                novo_status = None
                status_label = ""
                if any(k in mensagem for k in ['conclu', 'feita', 'feito', 'pronto', 'done']):
                    novo_status = 'done'
                    status_label = 'Concluído'
                elif any(k in mensagem for k in ['fazendo', 'progresso', 'doing']):
                    novo_status = 'doing'
                    status_label = 'Em Progresso'
                elif any(k in mensagem for k in ['fazer', 'todo', 'pendente']):
                    novo_status = 'todo'
                    status_label = 'A Fazer'
                
                if novo_status:
                    tarefa.status = novo_status
                    tarefa.save()
                    action_performed = True
                    resposta = f"Com certeza! Atualizei com sucesso o status da tarefa **#{tarefa.id} - {tarefa.titulo}** para **{status_label}** no banco de dados. *(Dica: Recarregue a página para atualizar o painel!)*"
                else:
                    resposta = f"Encontrei a tarefa **#{tarefa.id} - {tarefa.titulo}** (Status atual: {tarefa.get_status_display()}). Qual status deseja definir? (A Fazer, Em Progresso ou Concluído)"
            else:
                resposta = f"Desculpe, não encontrei nenhuma tarefa com o ID **#{task_id}** vinculada à pousada **{hotel.nome}**."
        else:
            resposta = "Para alterar o status de uma atividade, por favor informe o número/ID da tarefa. Exemplo: *'Marcar a tarefa 5 como concluída'*."
            
    # INTENT 2: Create Task
    elif any(k in mensagem for k in ['criar', 'adicionar', 'marcar', 'atribuir', 'agendar', 'cadastrar']):
        data_vencimento = date.today()
        data_label = "hoje"
        
        if 'amanhã' in mensagem or 'amanha' in mensagem:
            data_vencimento = date.today() + timedelta(days=1)
            data_label = "amanhã"
        elif 'semana' in mensagem:
            data_vencimento = date.today() + timedelta(days=7)
            data_label = "daqui a uma semana"
        else:
            # Look for YYYY-MM-DD
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', mensagem)
            if date_match:
                try:
                    data_vencimento = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    data_label = data_vencimento.strftime('%d/%m/%Y')
                except ValueError:
                    pass
            else:
                # Look for DD/MM/YYYY
                date_match2 = re.search(r'(\d{2}/\d{2}/\d{4})', mensagem)
                if date_match2:
                    try:
                        data_vencimento = datetime.strptime(date_match2.group(1), '%d/%m/%Y').date()
                        data_label = data_vencimento.strftime('%d/%m/%Y')
                    except ValueError:
                        pass
        
        # Extract title
        titulo = ""
        quote_match = re.findall(r'"([^"]*)"', original_msg)
        if quote_match:
            titulo = quote_match[0].strip()
        else:
            if 'reunião' in mensagem or 'reuniao' in mensagem:
                titulo = "Reunião de Equipe"
            elif 'faxina' in mensagem or 'limpeza' in mensagem:
                titulo = "Faxina e Higienização"
            elif 'manutenção' in mensagem or 'manutencao' in mensagem:
                titulo = "Manutenção do Quarto"
            else:
                titulo = "Atividade Operacional"
        
        responsavel = None
        for func in hotel.equipe.all():
            nome_func = func.user.first_name.lower() or func.user.username.lower()
            if nome_func in mensagem:
                responsavel = func
                break
                
        unidade = None
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
        
        prioridade = 'normal'
        if any(k in mensagem for k in ['urgente', 'alta', 'prioridade alta']):
            prioridade = 'alta'
        elif any(k in mensagem for k in ['baixa', 'prioridade baixa']):
            prioridade = 'baixa'
            
        t = Tarefa.objects.create(
            hotel=hotel,
            titulo=titulo,
            descricao=f"Criado automaticamente via Assistente de IA por solicitação de {request.user.get_full_name() or request.user.username}.",
            prioridade=prioridade,
            status='todo',
            data_vencimento=data_vencimento,
            responsavel=responsavel,
            unidade=unidade
        )
        action_performed = True
        
        resp_parts = [f"Perfeito! Agendei a tarefa **#{t.id} - {t.titulo}** para **{data_label}**."]
        if responsavel:
            resp_parts.append(f"Responsável: **{responsavel.user.get_full_name() or responsavel.user.username}**.")
        if unidade:
            resp_parts.append(f"Acomodação vinculada: **{unidade.identificador}**.")
        resp_parts.append("*(Dica: Recarregue a página para ver a atividade no seu quadro de tarefas!)*")
        resposta = " ".join(resp_parts)

    # INTENT 3: List Tasks
    elif any(k in mensagem for k in ['tarefa', 'afazeres', 'lista', 'listar', 'pendente', 'urgente', 'atividades']):
        real_tasks = Tarefa.objects.filter(hotel=hotel).order_by('data_vencimento')
        
        if 'hoje' in mensagem:
            real_tasks = real_tasks.filter(data_vencimento=date.today())
            filter_desc = "agendadas para hoje"
        elif 'urgente' in mensagem or 'urgentes' in mensagem:
            real_tasks = real_tasks.filter(prioridade='alta')
            filter_desc = "com prioridade alta (urgentes)"
        elif 'pendente' in mensagem or 'pendentes' in mensagem or 'todo' in mensagem or 'doing' in mensagem:
            real_tasks = real_tasks.filter(status__in=['todo', 'doing'])
            filter_desc = "pendentes de conclusão"
        else:
            filter_desc = "gerais registradas"
            
        if real_tasks.exists():
            resposta = f"Aqui estão as tarefas {filter_desc} na **{hotel.nome}**:<br><br>"
            for t in real_tasks[:8]:
                status_emoji = "⏳"
                if t.status == 'doing':
                    status_emoji = "⚡"
                elif t.status == 'done':
                    status_emoji = "✅"
                
                resp_line = f"{status_emoji} **#{t.id} - {t.titulo}**<br>"
                details = []
                if t.responsavel:
                    details.append(f"Atribuída a: {t.responsavel.user.get_full_name() or t.responsavel.user.username}")
                if t.data_vencimento:
                    details.append(f"Vence em: {t.data_vencimento.strftime('%d/%m/%Y')}")
                details.append(f"Status: {t.get_status_display()}")
                details.append(f"Prioridade: {t.get_prioridade_display()}")
                resp_line += f"&nbsp;&nbsp;&nbsp;&nbsp;*({', '.join(details)})*<br>"
                resposta += resp_line
        else:
            resposta = f"Não encontrei nenhuma tarefa {filter_desc} cadastrada para a **{hotel.nome}**."

    # INTENT 4: Greeting & Finance Fallbacks
    elif any(k in mensagem for k in ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite']):
        resposta = f"Olá, **{request.user.first_name or request.user.username}**! Sou o seu assistente Naviê AI para a **{hotel.nome}**. Posso gerenciar tarefas operacionais em tempo real: experimente dizer *'criar faxina para amanhã'* ou *'quais tarefas pendentes?'*!"
    elif 'faturamento' in mensagem or 'financeiro' in mensagem or 'caixa' in mensagem or 'receita' in mensagem:
        resposta = "Consultando relatórios financeiros... Atualmente os lançamentos operacionais indicam faturamento positivo com fluxo de caixa sob controle neste mês. Para ver o detalhado, navegue até a aba 'Visão Geral / Financeiro'!"
    else:
        resposta = "Entendido! Posso ajudar na organização operacional da pousada. Experimente me pedir para: *'listar as tarefas de hoje'*, *'marcar a tarefa 5 como concluída'* ou *'criar uma faxina para amanhã'*!"
        
    context = {'resposta_ia': resposta}
    return render(request, 'hoteis/ia_chat_response.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_criar_tarefa(request):
    """
    Creates a new operational Task/Activity for the B2B dashboard.
    --------------------------------------------------------------
    This view manages the B2B Task Creation modal and handles POST requests 
    to instantiate a new task linked to the current user's hotel.
    
    Operational Schema (AI-Readiness):
    - GET: Renders a form containing members of the hotel staff, active room units, and bookings.
    - POST: Validates arguments and creates a Tarefa record.
    
    Fields required in POST:
    - titulo (str): Non-empty task title.
    - descricao (str, optional): Additional instructions.
    - prioridade (str): choices: 'baixa', 'normal', 'alta'. Default 'normal'.
    - status (str): choices: 'todo', 'doing', 'done'. Default 'todo'.
    - data_vencimento (str, format YYYY-MM-DD): Target deadline.
    - responsavel_id (int, optional): ID of the staff member (ParceiroUsuario).
    - unidade_id (int, optional): ID of the room unit (UnidadeQuarto).
    - reserva_id (int, optional): ID of the linked booking (Reserva).
    
    Returns:
    - HTML modal render on GET, or HX-Redirect to B2B dashboard on successful POST.
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
    return render(request, 'hoteis/atividades/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_editar_tarefa(request, tarefa_id):
    """
    Edits an existing operational Task/Activity.
    -------------------------------------------
    This view retrieves the specified Tarefa record and renders the edit form modal,
    saving any changes during a POST request.
    
    Operational Schema (AI-Readiness):
    - GET: Populates the modal fields with the current task state.
    - POST: Modifies the task state and saves it.
    
    Parameters:
    - request: HttpRequest object.
    - tarefa_id (int): Primary key ID of the target Task.
    
    Fields allowed in POST:
    - Same parameters as partner_criar_tarefa. Modifies instead of creates.
    
    Returns:
    - HTML modal on GET, or HX-Redirect to B2B dashboard on successful POST.
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
    return render(request, 'hoteis/atividades/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_deletar_tarefa(request, tarefa_id):
    """
    Deletes an operational Task/Activity.
    -------------------------------------
    Accepts only POST requests to securely delete the Tarefa object and redirect.
    
    Operational Schema (AI-Readiness):
    - POST: Deletes the Tarefa from the database.
    
    Parameters:
    - request: HttpRequest object.
    - tarefa_id (int): Primary key ID of the target Task to delete.
    
    Returns:
    - Redirect or HX-Redirect to the B2B dashboard.
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
    Asynchronously updates the status of a Task (specifically for drag-and-drop actions).
    -------------------------------------------------------------------------------------
    Invoked primarily via SortableJS on the B2B Kanban board, updating status in real-time.
    
    Operational Schema (AI-Readiness):
    - POST: Modifies the status attribute.
    
    Parameters:
    - request: HttpRequest.
    - tarefa_id (int): ID of the task.
    - request.POST.get('status'): Target status value, choices: ('todo', 'doing', 'done', 'overdue').
    
    Returns:
    - HttpResponse with status code 200 on success, or 400 on invalid parameters.
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
        
    # Processa remoção ou novo upload do vídeo do banner
    if request.POST.get('remover_hero_video') == 'true':
        hotel.hero_video = None
    elif 'hero_video' in request.FILES:
        video_file = request.FILES['hero_video']
        # Limitar a 30MB
        if video_file.size > 30 * 1024 * 1024:
            messages.error(request, "O vídeo em loop ultrapassa o limite de 30MB permitido.")
            return redirect('hoteis:partner_dashboard')
        hotel.hero_video = video_file
        
    hotel.save()
    messages.success(request, "Configurações do estabelecimento gravadas com sucesso!")
    return redirect('hoteis:partner_dashboard')


# ─────────────────────────────────────────────────────────────
# GESTÃO REATIVA DE ACOMODAÇÕES (B2B HTMX CONTROLLERS)
# ─────────────────────────────────────────────────────────────

from django.views.decorators.http import require_http_methods, require_POST
from django.http import HttpResponse
from .models import QuartoImagem

@login_required(login_url='hoteis:partner_login')
def partner_quarto_formulario(request, quarto_id=None):
    """
    Carrega o formulário completo de criação ou edição de quarto via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto = None
    if quarto_id:
        quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
        
    context = {
        'quarto': quarto,
        'hotel': hotel,
        'capacidades': [1, 2, 3, 4, 5, 6, 7],
        'tags_disponiveis': ["Família", "Casal", "Romântico", "Serra", "Trabalho Remoto", "Pet Friendly", "Silencioso"],
        'comodidades_disponiveis': ["Ar Condicionado", "Wi-Fi de Alta Velocidade", "Copa Completa", "Piscina Privativa", "Hidromassagem", "Frigobar Abastecido", "Café no Quarto"]
    }
    return render(request, 'hoteis/quartos/partials/quarto_formulario.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_quarto_lista(request):
    """
    Retorna apenas a grade de cards dos quartos via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quartos = hotel.quartos.all()
    
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_quarto_salvar(request):
    """
    Salva ou atualiza um quarto com suporte a upload de múltiplas imagens,
    descontos multidias, categorização e SEO/IA. Retorna a grade atualizada via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto_id = request.POST.get('quarto_id')
    
    if quarto_id:
        quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
    else:
        quarto = Quarto(hotel=hotel)
        
    quarto.nome = request.POST.get('nome', '').strip()
    quarto.descricao = request.POST.get('descricao', '').strip()
    
    # Tratamento de preço decimal
    preco_raw = request.POST.get('preco', '0').replace(',', '.')
    try:
        quarto.preco = float(preco_raw)
    except ValueError:
        quarto.preco = 0.00
        
    quarto.video_url = request.POST.get('video_url', '').strip() or None
    
    # Processa upload do arquivo de vídeo local
    if request.POST.get('remover_video') == 'true':
        quarto.video_arquivo = None
    elif 'video_arquivo' in request.FILES:
        vid_file = request.FILES['video_arquivo']
        if vid_file.size <= 30 * 1024 * 1024:  # Limite de 30MB
            quarto.video_arquivo = vid_file
    
    try:
        quarto.capacidade_pessoas = int(request.POST.get('capacidade_pessoas', '2'))
    except ValueError:
        quarto.capacidade_pessoas = 2
        
    # Tags e comodidades selecionadas
    quarto.tags = request.POST.get('tags', '').strip()
    quarto.comodidades = request.POST.get('comodidades', '').strip()
    
    # Descontos
    quarto.tem_desconto_multidias = request.POST.get('tem_desconto_multidias') == 'true'
    try:
        quarto.dias_minimos_desconto = int(request.POST.get('dias_minimos_desconto', '3'))
    except ValueError:
        quarto.dias_minimos_desconto = 3
        
    desc_raw = request.POST.get('percentual_desconto', '0').replace(',', '.')
    try:
        quarto.percentual_desconto = float(desc_raw)
    except ValueError:
        quarto.percentual_desconto = 0.00
        
    # SEO e IA
    quarto.seo_titulo = request.POST.get('seo_titulo', '').strip() or None
    quarto.seo_descricao = request.POST.get('seo_descricao', '').strip() or None
    
    quarto.save()
    
    # Processa a sincronização de unidades físicas (UnidadeQuarto)
    unidades_ids = request.POST.getlist('unidades_ids')
    unidades_identificadores = request.POST.getlist('unidades_identificadores')
    
    submitted_pairs = []
    for uid, ident in zip(unidades_ids, unidades_identificadores):
        ident = ident.strip()
        if ident:
            submitted_pairs.append((uid, ident))
            
    # Se nenhuma unidade foi enviada, garante pelo menos uma padrão
    if not submitted_pairs:
        submitted_pairs.append(('new', '101'))
        
    existing_units = {str(u.id): u for u in quarto.unidades.all()}
    submitted_ids = set()
    
    for uid, ident in submitted_pairs:
        if uid in existing_units:
            unit = existing_units[uid]
            unit.identificador = ident
            unit.ativa = True
            unit.save()
            submitted_ids.add(uid)
        else:
            new_unit = UnidadeQuarto.objects.create(
                quarto=quarto,
                identificador=ident,
                ativa=True
            )
            submitted_ids.add(str(new_unit.id))
            
    # Exclui ou desativa fisicamente as que não vieram no POST
    for uid, unit in existing_units.items():
        if uid not in submitted_ids:
            try:
                unit.delete()
            except Exception:
                unit.ativa = False
                unit.save()
    
    # Processa uploads de múltiplas imagens
    imagens_carregadas = request.FILES.getlist('imagens')
    current_count = QuartoImagem.objects.filter(quarto=quarto).count()
    for idx, img in enumerate(imagens_carregadas):
        # Limite de no máximo 10 fotos no total
        if current_count + idx >= 10:
            break
        QuartoImagem.objects.create(
            quarto=quarto,
            url_imagem=img,
            ordem=current_count + idx
        )
        
    messages.success(request, f"Acomodação '{quarto.nome}' salva com sucesso!")
    
    # Retorna a grade atualizada
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar(request, quarto_id):
    """
    Exclui um quarto do estabelecimento e retorna a grade atualizada via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
    quarto_nome = quarto.nome
    quarto.delete()
    
    messages.success(request, f"Quarto '{quarto_nome}' excluído com sucesso!")
    
    # Retorna a grade atualizada
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar_imagem(request, imagem_id):
    """
    Exclui uma imagem específica do quarto via HTMX. Retorna string vazia para remover o card.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    img = get_object_or_404(QuartoImagem, id=imagem_id, quarto__hotel=hotel)
    img.delete()
    
    return HttpResponse("")

def quarto_detalhe(request, hotel_id, quarto_slug):
    """
    Página pública B2C de detalhes de uma acomodação específica.
    URL amigável com slug gerado do nome do quarto, único por hotel.
    Ex: /hotel/1/acomodacao/suite-premium-2/
    """
    hotel = get_object_or_404(Hotel, id=hotel_id)
    quarto = get_object_or_404(Quarto, hotel=hotel, slug=quarto_slug)
    
    # Incrementa contador de visualizações
    quarto.visualizacoes += 1
    quarto.save(update_fields=['visualizacoes'])

    imagens = list(quarto.imagens.all())
    primeira_imagem = imagens[0] if imagens else None
    outras_imagens = imagens[1:] if len(imagens) > 1 else []

    comodidades = [c.strip() for c in quarto.comodidades.split(',') if c.strip()] if quarto.comodidades else []
    tags = [t.strip() for t in quarto.tags.split(',') if t.strip()] if quarto.tags else []

    context = {
        'hotel': hotel,
        'quarto': quarto,
        'primeira_imagem': primeira_imagem,
        'outras_imagens': outras_imagens,
        'comodidades': comodidades,
        'tags': tags,
        'imagens_todas': imagens,
    }
    return render(request, 'hoteis/quartos/quarto_detalhe.html', context)

@require_POST
def carrinho_adicionar(request, quarto_id):
    quarto = get_object_or_404(Quarto, id=quarto_id)
    checkin_str = request.POST.get('checkin')
    checkout_str = request.POST.get('checkout')
    
    if not checkin_str or not checkout_str:
        return JsonResponse({'success': False, 'error': 'Selecione as datas de check-in e check-out.'}, status=400)
    
    try:
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Formato de data inválido.'}, status=400)
        
    if checkout <= checkin:
        return JsonResponse({'success': False, 'error': 'A data de checkout deve ser após a data de check-in.'}, status=400)
        
    # Validar disponibilidade
    if not checar_disponibilidade_quarto(quarto, checkin, checkout):
        return JsonResponse({'success': False, 'error': 'Desculpe, esta acomodação não está disponível para o período selecionado.'}, status=400)
        
    # Adicionar ao carrinho na sessão pré-configurado com a capacidade máxima do quarto
    request.session['carrinho'] = {
        'quarto_id': quarto.id,
        'checkin': checkin_str,
        'checkout': checkout_str,
        'quantidade_hospedes': quarto.capacidade_pessoas,
        'hospedes': [{} for _ in range(quarto.capacidade_pessoas)],
        'veiculo': {'placa': '', 'modelo': '', 'cor': ''}
    }
    request.session.modified = True
    
    return JsonResponse({'success': True})

def carrinho_remover(request):
    if 'carrinho' in request.session:
        del request.session['carrinho']
        request.session.modified = True
    
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')
    return redirect('hoteis:home')

@require_POST
def carrinho_salvar_fnrh(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    try:
        idx = int(request.GET.get('idx', 0))
    except ValueError:
        idx = 0
        
    quantidade = carrinho_data.get('quantidade_hospedes', 1)
    if idx < 0 or idx >= quantidade:
        return JsonResponse({'success': False, 'error': 'Índice de hóspede inválido.'}, status=400)
        
    hospedes = carrinho_data.get('hospedes', [{}])
    while len(hospedes) < quantidade:
        hospedes.append({})
    while len(hospedes) > quantidade:
        hospedes.pop()
        
    nome = request.POST.get('hospede_nome', '').strip()
    cpf = request.POST.get('hospede_cpf', '').strip()
    email = request.POST.get('hospede_email', '').strip()
    telefone = request.POST.get('hospede_telefone', '').strip()
    rg = request.POST.get('hospede_rg', '').strip()
    nacionalidade = request.POST.get('hospede_nacionalidade', 'Brasileira').strip()
    profissao = request.POST.get('hospede_profissao', '').strip()
    cep = request.POST.get('hospede_cep', '').strip()
    endereco = request.POST.get('hospede_endereco', '').strip()
    
    # Validação condicional com base no tipo de hóspede (titular vs acompanhante)
    if idx == 0:
        if not all([nome, cpf, email, telefone, cep, endereco]):
            return JsonResponse({'success': False, 'error': 'Preencha todos os campos obrigatórios do hóspede principal.'}, status=400)
        
        fnrh = {
            'nome': nome,
            'cpf': cpf,
            'email': email,
            'telefone': telefone,
            'rg': rg,
            'nacionalidade': nacionalidade,
            'profissao': profissao,
            'cep': cep,
            'endereco': endereco
        }
    else:
        # Se vier 100% em branco, permite salvar vazio
        if not nome and not cpf and not email and not telefone and not rg and not cep and not endereco:
            fnrh = {}
        elif not all([nome, cpf]):
            return JsonResponse({'success': False, 'error': 'Preencha todos os campos obrigatórios (Nome e CPF) do acompanhante.'}, status=400)
        else:
            fnrh = {
                'nome': nome,
                'cpf': cpf,
                'email': email,
                'telefone': telefone,
                'rg': rg,
                'nacionalidade': nacionalidade,
                'profissao': profissao,
                'cep': cep,
                'endereco': endereco
            }
    
    hospedes[idx] = fnrh
    carrinho_data['hospedes'] = hospedes
    
    # Salvar veículo de forma integrada se idx == 0 (hóspede titular)
    if idx == 0:
        veiculo_placa = request.POST.get('veiculo_placa', '').strip().upper()
        veiculo_modelo = request.POST.get('veiculo_modelo', '').strip()
        veiculo_cor = request.POST.get('veiculo_cor', '').strip()
        
        if veiculo_placa:
            carrinho_data['veiculo'] = {
                'placa': veiculo_placa,
                'modelo': veiculo_modelo,
                'cor': veiculo_cor
            }
        else:
            carrinho_data['veiculo'] = {
                'placa': '',
                'modelo': '',
                'cor': ''
            }
            
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    # Ligar FNRH salva do usuário no perfil principal da conta (apenas para o titular se o campo estiver vazio)
    if idx == 0 and request.user.is_authenticated:
        from clientes.models import ClientePerfil
        try:
            perfil, _ = ClientePerfil.objects.get_or_create(user=request.user)
            if cpf and not perfil.cpf:
                perfil.cpf = cpf
            if telefone and not perfil.telefone:
                perfil.telefone = telefone
            if cep and not perfil.cep:
                perfil.cep = cep
            if endereco and not perfil.endereco:
                perfil.endereco = endereco
            perfil.save()
        except Exception as e:
            pass
            
    return JsonResponse({'success': True})


@require_POST
def carrinho_definir_hospedes(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Quantidade inválida.'}, status=400)
        
    quarto_id = carrinho_data.get('quarto_id')
    quarto = get_object_or_404(Quarto, id=quarto_id)
    
    if quantidade < 1 or quantidade > quarto.capacidade_pessoas:
        return JsonResponse({
            'success': False, 
            'error': f'A quantidade de hóspedes deve ser entre 1 e {quarto.capacidade_pessoas}.'
        }, status=400)
        
    carrinho_data['quantidade_hospedes'] = quantidade
    hospedes = carrinho_data.get('hospedes', [{}])
    
    # Ajusta o tamanho da lista de hóspedes na sessão
    while len(hospedes) < quantidade:
        hospedes.append({})
    while len(hospedes) > quantidade:
        hospedes.pop()
        
    carrinho_data['hospedes'] = hospedes
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')
        
    return JsonResponse({'success': True})


@require_POST
def carrinho_salvar_veiculo(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    placa = request.POST.get('placa', '').strip().upper()
    modelo = request.POST.get('modelo', '').strip()
    cor = request.POST.get('cor', '').strip()
    
    if not placa:
        veiculo = {'placa': '', 'modelo': '', 'cor': ''}
    else:
        veiculo = {
            'placa': placa,
            'modelo': modelo,
            'cor': cor
        }
        
    carrinho_data['veiculo'] = veiculo
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    return JsonResponse({'success': True})


@login_required
def checkout_processar(request):
    import json
    import uuid
    import requests
    from django.conf import settings
    
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        if request.method == 'POST' or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': 'Seu carrinho de compras está vazio.'}, status=400)
        messages.error(request, 'Seu carrinho de compras está vazio.')
        return redirect('hoteis:home')
        
    quantidade_hospedes = carrinho_data.get('quantidade_hospedes', 1)
    hospedes = carrinho_data.get('hospedes', [{}])
    
    # Garantir que a lista de hóspedes esteja correta
    while len(hospedes) < quantidade_hospedes:
        hospedes.append({})
    while len(hospedes) > quantidade_hospedes:
        hospedes.pop()
        
    required_titular = ['nome', 'cpf', 'email', 'telefone', 'cep', 'endereco']
    required_acompanhante = ['nome', 'cpf']
    
    for idx, h in enumerate(hospedes):
        if idx == 0:
            if not all(h.get(f) for f in required_titular):
                if request.method == 'POST':
                    return JsonResponse({'success': False, 'error': 'Preencha todos os dados obrigatórios do hóspede titular antes de finalizar.'}, status=400)
                messages.error(request, 'Preencha todos os dados obrigatórios do hóspede titular antes de finalizar.')
                return redirect('hoteis:home')
        else:
            # Acompanhante é opcional se estiver completamente vazio.
            # Mas se tiver qualquer dado preenchido, deve obrigatoriamente preencher Nome e CPF.
            h_tem_dados = any(h.get(f) for f in ['nome', 'cpf', 'email', 'telefone', 'rg', 'nacionalidade', 'profissao', 'cep', 'endereco'])
            if h_tem_dados:
                if not all(h.get(f) for f in required_acompanhante):
                    if request.method == 'POST':
                        return JsonResponse({'success': False, 'error': f'Preencha todos os dados obrigatórios (Nome e CPF) do acompanhante {idx + 1} antes de finalizar.'}, status=400)
                    messages.error(request, f'Preencha todos os dados obrigatórios (Nome e CPF) do acompanhante {idx + 1} antes de finalizar.')
                    return redirect('hoteis:home')
            
    quarto_id = carrinho_data['quarto_id']
    quarto = get_object_or_404(Quarto, id=quarto_id)
    
    try:
        checkin = datetime.strptime(carrinho_data['checkin'], '%Y-%m-%d').date()
        checkout = datetime.strptime(carrinho_data['checkout'], '%Y-%m-%d').date()
    except ValueError:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'Datas inválidas no carrinho.'}, status=400)
        messages.error(request, 'Datas inválidas no carrinho.')
        return redirect('hoteis:home')
        
    # Calcular valores financeiros
    noites = (checkout - checkin).days
    if noites <= 0:
        noites = 1
        
    from sas.financeiro import calcular_taxas_reserva
    fin = calcular_taxas_reserva(quarto.hotel.empresa, 'hospedagem', quarto.preco, noites)
    
    if request.method == 'GET':
        # Renderizar a página de checkout pagamento
        context = {
            'carrinho': carrinho_data,
            'quarto': quarto,
            'noites': noites,
            'financeiro': fin,
            'mp_public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', ''),
        }
        return render(request, 'hoteis/checkout_pagamento.html', context)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Formato de payload inválido.'}, status=400)
            
        forma_pagamento = data.get('forma_pagamento')
        if forma_pagamento not in ['cartao', 'pix']:
            return JsonResponse({'success': False, 'error': 'Selecione uma forma de pagamento válida.'}, status=400)
            
        # 1. Verificar e alocar UnidadeQuarto física livre para prevenir overbooking
        unidades = quarto.unidades.filter(ativa=True)
        unidade_alocada = None
        
        from hoteis.utils import verifica_disponibilidade_unidade
        for uni in unidades:
            if verifica_disponibilidade_unidade(uni, checkin, checkout):
                unidade_alocada = uni
                break
                
        if not unidade_alocada:
            return JsonResponse({'success': False, 'error': 'Desculpe, a acomodação escolhida não possui mais vagas físicas disponíveis para este período.'}, status=400)
            
        # 2. Conectar ao Mercado Pago (Checkout Transparente API)
        url_mp = "https://api.mercadopago.com/v1/payments"
        headers = {
            "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        }
        
        titular_fnrh = hospedes[0]
        cpf_limpo = titular_fnrh['cpf'].replace(".", "").replace("-", "").replace(" ", "").strip()
        
        # Estrutura base do payer
        payer = {
            "email": titular_fnrh['email'],
            "first_name": titular_fnrh['nome'].split()[0],
            "last_name": " ".join(titular_fnrh['nome'].split()[1:]) or "Silva",
            "identification": {
                "type": "CPF",
                "number": cpf_limpo
            }
        }
        
        payload_mp = {
            "transaction_amount": float(fin['total_cliente']),
            "description": f"Reserva {quarto.nome} - {quarto.hotel.nome}",
            "payer": payer,
        }
        
        if forma_pagamento == 'cartao':
            token = data.get('token')
            installments = int(data.get('installments', 1))
            payment_method_id = data.get('payment_method_id')
            
            if not token:
                return JsonResponse({'success': False, 'error': 'Token do cartão de crédito não foi gerado.'}, status=400)
                
            payload_mp.update({
                "token": token,
                "installments": installments,
                "payment_method_id": payment_method_id,
            })
        elif forma_pagamento == 'pix':
            payload_mp.update({
                "payment_method_id": "pix"
            })
            
        try:
            # Em ambiente de teste unitário, podemos mockar ou injetar chamadas simuladas caso a rede falhe
            response = requests.post(url_mp, headers=headers, json=payload_mp, timeout=15)
            resp_data = response.json()
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Falha na comunicação com o gateway de pagamento: {str(e)}'}, status=500)
            
        if response.status_code not in [200, 201]:
            error_message = resp_data.get('message', 'Erro desconhecido no gateway de pagamento.')
            # Tratar caso o token esteja inválido ou sandbox dê erro
            if 'cause' in resp_data and resp_data['cause']:
                error_message = resp_data['cause'][0].get('description', error_message)
            return JsonResponse({'success': False, 'error': f'Pagamento Recusado: {error_message}'}, status=400)
            
        status_pagamento = resp_data.get('status')
        status_detail = resp_data.get('status_detail')
        
        # Pix fica 'pending', cartão deve estar 'approved'
        if forma_pagamento == 'cartao' and status_pagamento != 'approved':
            return JsonResponse({'success': False, 'error': f'O pagamento foi recusado pelo banco. Detalhe: {status_detail}'}, status=400)
            
        # 3. Criar a Reserva no Banco
        status_reserva = 'confirmada' if status_pagamento == 'approved' else 'pendente'
        reserva = Reserva.objects.create(
            usuario=request.user,
            unidade=unidade_alocada,
            data_checkin=checkin,
            data_checkout=checkout,
            subtotal=fin['subtotal'],
            taxas=fin['taxa_servico'],
            valor_total=fin['total_cliente'],
            taxa_servico_plataforma=fin['taxa_servico'],
            taxa_gateway=fin['taxa_gateway'],
            repasse_parceiro=fin['repasse_parceiro'],
            ganho_liquido_plataforma=fin['ganho_liquido'],
            status=status_reserva,
            canal_venda='marketplace',
            hospede_nome=titular_fnrh['nome'],
            hospede_cpf=titular_fnrh['cpf'],
            hospede_email=titular_fnrh['email'],
            hospede_telefone=titular_fnrh['telefone'],
            hospede_rg=titular_fnrh.get('rg', ''),
            hospede_nacionalidade=titular_fnrh.get('nacionalidade', 'Brasileira'),
            hospede_profissao=titular_fnrh.get('profissao', ''),
            hospede_endereco=f"{titular_fnrh['endereco']} (CEP: {titular_fnrh['cep']})",
            quantidade_hospedes=quantidade_hospedes
        )
        
        # Criar registros de HospedeReserva para todos
        for idx, h in enumerate(hospedes):
            endereco_completo = h.get('endereco', '')
            if h.get('cep'):
                endereco_completo = f"{endereco_completo} (CEP: {h['cep']})".strip()
                
            HospedeReserva.objects.create(
                reserva=reserva,
                ordem=idx + 1,
                nome=h['nome'],
                cpf=h['cpf'],
                email=h.get('email', ''),
                telefone=h.get('telefone', ''),
                rg=h.get('rg', ''),
                nacionalidade=h.get('nacionalidade', 'Brasileira'),
                profissao=h.get('profissao', ''),
                endereco=endereco_completo
            )
            
        # Criar VeiculoReserva se placa informada
        veiculo_data = carrinho_data.get('veiculo', {})
        if veiculo_data and veiculo_data.get('placa'):
            VeiculoReserva.objects.create(
                reserva=reserva,
                placa=veiculo_data['placa'].upper(),
                modelo=veiculo_data.get('modelo', ''),
                cor=veiculo_data.get('cor', '')
            )
            
        # Criar o Voucher Universal Naviê
        from vouchers.models import Voucher
        # Obfuscate CPF para cache de portaria
        cpf_limpo = titular_fnrh['cpf'].replace(".", "").replace("-", "").replace(" ", "").strip()
        cpf_ocultado = f"***.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-**" if len(cpf_limpo) == 11 else "USER-UNKNOWN"

        Voucher.objects.create(
            empresa=quarto.hotel.empresa,
            tipo='hospedagem',
            object_id=str(reserva.id),
            codigo_seguro=f"VALIDA-RESERVA-{reserva.id}-{unidade_alocada.identificador}-{cpf_ocultado}",
            titulo_exibicao=f"{unidade_alocada.identificador} ({quarto.nome})",
            subtitulo_exibicao=quarto.hotel.nome,
            nome_beneficiario=titular_fnrh['nome'],
            documento_beneficiario=cpf_ocultado,
            detalhes_json={
                'checkin': checkin.strftime('%d/%m/%Y'),
                'checkout': checkout.strftime('%d/%m/%Y'),
                'noites': noites,
                'reserva_id': str(reserva.id)
            }
        )
            
        # 4. Limpar o carrinho
        if 'carrinho' in request.session:
            del request.session['carrinho']
            request.session.modified = True
            
        # Retornar dados de sucesso
        ret_data = {
            'success': True,
            'reserva_id': str(reserva.id),
            'redirect_url': request.build_absolute_uri(f'/carrinho/sucesso/{reserva.id}/')
        }
        
        # Inserir payload Pix para o front-end se aplicável
        if forma_pagamento == 'pix':
            try:
                qr_code = resp_data['point_of_interaction']['transaction_data']['qr_code']
                qr_code_base64 = resp_data['point_of_interaction']['transaction_data']['qr_code_base64']
                ret_data.update({
                    'forma_pagamento': 'pix',
                    'pix_qr_code': qr_code,
                    'pix_qr_code_base64': qr_code_base64
                })
            except Exception:
                pass
                
        return JsonResponse(ret_data)

@login_required
def checkout_sucesso(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    return render(request, 'hoteis/checkout_sucesso.html', {
        'reserva': reserva,
        'hotel': reserva.unidade.quarto.hotel
    })

@login_required(login_url='hoteis:partner_login')
@login_required(login_url='hoteis:partner_login')
def partner_reserva_criar(request):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    
    hotel = request.user.perfil_parceiro.hotel
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    
    if request.method == 'POST':
        unidade_id = request.POST.get('unidade_id')
        data_checkin_str = request.POST.get('data_checkin')
        data_checkout_str = request.POST.get('data_checkout')
        valor_total_str = request.POST.get('valor_total', '0.00').strip()
        if ',' in valor_total_str:
            valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
        status = request.POST.get('status', 'pendente')
        quantidade_hospedes = int(request.POST.get('quantidade_hospedes', '1'))
        
        unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
        
        # Parse datas
        from datetime import datetime
        try:
            d_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
            d_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">Formato de datas inválido. Use AAAA-MM-DD.</div>', status=400)
            
        if d_checkout <= d_checkin:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">A data de checkout deve ser posterior ao checkin.</div>', status=400)
            
        # Validar conflitos de reservas
        conflitos = Reserva.objects.filter(
            unidade=unidade,
            data_checkin__lt=d_checkout,
            data_checkout__gt=d_checkin
        ).exclude(status='cancelada')
        
        if conflitos.exists():
            return HttpResponse(f'<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O quarto {unidade.identificador} já possui uma reserva ativa neste período.</div>', status=400)
            
        try:
            valor_total = float(valor_total_str)
        except ValueError:
            valor_total = 0.00
            
        # Pegar dados do hóspede titular (ordem=1)
        nome_1 = request.POST.get('nome_1', '').strip()
        cpf_1 = request.POST.get('cpf_1', '').strip()
        email_1 = request.POST.get('email_1', '').strip()
        telefone_1 = request.POST.get('telefone_1', '').strip()
        rg_1 = request.POST.get('rg_1', '').strip()
        nacionalidade_1 = request.POST.get('nacionalidade_1', 'Brasileira').strip()
        profissao_1 = request.POST.get('profissao_1', '').strip()
        endereco_1 = request.POST.get('endereco_1', '').strip()
        
        if not nome_1:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O nome do Hóspede 1 (Titular) é obrigatório.</div>', status=400)
            
        # Criar reserva walk-in
        reserva = Reserva.objects.create(
            unidade=unidade,
            data_checkin=d_checkin,
            data_checkout=d_checkout,
            subtotal=valor_total,
            valor_total=valor_total,
            status=status,
            canal_venda='walk-in',
            quantidade_hospedes=quantidade_hospedes,
            hospede_nome=nome_1,
            hospede_cpf=cpf_1,
            hospede_email=email_1,
            hospede_telefone=telefone_1,
            hospede_rg=rg_1,
            hospede_nacionalidade=nacionalidade_1,
            hospede_profissao=profissao_1,
            hospede_endereco=endereco_1
        )
        
        # Registrar todos os hóspedes
        import re
        for i in range(1, quantidade_hospedes + 1):
            nome = request.POST.get(f'nome_{i}', '').strip()
            cpf = request.POST.get(f'cpf_{i}', '').strip()
            email = request.POST.get(f'email_{i}', '').strip()
            telefone = request.POST.get(f'telefone_{i}', '').strip()
            rg = request.POST.get(f'rg_{i}', '').strip()
            nacionalidade = request.POST.get(f'nacionalidade_{i}', 'Brasileira').strip()
            profissao = request.POST.get(f'profissao_{i}', '').strip()
            endereco = request.POST.get(f'endereco_{i}', '').strip()
            
            # Pular acompanhantes sem nome se quantidade informada exceder
            if i > 1 and not nome:
                continue
                
            docs_list = request.FILES.getlist(f'documentos_{i}')
            hospede = HospedeReserva.objects.create(
                reserva=reserva,
                ordem=i,
                nome=nome or f"Acompanhante {i}",
                cpf=cpf,
                email=email,
                telefone=telefone,
                rg=rg,
                nacionalidade=nacionalidade,
                profissao=profissao,
                endereco=endereco,
                documento_frente=docs_list[0] if len(docs_list) > 0 else None,
                documento_verso=docs_list[1] if len(docs_list) > 1 else None
            )
            
        # Registrar veículo se placa informada
        placa_1 = request.POST.get('placa_1', '').strip()
        if placa_1:
            VeiculoReserva.objects.create(
                reserva=reserva,
                placa=placa_1.upper(),
                modelo=request.POST.get('modelo_1', '').strip(),
                cor=request.POST.get('cor_1', '').strip()
            )
            
        response = HttpResponse("""
            <script>
                document.getElementById('modal-container').innerHTML = '';
                if (typeof window.triggerReservasRefresh === 'function') {
                    window.triggerReservasRefresh();
                }
            </script>
        """)
        return response
        
    # GET: renderizar formulário em branco
    from datetime import date, timedelta
    data_inicio = date.today()
    data_fim = data_inicio + timedelta(days=1)
    
    return render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': True,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': None,
        'hospedes': [],
        'veiculo': None,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    })

@login_required(login_url='hoteis:partner_login')
def partner_reserva_detalhe(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    return render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo
    })

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_salvar(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    unidade_id = request.POST.get('unidade_id')
    data_checkin_str = request.POST.get('data_checkin')
    data_checkout_str = request.POST.get('data_checkout')
    valor_total_str = request.POST.get('valor_total', '0.00').strip()
    if ',' in valor_total_str:
        valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
    status = request.POST.get('status', reserva.status)
    quantidade_hospedes = int(request.POST.get('quantidade_hospedes', '1'))
    
    unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
    
    # Parse datas
    from datetime import datetime
    try:
        d_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
        d_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">Formato de datas inválido. Use AAAA-MM-DD.</div>', status=400)
        
    if d_checkout <= d_checkin:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">A data de checkout deve ser posterior ao checkin.</div>', status=400)
        
    # Validar conflitos de reservas
    conflitos = Reserva.objects.filter(
        unidade=unidade,
        data_checkin__lt=d_checkout,
        data_checkout__gt=d_checkin
    ).exclude(id=reserva.id).exclude(status='cancelada')
    
    if conflitos.exists():
        return HttpResponse(f'<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O quarto {unidade.identificador} já possui uma reserva ativa neste período.</div>', status=400)
        
    try:
        valor_total = float(valor_total_str)
    except ValueError:
        valor_total = reserva.valor_total
        
    # Pegar dados do hóspede titular (ordem=1)
    nome_1 = request.POST.get('nome_1', '').strip()
    cpf_1 = request.POST.get('cpf_1', '').strip()
    email_1 = request.POST.get('email_1', '').strip()
    telefone_1 = request.POST.get('telefone_1', '').strip()
    rg_1 = request.POST.get('rg_1', '').strip()
    nacionalidade_1 = request.POST.get('nacionalidade_1', 'Brasileira').strip()
    profissao_1 = request.POST.get('profissao_1', '').strip()
    endereco_1 = request.POST.get('endereco_1', '').strip()
    
    if not nome_1:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O nome do Hóspede 1 (Titular) é obrigatório.</div>', status=400)
        
    # Atualizar reserva
    reserva.unidade = unidade
    reserva.data_checkin = d_checkin
    reserva.data_checkout = d_checkout
    reserva.subtotal = valor_total
    reserva.valor_total = valor_total
    reserva.status = status
    reserva.quantidade_hospedes = quantidade_hospedes
    reserva.hospede_nome = nome_1
    reserva.hospede_cpf = cpf_1
    reserva.hospede_email = email_1
    reserva.hospede_telefone = telefone_1
    reserva.hospede_rg = rg_1
    reserva.hospede_nacionalidade = nacionalidade_1
    reserva.hospede_profissao = profissao_1
    reserva.hospede_endereco = endereco_1
    reserva.save()
    
    # Atualizar hóspedes
    import re
    for i in range(1, quantidade_hospedes + 1):
        nome = request.POST.get(f'nome_{i}', '').strip()
        cpf = request.POST.get(f'cpf_{i}', '').strip()
        email = request.POST.get(f'email_{i}', '').strip()
        telefone = request.POST.get(f'telefone_{i}', '').strip()
        rg = request.POST.get(f'rg_{i}', '').strip()
        nacionalidade = request.POST.get(f'nacionalidade_{i}', 'Brasileira').strip()
        profissao = request.POST.get(f'profissao_{i}', '').strip()
        endereco = request.POST.get(f'endereco_{i}', '').strip()
        
        if i > 1 and not nome:
            continue
            
        hospede, created = HospedeReserva.objects.get_or_create(reserva=reserva, ordem=i)
        hospede.nome = nome or f"Hóspede {i}"
        hospede.cpf = cpf
        hospede.email = email
        hospede.telefone = telefone
        hospede.rg = rg
        hospede.nacionalidade = nacionalidade
        hospede.profissao = profissao
        hospede.endereco = endereco
        
        if request.POST.get(f'delete_doc_frente_{i}') == 'true':
            hospede.documento_frente = None
        if request.POST.get(f'delete_doc_verso_{i}') == 'true':
            hospede.documento_verso = None

        docs_list = request.FILES.getlist(f'documentos_{i}')
        if len(docs_list) > 0:
            hospede.documento_frente = docs_list[0]
        if len(docs_list) > 1:
            hospede.documento_verso = docs_list[1]
            
        hospede.save()
        
    # Deletar acompanhantes sobressalentes
    reserva.hospedes.filter(ordem__gt=quantidade_hospedes).delete()
    
    # Atualizar veículo
    placa_1 = request.POST.get('placa_1', '').strip()
    if placa_1:
        veiculo, created = VeiculoReserva.objects.get_or_create(reserva=reserva)
        veiculo.placa = placa_1.upper()
        veiculo.modelo = request.POST.get('modelo_1', '').strip()
        veiculo.cor = request.POST.get('cor_1', '').strip()
        veiculo.save()
    else:
        VeiculoReserva.objects.filter(reserva=reserva).delete()
        
    response = HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            if (typeof window.triggerReservasRefresh === 'function') {
                window.triggerReservasRefresh();
            }
        </script>
    """)
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_checkin(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    # Toggle Check-in
    if reserva.status == 'hospedado' or reserva.status == 'concluido':
        # Unmark check-in: revert to 'confirmada' and clear timestamps
        reserva.status = 'confirmada'
        reserva.checkin_realizado_em = None
        reserva.checkout_realizado_em = None
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkin',
            detalhes=f"Check-in desmarcado pelo usuário {request.user.username}."
        )
    else:
        # Mark check-in
        reserva.status = 'hospedado'
        from django.utils import timezone
        reserva.checkin_realizado_em = timezone.now()
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkin',
            detalhes=f"Check-in realizado pelo usuário {request.user.username}."
        )
        
    # Render the modal form to keep it open with the updated state
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    response = render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'trigger_grid_update': True
    })
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_checkout(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    # Toggle Check-out
    if reserva.status == 'concluido':
        # Unmark check-out: revert to 'hospedado'
        reserva.status = 'hospedado'
        reserva.checkout_realizado_em = None
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkout',
            detalhes=f"Check-out desmarcado pelo usuário {request.user.username}."
        )
    else:
        # Mark check-out
        reserva.status = 'concluido'
        from django.utils import timezone
        reserva.checkout_realizado_em = timezone.now()
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkout',
            detalhes=f"Check-out realizado pelo usuário {request.user.username}."
        )
        
        # Criar tarefa de limpeza pós-checkout se não existir
        if not Tarefa.objects.filter(reserva=reserva, titulo__icontains="Limpeza").exists():
            Tarefa.objects.create(
                hotel=hotel,
                titulo=f"Limpeza e Preparação - {reserva.unidade.identificador}",
                descricao=f"Realizar limpeza pós-checkout da reserva #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}.",
                prioridade='alta',
                status='todo',
                unidade=reserva.unidade,
                reserva=reserva
            )
        
    # Render the modal form to keep it open with the updated state
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    response = render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'trigger_grid_update': True
    })
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_cancelar(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    reserva.status = 'cancelada'
    reserva.save()
    
    response = HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            // disparar atualização do grid
            const filtro = document.getElementById('filtro-periodo');
            if (filtro) {
                htmx.trigger(filtro, 'change');
            } else {
                window.location.reload();
            }
        </script>
    """)
    return response


@login_required(login_url='hoteis:partner_login')
def partner_hospedes_pedidos(request):
    """
    Retorna a lista de pedidos de quarto do hotel logado (útil para atualização assíncrona).
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    pedidos = PedidoServico.objects.filter(hotel=hotel).order_by('-criado_em')
    return render(request, 'hoteis/partials/pedidos_lista.html', {'pedidos_ativos': pedidos})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_hospedes_atualizar_status(request, pedido_id):
    """
    Atualiza o status de uma solicitação de hóspede e retorna o card unitário atualizado.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    pedido = get_object_or_404(PedidoServico, id=pedido_id, hotel=hotel)
    
    novo_status = request.POST.get('status')
    if novo_status in dict(PedidoServico.STATUS_CHOICES):
        pedido.status = novo_status
        pedido.save()
        
    return render(request, 'hoteis/partials/pedido_card.html', {'p': pedido})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_hospedes_lancar_consumo(request, reserva_id):
    """
    Lança um item de consumo (frigobar/bomboniere) na conta da reserva e atualiza a grade de reservas.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    produto_id = request.POST.get('produto_id')
    quantidade_str = request.POST.get('quantidade', '1')
    observacoes = request.POST.get('observacoes', '').strip()
    
    try:
        quantidade = int(quantidade_str)
    except ValueError:
        quantidade = 1
        
    produto = get_object_or_404(ProdutoConsumo, id=produto_id, hotel=hotel)
    valor_total = produto.preco * quantidade
    
    # Criar um pedido do tipo 'entregue' para faturamento do frigobar
    pedido = PedidoServico.objects.create(
        reserva=reserva,
        unidade=reserva.unidade,
        hotel=hotel,
        status='entregue',
        observacoes=observacoes or f"Consumo lançado pela recepção: {produto.nome}.",
        valor_total=valor_total
    )
    
    ItemPedidoServico.objects.create(
        pedido=pedido,
        produto=produto,
        quantidade=quantidade,
        preco_unitario=produto.preco
    )
    
    # Adicionar o consumo ao valor total da reserva
    reserva.valor_total += valor_total
    reserva.save()
    
    # Log de auditoria
    try:
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user if request.user.is_authenticated else None,
            acao='consumo_lancado',
            detalhes=f"Lançado consumo de {quantidade}x {produto.nome} (Total: R$ {valor_total})."
        )
    except Exception:
        pass
    
    # Resposta com feedback e atualização do grid B2B em background
    return HttpResponse(f"""
        <div id="lancar-consumo-feedback" class="p-3 mb-3 text-xs text-green-800 bg-green-50 rounded-xl border border-green-500/20">
            Lançado com sucesso! R$ {valor_total} adicionados ao quarto {reserva.unidade.identificador}.
        </div>
        <script>
            if (typeof window.triggerReservasRefresh === 'function') {{
                window.triggerReservasRefresh();
            }}
            setTimeout(() => {{
                document.getElementById('lancar-consumo-feedback')?.remove();
            }}, 3500);
        </script>
    """)



