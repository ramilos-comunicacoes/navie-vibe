from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache
from .models import RestauranteUsuario, Restaurante, RestauranteAtracao

def partner_auth(request):
    """
    Controla o login e a solicitação de parceria para donos e equipes de restaurantes.
    Usa HTMX para transições fluidas de tela inteira sem recarregamento.
    """
    from django.http import HttpResponse
    from django.urls import reverse
    
    is_htmx = request.headers.get('HX-Request') == 'true' or 'form' in request.GET
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_restaurante'):
            if is_htmx:
                response = HttpResponse()
                response['HX-Redirect'] = reverse('restaurantes:partner_dashboard')
                return response
            return redirect('restaurantes:partner_dashboard')
        # Usuários logados como cliente comum não são redirecionados

    # Se for requisição HTMX do tipo GET para trocar de formulário
    if request.method == 'GET' and is_htmx:
        form_type = request.GET.get('form', 'login')
        if form_type == 'register':
            return render(request, 'restaurantes/auth/partner_register_form.html')
        return render(request, 'restaurantes/auth/partner_login_form.html')

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
                if user.is_superuser:
                    auth_login(request, user)
                    messages.success(request, f"Bem-vindo, Administrador {user.first_name or user.username}!")
                    if is_htmx:
                        response = HttpResponse()
                        response['HX-Redirect'] = reverse('restaurantes:partner_dashboard')
                        return response
                    return redirect('restaurantes:partner_dashboard')
                elif hasattr(user, 'perfil_restaurante'):
                    perfil = user.perfil_restaurante
                    if perfil.ativo:
                        auth_login(request, user)
                        messages.success(request, f"Bem-vindo de volta, {user.first_name or user.username}!")
                        if is_htmx:
                            response = HttpResponse()
                            response['HX-Redirect'] = reverse('restaurantes:partner_dashboard')
                            return response
                        return redirect('restaurantes:partner_dashboard')
                    else:
                        msg = "Sua conta de parceiro de restaurante está aguardando aprovação."
                else:
                    msg = "Este portal é exclusivo para parceiros de restaurantes."
            else:
                msg = "Credenciais inválidas. Verifique seu login e senha."
                
            if is_htmx:
                context = {'error_message': msg, 'username_entered': username_or_email}
                return render(request, 'restaurantes/auth/partner_login_form.html', context)
            else:
                messages.error(request, msg)
                
        elif action == 'register':
            nome_restaurante = request.POST.get('nome_restaurante', '').strip()
            tipo_restaurante = request.POST.get('tipo_restaurante', '').strip()
            cnpj = request.POST.get('cnpj', '').strip()
            responsavel = request.POST.get('responsavel_nome', '').strip()
            email = request.POST.get('responsavel_email', '').strip()
            telefone = request.POST.get('responsavel_telefone', '').strip()
            
            if nome_restaurante and responsavel and email and telefone:
                if is_htmx:
                    context = {
                        'nome_restaurante': nome_restaurante,
                        'responsavel': responsavel,
                        'email': email,
                    }
                    return render(request, 'restaurantes/auth/partner_register_success.html', context)
                else:
                    messages.success(request, "Solicitação de parceria enviada com sucesso! Nossa equipe analisará os dados do restaurante.")
            else:
                msg = "Preencha todos os campos obrigatórios para enviar a solicitação."
                if is_htmx:
                    context = {'error_message': msg}
                    return render(request, 'restaurantes/auth/partner_register_form.html', context)
                else:
                    messages.error(request, msg)

    return render(request, 'restaurantes/auth/partner_login.html')

