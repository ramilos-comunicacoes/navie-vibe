from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

# ==============================================================================
# VIEW: LOGIN
# Gerencia a autenticação dos funcionários da pousada com base em suas credenciais.
# Renderiza a tela de login Split Screen (partner_login.html).
# ==============================================================================
def login_view(request):
    """
    Realiza o login de usuários (Gerentes, Recepcionistas, Camareiras e Manutenção).
    Se já estiver logado, redireciona diretamente para o dashboard geral.
    """
    # Se o usuário já está autenticado, manda direto para a página interna
    if request.user.is_authenticated:
        return redirect('sistema:dashboard')

    if request.method == 'POST':
        usuario_ou_email = request.POST.get('username', '').strip()
        senha_secreta = request.POST.get('password', '')

        # Tenta autenticar utilizando as credenciais informadas
        # Como o Django por padrão usa username, o authenticate faz essa validação.
        usuario = authenticate(request, username=usuario_ou_email, password=senha_secreta)

        if usuario is not None:
            if usuario.is_active:
                # Realiza a sessão de login oficial do Django
                auth_login(request, usuario)
                
                # Redireciona para o painel principal
                return redirect('sistema:dashboard')
            else:
                messages.error(request, "Esta conta está desativada no sistema. Fale com o Administrador.")
        else:
            messages.error(request, "Credenciais inválidas. Verifique seu usuário e senha secreta.")

    # Renderiza o template de login split-screen premium do Naviê Hospedagens
    return render(request, 'partner_login.html')


# ==============================================================================
# VIEW: LOGOUT
# Encerra de forma segura a sessão ativa do usuário e o redireciona ao login.
# ==============================================================================
@login_required(login_url='sistema:login')
def logout_view(request):
    """
    Destrói a sessão ativa do Django e redireciona o usuário para a tela de login.
    """
    # Armazena o nome antes de limpar a sessão para uma mensagem de despedida amigável
    nome_usuario = request.user.nome_completo or request.user.username
    auth_logout(request)
    messages.info(request, f"Até logo, {nome_usuario}. Sua sessão foi encerrada com segurança.")
    
    return redirect('sistema:login')
