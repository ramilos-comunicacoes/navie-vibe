from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache
from .models import RestauranteUsuario, Restaurante

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
    
    context = {
        'perfil': perfil,
        'restaurante': restaurante,
    }
    return render(request, 'restaurantes/partner_dashboard.html', context)

def partner_logout(request):
    """
    Encerra a sessão do parceiro de restaurante.
    """
    auth_logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('restaurantes:partner_login')


def restaurante_detalhe(request, slug):
    """
    Página pública (B2C) do restaurante — exibe o hero, atração do dia,
    destaques do cardápio, mapa de localização e seção sobre.
    """
    from django.shortcuts import get_object_or_404
    restaurante = get_object_or_404(Restaurante.objects.using('restaurantes'), slug=slug, ativo=True)

    # Atração do Dia (mock até o sistema de gestão estar pronto)
    class MockAtracao:
        titulo = None
        texto = None
        banner = None
        video = None
        midia_tipo = 'imagem'
        cor_fundo = '#0f172a'
        cor_texto = '#ffffff'
        whatsapp = None

    atracao = MockAtracao()

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
        'atracao': atracao,
        'pratos_mock': pratos_mock,
    }
    return render(request, 'restaurantes/restaurante_detalhe.html', context)