@login_required(login_url='restaurantes:partner_login')
@never_cache
def partner_dashboard(request):
    """
    O painel B2B adaptativo do parceiro de restaurante.
    Suporta visão consolidada de Superusuário.
    """
    is_superuser = request.user.is_superuser
    
    # Se for POST e for superusuário, processamos ações administrativas
    if request.method == 'POST' and is_superuser:
        action = request.POST.get('superuser_action')
        if action == 'reset_password':
            user_id = request.POST.get('user_id')
            new_password = request.POST.get('new_password', '').strip()
            if user_id and new_password:
                user = User.objects.using('default').filter(id=user_id).first()
                if user:
                    user.set_password(new_password)
                    user.save(using='default')
                    messages.success(request, f"Senha do usuário {user.username} redefinida com sucesso.")
                else:
                    messages.error(request, "Usuário não encontrado.")
            else:
                messages.error(request, "Campos inválidos.")
            return redirect(request.path + '?tab=superuser')
            
        elif action == 'toggle_status':
            perfil_id = request.POST.get('perfil_id')
            if perfil_id:
                perfil_u = RestauranteUsuario.objects.using('restaurantes').filter(id=perfil_id).first()
                if perfil_u:
                    perfil_u.ativo = not perfil_u.ativo
                    perfil_u.save(using='restaurantes')
                    status_str = "ativado" if perfil_u.ativo else "desativado"
                    messages.success(request, f"Perfil do usuário {perfil_u.user.username} foi {status_str}.")
                else:
                    messages.error(request, "Perfil de parceiro não encontrado.")
            return redirect(request.path + '?tab=superuser')
            
        elif action == 'change_role':
            perfil_id = request.POST.get('perfil_id')
            new_role = request.POST.get('role')
            if perfil_id and new_role:
                perfil_u = RestauranteUsuario.objects.using('restaurantes').filter(id=perfil_id).first()
                if perfil_u:
                    perfil_u.role = new_role
                    perfil_u.save(using='restaurantes')
                    messages.success(request, f"Cargo do usuário {perfil_u.user.username} alterado para {perfil_u.get_role_display()}.")
                else:
                    messages.error(request, "Perfil de parceiro não encontrado.")
            return redirect(request.path + '?tab=superuser')

    restaurante = None
    restaurantes_todos = None
    equipes_todas = None
    perfil = None

    if is_superuser:
        selected_id = request.GET.get('gerenciar_restaurante_id')
        if selected_id:
            if selected_id == 'clear':
                if 'superuser_restaurante_id' in request.session:
                    del request.session['superuser_restaurante_id']
            else:
                request.session['superuser_restaurante_id'] = int(selected_id)
        
        superuser_restaurante_id = request.session.get('superuser_restaurante_id')
        restaurantes_todos = Restaurante.objects.using('restaurantes').all()
        equipes_todas = RestauranteUsuario.objects.using('restaurantes').all()
        
        for eq in equipes_todas:
            eq.user = User.objects.using('default').filter(id=eq.user_id).first()

        if superuser_restaurante_id:
            restaurante = Restaurante.objects.using('restaurantes').filter(id=superuser_restaurante_id).first()
            if not restaurante:
                restaurante = restaurantes_todos.first()
        else:
            restaurante = None
            
        class SuperuserPerfil:
            role = 'proprietario'
            ativo = True
            user = request.user
        perfil = SuperuserPerfil()
    else:
        if not hasattr(request.user, 'perfil_restaurante'):
            messages.error(request, "Acesso negado. Esta conta não possui perfil de restaurante.")
            return redirect('restaurantes:partner_login')
            
        perfil = request.user.perfil_restaurante
        if not perfil.ativo:
            messages.error(request, "Sua conta de parceiro está inativa ou aguardando aprovação.")
            return redirect('restaurantes:partner_login')
            
        restaurante = perfil.restaurante

    if restaurante:
        atracoes = RestauranteAtracao.objects.using('restaurantes').filter(restaurante=restaurante)
    else:
        atracoes = RestauranteAtracao.objects.using('restaurantes').none()

    context = {
        'perfil': perfil,
        'restaurante': restaurante,
        'atracoes': atracoes,
        'is_superuser': is_superuser,
        'restaurantes_todos': restaurantes_todos,
        'equipes_todas': equipes_todas,
    }
    return render(request, 'restaurantes/partner_dashboard.html', context)

def partner_logout(request):
    """
    Encerra a sessão do parceiro de restaurante.
    """
    auth_logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('restaurantes:partner_login')


