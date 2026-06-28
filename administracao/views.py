from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from parceiros.models import SolicitacaoEmpresa, Documento, StatusSolicitacao, TipoEmpresa
from hoteis.models import Hotel, Local, Produtor, ParceiroUsuario, Quarto, ConfigSistema, HotelTarifaFaixa, HotelDocumento, HotelTermoAdesao, HotelAuditLog
from core.models import Empresa

# Decorador customizado para garantir que apenas superusuários ativos acessem as views
def superuser_required(view_func):
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='administracao:login'
    )
    return actual_decorator(view_func)

def login_view(request):
    # Se já logado como superusuário, vai direto pro dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('administracao:dashboard')
        
    error_msg = None
    
    if request.method == 'POST':
        username = request.POST.get('navie_username') or request.POST.get('username')
        password = request.POST.get('navie_password') or request.POST.get('password')
        next_url = request.POST.get('next', 'administracao:dashboard')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                # Garante que redirecionamentos não caiam em loops
                if not next_url or next_url == 'None' or next_url == '':
                    next_url = 'administracao:dashboard'
                
                if ':' in next_url or next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('administracao:dashboard')
            else:
                error_msg = "Acesso restrito apenas para administradores do sistema."
        else:
            error_msg = "Usuário ou senha incorretos. Verifique suas credenciais."
            
    return render(request, 'administracao/login.html', {
        'error_msg': error_msg,
        'next': request.GET.get('next', '')
    })

@superuser_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sessão encerrada com sucesso.")
    return redirect('administracao:login')

@superuser_required
def dashboard_view(request):
    # Métricas Globais
    total_solicitacoes_pendentes = SolicitacaoEmpresa.objects.filter(status=StatusSolicitacao.PENDENTE).count()
    total_solicitacoes_geral = SolicitacaoEmpresa.objects.count()
    total_empresas_aprovadas = SolicitacaoEmpresa.objects.filter(status=StatusSolicitacao.APROVADO).count()
    
    # Hoteis Ativos no banco de hospedagem
    total_hoteis_ativos = Hotel.objects.count()
    
    # Total de Clientes / Usuários do sistema
    total_usuarios = User.objects.count()
    
    # Lista de todas as solicitações recentes
    solicitacoes = SolicitacaoEmpresa.objects.all().order_by('-data_solicitacao')
    
    context = {
        'total_solicitacoes_pendentes': total_solicitacoes_pendentes,
        'total_solicitacoes_geral': total_solicitacoes_geral,
        'total_empresas_aprovadas': total_empresas_aprovadas,
        'total_hoteis_ativos': total_hoteis_ativos,
        'total_usuarios': total_usuarios,
        'solicitacoes': solicitacoes,
        'active_tab': 'dashboard',
    }
    return render(request, 'administracao/dashboard.html', context)

@superuser_required
def solicitacao_detail_view(request, pk):
    solicitacao = get_object_or_404(SolicitacaoEmpresa, pk=pk)
    
    context = {
        'solicitacao': solicitacao,
        'status_choices': StatusSolicitacao.choices,
        'active_tab': 'solicitacoes',
    }
    return render(request, 'administracao/solicitacao_detail.html', context)

@superuser_required
def solicitacao_update_status_view(request, pk):
    if request.method == 'POST':
        solicitacao = get_object_or_404(SolicitacaoEmpresa, pk=pk)
        
        status = request.POST.get('status')
        notas_internas = request.POST.get('notas_internas', '')
        
        if status in [choice[0] for choice in StatusSolicitacao.choices]:
            solicitacao.status = status
            solicitacao.notas_internas = notas_internas
            solicitacao.atendido_por = request.user.get_full_name() or request.user.username
            solicitacao.save()
            messages.success(request, f"Solicitação de {solicitacao.nome_fantasia} atualizada com sucesso!")
        else:
            messages.error(request, "Status inválido fornecido.")
            
    return redirect('administracao:solicitacao_detail', pk=pk)

@superuser_required
def documentos_list_view(request):
    documentos = Documento.objects.all().order_by('titulo')
    context = {
        'documentos': documentos,
        'active_tab': 'documentos',
    }
    return render(request, 'administracao/documentos_list.html', context)

