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
                # Checa se o usuário possui perfil de restaurante
                if hasattr(user, 'perfil_restaurante'):
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
    """
    # Garante que possui perfil de restaurante
    if not hasattr(request.user, 'perfil_restaurante'):
        messages.error(request, "Acesso negado. Esta conta não possui perfil de restaurante.")
        return redirect('restaurantes:partner_login')
        
    perfil = request.user.perfil_restaurante
    restaurante = perfil.restaurante
    
    # Atrações cadastradas
    atracoes = RestauranteAtracao.objects.using('restaurantes').filter(restaurante=restaurante)
    
    context = {
        'perfil': perfil,
        'restaurante': restaurante,
        'atracoes': atracoes,
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
            return redirect('/sistema/?tab=configuracoes')
        restaurante.sobre_video = video_file

    if request.POST.get('remover_hero_video') == 'true':
        restaurante.hero_video = None
    elif 'hero_video' in request.FILES:
        video_file = request.FILES['hero_video']
        if video_file.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo em loop do hero ultrapassa o limite de 8MB permitido.")
            return redirect('/sistema/?tab=configuracoes')
        restaurante.hero_video = video_file
        
    restaurante.save(using='restaurantes')
    messages.success(request, "Configurações do restaurante salvas com sucesso.")
    return redirect('/sistema/?tab=configuracoes')


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
    atracao.ativo = request.POST.get('ativo') == 'true' or request.POST.get('ativo') == 'on' or True
    
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
            return redirect('/sistema/?tab=configuracoes&sub=destaques')
        atracao.video = video_file
        
    atracao.save(using='restaurantes')
    messages.success(request, "Atração salva com sucesso.")
    return redirect('/sistema/?tab=configuracoes&sub=destaques')


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
    return redirect('/sistema/?tab=configuracoes&sub=destaques')


def restaurante_detalhe(request, slug):
    """
    Página pública (B2C) do restaurante — exibe o hero, atração do dia,
    destaques do cardápio, mapa de localização e seção sobre.
    """
    from django.shortcuts import get_object_or_404
    restaurante = get_object_or_404(Restaurante.objects.using('restaurantes'), slug=slug, ativo=True)

    # Busca as atrações ativas do restaurante
    atracoes = RestauranteAtracao.objects.using('restaurantes').filter(restaurante=restaurante, ativo=True)
    
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
        MockPrato("Filé ao Molho Especial", "Prato Principal", "Filé mignon grelhado com molho de ervas frescas e acompanhamentos da estação.", "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80"),
        MockPrato("Risoto de Cogumelos", "Entrada Premium", "Risoto cremoso preparado com mix de cogumelos frescos e parmesão artesanal.", "https://images.unsplash.com/photo-1476124369491-e7addf5db371?auto=format&fit=crop&w=800&q=80"),
        MockPrato("Frango Assado da Serra", "Regional", "Frango caipira assado lentamente com temperos regionais e farofa de mandioca.", "https://images.unsplash.com/photo-1598103442097-8b74394b95c5?auto=format&fit=crop&w=800&q=80"),
        MockPrato("Carne de Sol com Nata", "Clássico Nordestino", "Tradicional carne de sol grelhada servida com nata da terra e pirão.", "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80"),
        MockPrato("Sobremesa da Casa", "Doces & Sobremesas", "Mousse especial de chocolate com calda de frutas vermelhas da propriedade.", "https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?auto=format&fit=crop&w=800&q=80"),
    ]

    context = {
        'restaurante': restaurante,
        'atracoes': atracoes,
        'pratos_mock': pratos_mock,
    }
    return render(request, 'restaurantes/restaurante_detalhe.html', context)