@login_required(login_url='restaurantes:partner_login')
@require_POST
def partner_salvar_configuracoes(request):
    """
    Grava as configurações de personalização visual, contatos e geolocalização do restaurante.
    """
    if not hasattr(request.user, 'perfil_restaurante'):
        messages.error(request, "Acesso negado.")
        return redirect('restaurantes:partner_login')
        
    perfil = request.user.perfil_restaurante
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente para alterar as configurações.")
        return redirect('restaurantes:partner_dashboard')
        
    restaurante = perfil.restaurante
    
    # Atualização dos campos de texto e branding
    restaurante.nome = request.POST.get('nome', restaurante.nome).strip()
    restaurante.descricao = request.POST.get('descricao', restaurante.descricao).strip()
    restaurante.especialidade = request.POST.get('especialidade', restaurante.especialidade).strip()
    restaurante.cidade_nome = request.POST.get('cidade_nome', restaurante.cidade_nome).strip()
    restaurante.endereco = request.POST.get('endereco', restaurante.endereco).strip()
    
    # WhatsApp público
    raw_whatsapp = request.POST.get('whatsapp', '')
    cleaned_whatsapp = ''.join(c for c in raw_whatsapp if c.isdigit())
    if cleaned_whatsapp:
        if len(cleaned_whatsapp) in [10, 11] and not cleaned_whatsapp.startswith('55'):
            cleaned_whatsapp = '55' + cleaned_whatsapp
        restaurante.whatsapp = cleaned_whatsapp
    else:
        restaurante.whatsapp = None
        
    # WhatsApp privado (Naviê)
    raw_whatsapp_privado = request.POST.get('whatsapp_privado', '')
    cleaned_whatsapp_privado = ''.join(c for c in raw_whatsapp_privado if c.isdigit())
    if cleaned_whatsapp_privado:
        if len(cleaned_whatsapp_privado) in [10, 11] and not cleaned_whatsapp_privado.startswith('55'):
            cleaned_whatsapp_privado = '55' + cleaned_whatsapp_privado
        restaurante.whatsapp_privado = cleaned_whatsapp_privado
    else:
        restaurante.whatsapp_privado = None

    restaurante.email_contato = request.POST.get('email_contato', '').strip() or None
    
    restaurante.cor_primaria = request.POST.get('cor_primaria', restaurante.cor_primaria)
    restaurante.cor_secundaria = request.POST.get('cor_secundaria', restaurante.cor_secundaria)
    restaurante.hero_tipo = request.POST.get('hero_tipo', restaurante.hero_tipo)
    
    # Geolocalização
    lat = request.POST.get('latitude', '').strip().replace(',', '.')
    lon = request.POST.get('longitude', '').strip().replace(',', '.')
    if lat and lat.lower() != 'none' and lat.lower() != 'nan':
        try:
            restaurante.latitude = float(lat)
        except ValueError:
            pass
    if lon and lon.lower() != 'none' and lon.lower() != 'nan':
        try:
            restaurante.longitude = float(lon)
        except ValueError:
            pass

    # Seção Sobre
    restaurante.sobre_titulo = request.POST.get('sobre_titulo', '').strip() or None
    restaurante.sobre_texto = request.POST.get('sobre_texto', '').strip() or None
    restaurante.sobre_cor_fundo = request.POST.get('sobre_cor_fundo', '#f8fafc')
    restaurante.sobre_cor_texto = request.POST.get('sobre_cor_texto', '#0f172a')
    restaurante.sobre_midia_tipo = request.POST.get('sobre_midia_tipo', 'imagem')
            
    # Upload de arquivos e remoções
    if request.POST.get('remover_banner') == 'true':
        restaurante.banner = None
    elif 'banner' in request.FILES:
        restaurante.banner = request.FILES['banner']
        
    if request.POST.get('remover_logo') == 'true':
        restaurante.logo = None
    elif 'logo' in request.FILES:
        restaurante.logo = request.FILES['logo']
        
    if request.POST.get('remover_sobre_banner') == 'true':
        restaurante.sobre_banner = None
    elif 'sobre_banner' in request.FILES:
        restaurante.sobre_banner = request.FILES['sobre_banner']
        
    if request.POST.get('remover_sobre_video') == 'true':
        restaurante.sobre_video = None
    elif 'sobre_video' in request.FILES:
        video_file = request.FILES['sobre_video']
        if video_file.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo da seção sobre ultrapassa o limite de 8MB permitido.")
            from django.urls import reverse
            url_red = reverse('restaurantes:partner_dashboard') + '?tab=configuracoes'
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse()
                response['HX-Redirect'] = url_red
                return response
            return redirect(url_red)
        restaurante.sobre_video = video_file

    if request.POST.get('remover_hero_video') == 'true':
        restaurante.hero_video = None
    elif 'hero_video' in request.FILES:
        video_file = request.FILES['hero_video']
        if video_file.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo em loop do hero ultrapassa o limite de 8MB permitido.")
            from django.urls import reverse
            url_red = reverse('restaurantes:partner_dashboard') + '?tab=configuracoes'
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse()
                response['HX-Redirect'] = url_red
                return response
            return redirect(url_red)
        restaurante.hero_video = video_file
        
    restaurante.save(using='restaurantes')
    messages.success(request, "Configurações do restaurante salvas com sucesso.")
    from django.urls import reverse
    url_red = reverse('restaurantes:partner_dashboard') + '?tab=configuracoes'
    if request.headers.get('HX-Request'):
        from django.http import HttpResponse
        response = HttpResponse()
        response['HX-Redirect'] = url_red
        return response
    return redirect(url_red)