@superuser_required
def documento_edit_view(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        conteudo = request.POST.get('conteudo')
        
        if titulo and conteudo:
            documento.titulo = titulo
            documento.conteudo = conteudo
            documento.save()
            messages.success(request, f"Documento '{documento.titulo}' atualizado com sucesso!")
            return redirect('administracao:documentos_list')
        else:
            messages.error(request, "Título e Conteúdo são obrigatórios.")
            
    context = {
        'documento': documento,
        'active_tab': 'documentos',
    }
    return render(request, 'administracao/documento_edit.html', context)

# ─── MÓDULO DE GESTÃO DE HOTELARIA ────────────────────────────────────

@superuser_required
def hoteis_list_view(request):
    from django.db.models import Count, Avg
    from analytics.models import UserInteraction

    # Métricas da Hotelaria
    total_hoteis = Hotel.objects.count()
    hoteis_ativos = Hotel.objects.filter(status='ativo').count()
    hoteis_destaque = Hotel.objects.filter(destaque=True).count()
    total_quartos = Quarto.objects.count()
    
    # Lista de hotéis
    hoteis = Hotel.objects.all().select_related('local').order_by('nome')
    
    # Adiciona estatísticas de visualização para cada hotel
    for h in hoteis:
        main_page = UserInteraction.objects.filter(
            parent_id=str(h.id),
            category='hospedagem',
            interaction_type='page_view'
        ).aggregate(
            views_count=Count('id'),
            avg_time=Avg('time_spent')
        )
        main_views = main_page['views_count'] or 0
        main_avg_time = round(main_page['avg_time'] or 0, 1)

        room_views = (
            UserInteraction.objects.filter(
                parent_id=str(h.id),
                category='hospedagem',
                interaction_type='item_detail'
            )
            .values('item_id')
            .annotate(
                views_count=Count('id'),
                avg_time=Avg('time_spent')
            )
            .order_by('-views_count')
        )
        
        quartos_dict = {str(q.id): q.nome for q in h.quartos.all()}
        
        stats_list = []
        if main_views > 0:
            stats_list.append({
                'nome': 'Página Principal da Pousada',
                'tipo': 'Site Público',
                'visualizacoes': main_views,
                'tempo_medio': main_avg_time,
            })
            
        for stat in room_views:
            q_id = stat['item_id']
            if q_id:
                q_nome = quartos_dict.get(q_id, f"Acomodação #{q_id}")
                stats_list.append({
                    'nome': q_nome,
                    'tipo': 'Detalhe de Acomodação',
                    'visualizacoes': stat['views_count'],
                    'tempo_medio': round(stat['avg_time'] or 0, 1),
                })
                
        stats_list.sort(key=lambda x: x['visualizacoes'], reverse=True)
        h.ranking_stats = stats_list
    
    # Configuração Geral do Sistema
    config_sistema = ConfigSistema.objects.first()
    if not config_sistema:
        config_sistema = ConfigSistema.objects.create()
    
    context = {
        'total_hoteis': total_hoteis,
        'hoteis_ativos': hoteis_ativos,
        'hoteis_destaque': hoteis_destaque,
        'total_quartos': total_quartos,
        'hoteis': hoteis,
        'config_sistema': config_sistema,
        'active_tab': 'hoteis',
    }
    return render(request, 'administracao/hoteis_list.html', context)

@superuser_required
def hotel_create_view(request):
    # Garante a existência das localizações solicitadas pelo usuário
    Local.objects.get_or_create(nome="Serra da Serra", defaults={"endereco": "Serra da Ibiapaba, Rural", "cidade": "Tianguá", "estado": "CE"})
    Local.objects.get_or_create(nome="Alto Viçosa", defaults={"endereco": "Rua Matriz, 123", "cidade": "Viçosa do Ceará", "estado": "CE"})
    Local.objects.get_or_create(nome="Alto Visosa", defaults={"endereco": "Rua Matriz, 123", "cidade": "Viçosa do Ceará", "estado": "CE"})
    
    locais = Local.objects.all().order_by('nome')
    errors = []
    
    if request.method == 'POST':
        # 1. Dados do Hotel & Empresa
        nome_fantasia = request.POST.get('nome_fantasia')
        razao_social = request.POST.get('razao_social')
        cnpj = request.POST.get('cnpj')
        descricao = request.POST.get('descricao')
        whatsapp = request.POST.get('whatsapp')
        email_contato = request.POST.get('email_contato')
        slug = request.POST.get('slug')
        cor_primaria = request.POST.get('cor_primaria', '#f97316')
        destaque = request.POST.get('destaque') == 'on'
        venda_online = 'venda_online' in request.POST
        status = request.POST.get('status', 'ativo')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Rede/Empresa Portal Info
        slug_rede = request.POST.get('slug_rede')
        modalidade_portal = request.POST.get('modalidade_portal', 'individual')
        
        # 2. Dados de Localização
        cep = request.POST.get('cep')
        endereco = request.POST.get('endereco')
        cidade = request.POST.get('cidade')
        estado = request.POST.get('estado')
        local_id = request.POST.get('local_id')
        local_nome = request.POST.get('local_nome')
        
        # 3. Dados do Usuário Proprietário
        responsavel_nome = request.POST.get('responsavel_nome')
        username = request.POST.get('username')
        user_email = request.POST.get('user_email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        cpf = request.POST.get('cpf')
        
        # Validações de Unicidade
        if password != password_confirm:
            errors.append("A confirmação de senha não coincide com a senha informada.")
        if User.objects.filter(username=username).exists():
            errors.append("Este nome de usuário já está em uso.")
        if User.objects.filter(email=user_email).exists():
            errors.append("Este e-mail de usuário já está cadastrado.")
        if Empresa.objects.filter(cnpj=cnpj).exists():
            errors.append("Este CNPJ já está cadastrado em outra empresa.")
        if slug_rede and Empresa.objects.filter(slug=slug_rede).exists():
            errors.append("Este slug de subdomínio de rede já está em uso por outra empresa.")
        if Hotel.objects.filter(slug=slug).exists():
            errors.append("Este slug de URL já está em uso por outro hotel.")
            
        if not errors:
            try:
                # Resolve ou cria Local
                if local_id == 'new':
                    local = Local.objects.create(
                        nome=local_nome or nome_fantasia,
                        endereco=endereco,
                        cidade=cidade,
                        estado=estado
                    )
                else:
                    local = get_object_or_404(Local, pk=local_id)
                
                # Cria Empresa
                empresa = Empresa.objects.create(
                    nome_fantasia=nome_fantasia,
                    razao_social=razao_social,
                    cnpj=cnpj,
                    categoria='hospedagem',
                    endereco=endereco,
                    cidade=cidade,
                    estado=estado,
                    cep=cep,
                    email_contato=email_contato,
                    telefone_contato=whatsapp,
                    cor_primaria=cor_primaria,
                    logo=request.FILES.get('logo'),
                    banner=request.FILES.get('banner'),
                    slug=slug_rede or None,
                    modalidade_portal=modalidade_portal
                )
                
                # Cria Hotel
                config_sistema = ConfigSistema.objects.first()
                taxa_fixa = config_sistema.taxa_fixa_padrao if config_sistema else 15.00
                taxa_percentual = config_sistema.taxa_percentual_padrao if config_sistema else 10.00
                limite_trafego = config_sistema.limite_trafego_padrao if config_sistema else 100
                
                hotel = Hotel.objects.create(
                    empresa=empresa,
                    nome=nome_fantasia,
                    descricao=descricao,
                    banner=request.FILES.get('banner'),
                    local=local,
                    cor_primaria=cor_primaria,
                    whatsapp=whatsapp,
                    logo=request.FILES.get('logo'),
                    foto_fundo=request.FILES.get('foto_fundo'),
                    slug=slug,
                    status=status,
                    destaque=destaque,
                    venda_online=venda_online,
                    latitude=latitude or None,
                    longitude=longitude or None,
                    taxa_fixa_navie=taxa_fixa,
                    taxa_percentual_navie=taxa_percentual,
                    limite_trafego_gb=limite_trafego,
                    consumo_trafego_gb=0.00
                )
                
                # Cria Usuário
                user = User.objects.create_user(
                    username=username,
                    email=user_email,
                    password=password,
                    first_name=responsavel_nome
                )
                
                # Cria Vinculo de Parceiro
                ParceiroUsuario.objects.create(
                    user=user,
                    hotel=hotel,
                    role='proprietario',
                    cpf=cpf,
                    ativo=True
                )
                
                messages.success(request, f"Hotel '{nome_fantasia}' e seu usuário gestor foram criados com sucesso!")
                return redirect('administracao:hoteis_list')
                
            except Exception as e:
                errors.append(f"Erro ao salvar registros: {str(e)}")
                
    context = {
        'locais': locais,
        'errors': errors,
        'action': 'create',
        'active_tab': 'hoteis',
        'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
    }
    return render(request, 'administracao/hotel_form.html', context)

@superuser_required
def hotel_edit_view(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    empresa = hotel.empresa
    local = hotel.local
    
    # Localiza o usuário gestor proprietário da equipe
    parceiro_usuario = hotel.equipe.filter(role='proprietario').first()
    user = parceiro_usuario.user if parceiro_usuario else None
    
    # Garante a existência das localizações solicitadas pelo usuário
    Local.objects.get_or_create(nome="Serra da Serra", defaults={"endereco": "Serra da Ibiapaba, Rural", "cidade": "Tianguá", "estado": "CE"})
    Local.objects.get_or_create(nome="Alto Viçosa", defaults={"endereco": "Rua Matriz, 123", "cidade": "Viçosa do Ceará", "estado": "CE"})
    Local.objects.get_or_create(nome="Alto Visosa", defaults={"endereco": "Rua Matriz, 123", "cidade": "Viçosa do Ceará", "estado": "CE"})
    
    locais = Local.objects.all().order_by('nome')
    errors = []
    
    if request.method == 'POST':
        # 1. Dados do Hotel & Empresa
        nome_fantasia = request.POST.get('nome_fantasia')
        razao_social = request.POST.get('razao_social')
        cnpj = request.POST.get('cnpj')
        descricao = request.POST.get('descricao')
        whatsapp = request.POST.get('whatsapp')
        email_contato = request.POST.get('email_contato')
        slug = request.POST.get('slug')
        cor_primaria = request.POST.get('cor_primaria', '#f97316')
        destaque = request.POST.get('destaque') == 'on'
        venda_online = 'venda_online' in request.POST
        status = request.POST.get('status', 'ativo')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Rede/Empresa Portal Info
        slug_rede = request.POST.get('slug_rede')
        modalidade_portal = request.POST.get('modalidade_portal', 'individual')
        
        # 2. Dados de Localização
        cep = request.POST.get('cep')
        endereco = request.POST.get('endereco')
        cidade = request.POST.get('cidade')
        estado = request.POST.get('estado')
        local_id = request.POST.get('local_id')
        local_nome = request.POST.get('local_nome')
        
        # 3. Dados do Usuário Proprietário
        responsavel_nome = request.POST.get('responsavel_nome')
        username = request.POST.get('username')
        user_email = request.POST.get('user_email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        cpf = request.POST.get('cpf')
        
        # Validações de Unicidade (Ignorando os registros atuais)
        if password and password != password_confirm:
            errors.append("A confirmação de senha não coincide com a senha informada.")
        if User.objects.filter(username=username).exclude(pk=user.pk if user else None).exists():
            errors.append("Este nome de usuário já está em uso.")
        if User.objects.filter(email=user_email).exclude(pk=user.pk if user else None).exists():
            errors.append("Este e-mail de usuário já está cadastrado.")
        if empresa and Empresa.objects.filter(cnpj=cnpj).exclude(pk=empresa.pk).exists():
            errors.append("Este CNPJ já está cadastrado em outra empresa.")
        if slug_rede and Empresa.objects.filter(slug=slug_rede).exclude(pk=empresa.pk if empresa else None).exists():
            errors.append("Este slug de subdomínio de rede já está em uso por outra empresa.")
        if Hotel.objects.filter(slug=slug).exclude(pk=hotel.pk).exists():
            errors.append("Este slug de URL já está em uso por outro hotel.")
            
        if not errors:
            try:
                # 1. Resolve ou cria Local
                if local_id == 'new':
                    local = Local.objects.create(
                        nome=local_nome or nome_fantasia,
                        endereco=endereco,
                        cidade=cidade,
                        estado=estado
                    )
                else:
                    local = get_object_or_404(Local, pk=local_id)
                
                # 2. Atualiza ou cria Empresa
                if not empresa:
                    empresa = Empresa.objects.create(
                        nome_fantasia=nome_fantasia,
                        razao_social=razao_social,
                        cnpj=cnpj,
                        categoria='hospedagem',
                        endereco=endereco,
                        cidade=cidade,
                        estado=estado,
                        cep=cep,
                        email_contato=email_contato,
                        telefone_contato=whatsapp,
                        cor_primaria=cor_primaria,
                        slug=slug_rede or None,
                        modalidade_portal=modalidade_portal
                    )
                else:
                    empresa.nome_fantasia = nome_fantasia
                    empresa.razao_social = razao_social
                    empresa.cnpj = cnpj
                    empresa.endereco = endereco
                    empresa.cidade = cidade
                    empresa.estado = estado
                    empresa.cep = cep
                    empresa.email_contato = email_contato
                    empresa.telefone_contato = whatsapp
                    empresa.cor_primaria = cor_primaria
                    empresa.slug = slug_rede or None
                    empresa.modalidade_portal = modalidade_portal
                    if 'logo' in request.FILES:
                        empresa.logo = request.FILES['logo']
                    elif request.POST.get('clear_logo') == 'true':
                        empresa.logo = None
                    if 'banner' in request.FILES:
                        empresa.banner = request.FILES['banner']
                    elif request.POST.get('clear_banner') == 'true':
                        empresa.banner = None
                    empresa.save()
                
                # 3. Atualiza Hotel
                hotel.empresa = empresa
                hotel.nome = nome_fantasia
                hotel.descricao = descricao
                hotel.local = local
                hotel.cor_primaria = cor_primaria
                hotel.whatsapp = whatsapp
                hotel.slug = slug
                hotel.status = status
                hotel.destaque = destaque
                hotel.venda_online = venda_online
                hotel.latitude = latitude or None
                hotel.longitude = longitude or None
                
                if 'logo' in request.FILES:
                    hotel.logo = request.FILES['logo']
                elif request.POST.get('clear_logo') == 'true':
                    hotel.logo = None
                if 'banner' in request.FILES:
                    hotel.banner = request.FILES['banner']
                elif request.POST.get('clear_banner') == 'true':
                    hotel.banner = None
                if 'foto_fundo' in request.FILES:
                    hotel.foto_fundo = request.FILES['foto_fundo']
                elif request.POST.get('clear_foto_fundo') == 'true':
                    hotel.foto_fundo = None
                hotel.save()
                
                # 4. Atualiza ou cria Usuário
                if not user:
                    user = User.objects.create_user(
                        username=username,
                        email=user_email,
                        password=password or 'senha123',
                        first_name=responsavel_nome
                    )
                else:
                    user.username = username
                    user.email = user_email
                    user.first_name = responsavel_nome
                    if password:
                        user.set_password(password)
                    user.save()
                
                # 5. Atualiza ou cria ParceiroUsuario
                if not parceiro_usuario:
                    ParceiroUsuario.objects.create(
                        user=user,
                        hotel=hotel,
                        role='proprietario',
                        cpf=cpf,
                        ativo=True
                    )
                else:
                    parceiro_usuario.user = user
                    parceiro_usuario.cpf = cpf
                    parceiro_usuario.ativo = (status == 'ativo')
                    parceiro_usuario.save()
                    
                messages.success(request, f"Hotel '{nome_fantasia}' e credenciais do gestor foram atualizados com sucesso!")
                return redirect('administracao:hoteis_list')
                
            except Exception as e:
                errors.append(f"Erro ao salvar alterações: {str(e)}")
                
    context = {
        'hotel': hotel,
        'empresa': empresa,
        'local': local,
        'parceiro_usuario': parceiro_usuario,
        'user_obj': user,
        'locais': locais,
        'errors': errors,
        'action': 'edit',
        'active_tab': 'hoteis',
        'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
    }
    return render(request, 'administracao/hotel_form.html', context)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@superuser_required
def hotel_salvar_configuracao_admin(request, pk):
    if request.method == 'POST':
        hotel = get_object_or_404(Hotel, pk=pk)
        
        # Guardar valores originais para log de auditoria
        original_values = {
            'slug': hotel.slug,
            'taxa_fixa_navie': float(hotel.taxa_fixa_navie),
            'taxa_percentual_navie': float(hotel.taxa_percentual_navie),
            'limite_trafego_gb': int(hotel.limite_trafego_gb),
            'consumo_trafego_gb': float(hotel.consumo_trafego_gb),
            'venda_online': hotel.venda_online,
            'usar_tarifas_faixa': hotel.usar_tarifas_faixa,
            'status': hotel.status,
        }
        
        slug = request.POST.get('slug')
        taxa_fixa = request.POST.get('taxa_fixa_navie')
        taxa_percentual = request.POST.get('taxa_percentual_navie')
        limite_trafego = request.POST.get('limite_trafego_gb')
        consumo_trafego = request.POST.get('consumo_trafego_gb')
        venda_online = 'venda_online' in request.POST
        usar_tarifas_faixa = 'usar_tarifas_faixa' in request.POST
        status = request.POST.get('status', 'ativo')
        
        errors = []
        if not slug:
            errors.append("O slug do subdomínio é obrigatório.")
        elif Hotel.objects.filter(slug=slug).exclude(pk=hotel.pk).exists():
            errors.append("Este slug de subdomínio já está em uso por outro hotel.")
            
        if not errors:
            try:
                # Sanitize commas from localization format to allow float conversion
                taxa_fixa_clean = taxa_fixa.replace(',', '.') if taxa_fixa else '0.0'
                taxa_percentual_clean = taxa_percentual.replace(',', '.') if taxa_percentual else '0.0'
                consumo_trafego_clean = consumo_trafego.replace(',', '.') if consumo_trafego else '0.0'
                
                hotel.slug = slug
                hotel.taxa_fixa_navie = float(taxa_fixa_clean)
                hotel.taxa_percentual_navie = float(taxa_percentual_clean)
                hotel.limite_trafego_gb = int(limite_trafego) if limite_trafego else 100
                hotel.consumo_trafego_gb = float(consumo_trafego_clean)
                hotel.venda_online = venda_online
                hotel.usar_tarifas_faixa = usar_tarifas_faixa
                hotel.status = status
                hotel.save()
                
                # Gerar Logs de Auditoria
                new_values = {
                    'slug': hotel.slug,
                    'taxa_fixa_navie': float(hotel.taxa_fixa_navie),
                    'taxa_percentual_navie': float(hotel.taxa_percentual_navie),
                    'limite_trafego_gb': int(hotel.limite_trafego_gb),
                    'consumo_trafego_gb': float(hotel.consumo_trafego_gb),
                    'venda_online': hotel.venda_online,
                    'usar_tarifas_faixa': hotel.usar_tarifas_faixa,
                    'status': hotel.status,
                }
                
                ip = get_client_ip(request)
                ua = request.META.get('HTTP_USER_AGENT', '')[:255]
                
                for field, old_val in original_values.items():
                    new_val = new_values[field]
                    if old_val != new_val:
                        HotelAuditLog.objects.create(
                            hotel=hotel,
                            usuario=request.user,
                            ip_origem=ip,
                            dispositivo=ua,
                            campo_alterado=field,
                            valor_antigo=str(old_val),
                            valor_novo=str(new_val)
                        )
                        
                messages.success(request, f"Configurações administrativas de '{hotel.nome}' atualizadas com sucesso!")
            except Exception as e:
                messages.error(request, f"Erro ao salvar configurações: {str(e)}")
        else:
            for error in errors:
                messages.error(request, error)
                
    return redirect('administracao:hoteis_list')


@superuser_required
def hotel_documento_adicionar(request, pk):
    if request.method == 'POST':
        hotel = get_object_or_404(Hotel, pk=pk)
        nome = request.POST.get('nome')
        arquivo = request.FILES.get('arquivo')
        if nome and arquivo:
            try:
                doc = HotelDocumento.objects.create(hotel=hotel, nome=nome, arquivo=arquivo)
                # Audit Log
                HotelAuditLog.objects.create(
                    hotel=hotel,
                    usuario=request.user,
                    ip_origem=get_client_ip(request),
                    dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
                    campo_alterado='documento',
                    valor_antigo=None,
                    valor_novo=f"Adicionado documento: {nome} ({arquivo.name})"
                )
                messages.success(request, f"Documento '{nome}' adicionado com sucesso!")
            except Exception as e:
                messages.error(request, f"Erro ao adicionar documento: {str(e)}")
        else:
            messages.error(request, "Nome e arquivo do documento são obrigatórios.")
    return redirect('administracao:hoteis_list')


@superuser_required
def hotel_documento_excluir(request, doc_pk):
    doc = get_object_or_404(HotelDocumento, pk=doc_pk)
    hotel = doc.hotel
    nome = doc.nome
    try:
        doc.arquivo.delete(save=False)
        doc.delete()
        # Audit Log
        HotelAuditLog.objects.create(
            hotel=hotel,
            usuario=request.user,
            ip_origem=get_client_ip(request),
            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
            campo_alterado='documento',
            valor_antigo=f"Documento existente: {nome}",
            valor_novo="Removido"
        )
        messages.success(request, f"Documento '{nome}' removido com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao remover documento: {str(e)}")
    return redirect('administracao:hoteis_list')


@superuser_required
def hotel_termo_registrar(request, pk):
    if request.method == 'POST':
        hotel = get_object_or_404(Hotel, pk=pk)
        versao = request.POST.get('versao_termo', '1.0')
        try:
            HotelTermoAdesao.objects.create(
                hotel=hotel,
                versao_termo=versao,
                ip_origem=get_client_ip(request),
                dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
                usuario=request.user
            )
            # Audit Log
            HotelAuditLog.objects.create(
                hotel=hotel,
                usuario=request.user,
                ip_origem=get_client_ip(request),
                dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
                campo_alterado='termo_adesao',
                valor_antigo=None,
                valor_novo=f"Registrado aceite de termo versão {versao}"
            )
            messages.success(request, f"Aceite de Termo de Uso v{versao} registrado com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao registrar aceite de termo: {str(e)}")
    return redirect('administracao:hoteis_list')


@superuser_required
def hotel_tarifas_faixa_salvar(request, pk):
    if request.method == 'POST':
        hotel = get_object_or_404(Hotel, pk=pk)
        min_val = request.POST.get('valor_minimo')
        max_val = request.POST.get('valor_maximo')
        taxa_fixa = request.POST.get('taxa_fixa')
        taxa_pct = request.POST.get('taxa_percentual')
        
        if min_val and max_val:
            try:
                faixa = HotelTarifaFaixa.objects.create(
                    hotel=hotel,
                    valor_minimo=float(min_val),
                    valor_maximo=float(max_val),
                    taxa_fixa=float(taxa_fixa) if taxa_fixa else 0.0,
                    taxa_percentual=float(taxa_pct) if taxa_pct else 0.0
                )
                # Audit Log
                HotelAuditLog.objects.create(
                    hotel=hotel,
                    usuario=request.user,
                    ip_origem=get_client_ip(request),
                    dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
                    campo_alterado='tarifa_faixa',
                    valor_antigo=None,
                    valor_novo=f"Adicionada faixa: R$ {min_val} a R$ {max_val} -> R$ {taxa_fixa} + {taxa_pct}%"
                )
                messages.success(request, "Nova faixa de tarifa adicionada com sucesso!")
            except Exception as e:
                messages.error(request, f"Erro ao adicionar faixa de tarifa: {str(e)}")
        else:
            messages.error(request, "Valores mínimo e máximo são obrigatórios.")
    return redirect('administracao:hoteis_list')


@superuser_required
def hotel_tarifa_faixa_excluir(request, faixa_pk):
    faixa = get_object_or_404(HotelTarifaFaixa, pk=faixa_pk)
    hotel = faixa.hotel
    desc = f"Faixa: R$ {faixa.valor_minimo} a R$ {faixa.valor_maximo} -> R$ {faixa.taxa_fixa} + {faixa.taxa_percentual}%"
    try:
        faixa.delete()
        # Audit Log
        HotelAuditLog.objects.create(
            hotel=hotel,
            usuario=request.user,
            ip_origem=get_client_ip(request),
            dispositivo=request.META.get('HTTP_USER_AGENT', '')[:255],
            campo_alterado='tarifa_faixa',
            valor_antigo=desc,
            valor_novo="Removida"
        )
        messages.success(request, "Faixa de tarifa removida com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao remover faixa de tarifa: {str(e)}")
    return redirect('administracao:hoteis_list')


@superuser_required
def salvar_configuracao_sistema(request):
    if request.method == 'POST':
        taxa_fixa = request.POST.get('taxa_fixa_padrao')
        taxa_pct = request.POST.get('taxa_percentual_padrao')
        limite_trafego = request.POST.get('limite_trafego_padrao')
        
        try:
            config = ConfigSistema.objects.first()
            if not config:
                config = ConfigSistema.objects.create()
                
            config.taxa_fixa_padrao = float(taxa_fixa) if taxa_fixa else 15.00
            config.taxa_percentual_padrao = float(taxa_pct) if taxa_pct else 10.00
            config.limite_trafego_padrao = int(limite_trafego) if limite_trafego else 100
            config.save()
            messages.success(request, "Configurações gerais do sistema salvas com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao salvar configurações gerais: {str(e)}")
    return redirect('administracao:hoteis_list')