@login_required(login_url='restaurantes:partner_login')
@require_POST
def partner_salvar_atracao(request):
    """
    Cria ou atualiza uma atração do restaurante (B2B).
    """
    if not hasattr(request.user, 'perfil_restaurante'):
        messages.error(request, "Acesso negado.")
        return redirect('restaurantes:partner_login')
        
    perfil = request.user.perfil_restaurante
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente.")
        return redirect('restaurantes:partner_dashboard')
        
    restaurante = perfil.restaurante
    atracao_id = request.POST.get('atracao_id')
    
    if atracao_id:
        # Edição
        from django.shortcuts import get_object_or_404
        atracao = get_object_or_404(RestauranteAtracao.objects.using('restaurantes'), id=atracao_id, restaurante=restaurante)
    else:
        # Criação
        atracao = RestauranteAtracao(restaurante=restaurante)
        
    atracao.dia = request.POST.get('dia', '').strip()
    atracao.titulo = request.POST.get('titulo', '').strip()
    atracao.texto = request.POST.get('texto', '').strip()
    atracao.cor_fundo = request.POST.get('cor_fundo', '#0f172a').strip()
    atracao.cor_texto = request.POST.get('cor_texto', '#ffffff').strip()
    atracao.midia_tipo = request.POST.get('midia_tipo', 'imagem')
    atracao.ativo = request.POST.get('ativo') == 'true' or request.POST.get('ativo') == 'on'
    
    data_str = request.POST.get('data', '').strip()
    horario_str = request.POST.get('horario', '').strip()
    
    if data_str:
        from datetime import datetime
        try:
            atracao.data = datetime.strptime(data_str, '%d/%m/%Y').date()
            atracao.dia = data_str
        except ValueError:
            pass
    else:
        atracao.data = None
        
    if horario_str:
        from datetime import datetime
        try:
            atracao.horario = datetime.strptime(horario_str, '%H:%M').time()
        except ValueError:
            pass
    else:
        atracao.horario = None
    
    # Imagem
    if request.POST.get('remover_imagem') == 'true':
        atracao.imagem = None
    elif 'imagem' in request.FILES:
        atracao.imagem = request.FILES['imagem']
        
    # Vídeo
    if request.POST.get('remover_video') == 'true':
        atracao.video = None
    elif 'video' in request.FILES:
        video_file = request.FILES['video']
        if video_file.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo ultrapassa o limite de 8MB permitido.")
            from django.urls import reverse
            return redirect(reverse('restaurantes:partner_dashboard') + '?tab=configuracoes&sub=destaques')
        atracao.video = video_file
        
    atracao.save(using='restaurantes')
    messages.success(request, "Atração salva com sucesso.")
    from django.urls import reverse
    return redirect(reverse('restaurantes:partner_dashboard') + '?tab=configuracoes&sub=destaques')


@login_required(login_url='restaurantes:partner_login')
def partner_deletar_atracao(request, atracao_id):
    """
    Exclui uma atração do restaurante (B2B).
    """
    if not hasattr(request.user, 'perfil_restaurante'):
        messages.error(request, "Acesso negado.")
        return redirect('restaurantes:partner_login')
        
    perfil = request.user.perfil_restaurante
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente.")
        return redirect('restaurantes:partner_dashboard')
        
    from django.shortcuts import get_object_or_404
    atracao = get_object_or_404(RestauranteAtracao.objects.using('restaurantes'), id=atracao_id, restaurante=perfil.restaurante)
    
    # Deleta mídias físicas se houver
    if atracao.imagem:
        atracao.imagem.delete(save=False)
    if atracao.video:
        atracao.video.delete(save=False)
        
    atracao.delete(using='restaurantes')
    messages.success(request, "Atração excluída com sucesso.")
    from django.urls import reverse
    return redirect(reverse('restaurantes:partner_dashboard') + '?tab=configuracoes&sub=destaques')


def restaurante_detalhe(request, slug):
    """
    Página pública (B2C) do restaurante — exibe o hero, atração do dia,
    destaques do cardápio, mapa de localização e seção sobre.
    """
    from django.shortcuts import get_object_or_404
    restaurante = get_object_or_404(Restaurante.objects.using('restaurantes'), slug=slug, ativo=True)

    # Força o redirecionamento para o subdomínio correspondente caso acessado via domínio principal navievibe.com
    host_clean = request.get_host().split(':')[0].lower()
    if request.subdomains_supported and 'navievibe.com' in host_clean:
        subdomain_now = host_clean.split('.')[0]
        if subdomain_now != restaurante.slug_normalized:
            parts = host_clean.split('.')
            if len(parts) > 1:
                base_domain = host_clean
                reservados = ['www', 'admin', 'accounts', 'api', 'clientes', 'hospedagens', 'hotelaria', 'static', 'media', 'dashboard', 'navievibe']
                if subdomain_now in reservados or len(parts) > 2:
                    base_domain = '.'.join(parts[1:])
                port = ":" + request.get_host().split(":")[1] if ":" in request.get_host() else ""
                target_url = f"{request.scheme}://{restaurante.slug_normalized}.{base_domain}{port}/"
                return redirect(target_url)
        elif request.path != '/':
            # Se o subdomínio já está correto, mas acessaram a URL completa (/restaurantes/slug/),
            # redireciona para a raiz do subdomínio
            return redirect(f"{request.scheme}://{request.get_host()}/")
    elif request.subdomains_supported and request.path != '/':
        # Se for um domínio próprio (ex: manacadaserra.com ou www.manacadaserra.com)
        # e o path não for a raiz, redireciona para a raiz do domínio próprio
        return redirect(f"{request.scheme}://{request.get_host()}/")

    # Busca as atrações ativas do restaurante (hoje em diante ou sem data)
    from django.utils import timezone
    from django.db.models import Q
    today = timezone.localdate()
    atracoes = RestauranteAtracao.objects.using('restaurantes').filter(
        Q(restaurante=restaurante, ativo=True) & (Q(data__gte=today) | Q(data__isnull=True))
    ).order_by('data', 'horario', '-criado_em')
    
    # Fallback se não houver nenhuma cadastrada
    if not atracoes.exists():
        class MockAtracao:
            titulo = "Em Breve: Novas Atrações"
            texto = "Fique atento às nossas programações especiais com shows ao vivo, noites temáticas e eventos gastronômicos exclusivos."
            banner = None
            video = None
            midia_tipo = 'imagem'
            cor_fundo = '#0f172a'
            cor_texto = '#ffffff'
            dia = "Programação Especial"
        atracoes = [MockAtracao()]

    # Pratos Mock (para preencher a seção de destaques enquanto não há gestão de cardápio)
    class MockPrato:
        def __init__(self, nome, categoria, descricao, imagem_url):
            self.nome = nome
            self.categoria = categoria
            self.descricao = descricao
            self.imagem_url = imagem_url

    pratos_mock = [
        MockPrato("Filé ao Molho Especial", "Prato Principal", "Filé mignon grelhado com molho de ervas frescas e acompanhamentos da estação.", None),
        MockPrato("Risoto de Cogumelos", "Entrada Premium", "Risoto cremoso preparado com mix de cogumelos frescos e parmesão artesanal.", None),
        MockPrato("Frango Assado da Serra", "Regional", "Frango caipira assado lentamente com temperos regionais e farofa de mandioca.", None),
        MockPrato("Carne de Sol com Nata", "Clássico Nordestino", "Tradicional carne de sol grelhada servida com nata da terra e pirão.", None),
        MockPrato("Sobremesa da Casa", "Doces & Sobremesas", "Mousse especial de chocolate com calda de frutas vermelhas da propriedade.", None),
    ]

    slug_clean = restaurante.slug.replace('-', '').replace('_', '')
    class SpecialMenuCard:
        def __init__(self, sc):
            self.nome = "Cardápio & Pedidos"
            self.categoria = "Pedidos Rápidos"
            self.descricao = "Utilizando o link do MenuDino, o seu atendimento se torna muito mais ágil!"
            self.imagem_url = None
            self.is_special = True
            self.link_url = f"https://{sc}.menudino.com"
    
    pratos_mock.insert(0, SpecialMenuCard(slug_clean))

    galeria_data = {
        'manaca-da-serra': [
            {"titulo": "Filé Mignon com Fritas", "url": "/media/restaurantes/galeria/manaca/file_mignon.jpg"},
            {"titulo": "Camarão ao Fettuccine", "url": "/media/restaurantes/galeria/manaca/camarao_fettuccine.jpg"},
            {"titulo": "Risoto Carne de Sol", "url": "/media/restaurantes/galeria/manaca/risoto_carne_sol.jpg"},
            {"titulo": "Maminha Laminada", "url": "/media/restaurantes/galeria/manaca/maminha_laminada.jpg"},
            {"titulo": "Croquete Vaca Atolada", "url": "/media/restaurantes/galeria/manaca/croquete_vaca_atolada.jpg"},
            {"titulo": "Croquete de Linguiça Toscana", "url": "/media/restaurantes/galeria/manaca/croquete_toscana.jpg"},
            {"titulo": "Salada Agridoce", "url": "/media/restaurantes/galeria/manaca/salada_agridoce.jpg"},
            {"titulo": "Banana Flambada", "url": "/media/restaurantes/galeria/manaca/banana_flambada.jpg"},
            {"titulo": "Compota Caseira", "url": "/media/restaurantes/galeria/manaca/compota.jpg"},
            {"titulo": "Soda de Verão", "url": "/media/restaurantes/galeria/manaca/soda_verao.jpg"},
        ],
        'casa-de-engenho': [
            {"titulo": "Arquitetura Rústica", "url": "https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Cozinha Regional", "url": "https://images.unsplash.com/photo-1543353071-10c8ba85a904?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Ambiente Temático", "url": "https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Prato Tradicional", "url": "https://images.unsplash.com/photo-1590947132387-155cc02f3212?auto=format&fit=crop&w=600&h=800&q=80"},
        ],
        'premibeer': [
            {"titulo": "Torneiras de Chopp", "url": "https://images.unsplash.com/photo-1571613316887-6f8d5cbf7ef7?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Hambúrguer Gourmet", "url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Cerveja Artesanal", "url": "https://images.unsplash.com/photo-1608270586620-248524c67de9?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Espaço Pub", "url": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=600&h=800&q=80"},
        ],
        'biene-cacau': [
            {"titulo": "Trufas Artesanais", "url": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Cafeteria Charmosa", "url": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Confeitaria Fina", "url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&h=800&q=80"},
            {"titulo": "Cacau Selecionado", "url": "https://images.unsplash.com/photo-1587132137056-bfbf0166836e?auto=format&fit=crop&w=600&h=800&q=80"},
        ]
    }
    galeria = galeria_data.get(restaurante.slug, [])

    slug_clean = restaurante.slug.replace('-', '').replace('_', '')
    cardapio_url = f"https://{slug_clean}.menudino.com"

    context = {
        'restaurante': restaurante,
        'atracoes': atracoes,
        'pratos_mock': pratos_mock,
        'galeria': galeria,
        'cardapio_url': cardapio_url,
    }
    return render(request, 'restaurantes/restaurante_detalhe.html', context)


def restaurante_lista(request):
    """
    Lista todos os restaurantes ativos com busca e filtros de especialidades.
    """
    busca = request.GET.get('busca', '').strip()
    especialidade = request.GET.get('especialidade', '').strip()

    from django.db.models import Q
    restaurantes_qs = Restaurante.objects.using('restaurantes').filter(ativo=True)

    if busca:
        restaurantes_qs = restaurantes_qs.filter(
            Q(nome__icontains=busca) |
            Q(cidade_nome__icontains=busca) |
            Q(especialidade__icontains=busca) |
            Q(descricao__icontains=busca)
        )
    
    if especialidade:
        restaurantes_qs = restaurantes_qs.filter(especialidade__iexact=especialidade)

    # Obter lista de especialidades únicas para o filtro rápido
    especialidades = list(
        Restaurante.objects.using('restaurantes').filter(ativo=True)
        .values_list('especialidade', flat=True)
        .distinct()
    )

    context = {
        'restaurantes': restaurantes_qs,
        'busca': busca,
        'especialidade_selecionada': especialidade,
        'especialidades': especialidades,
    }
    return render(request, 'restaurantes/restaurante_lista.html', context)
