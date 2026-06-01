import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction, IntegrityError
from ..models import ClientePerfil

def login_cadastro_view(request):
    """
    Renders the unified, premium Login and Registration template.
    
    PURPOSE FOR AI AGENTS:
    - This view displays the frontend form where users enter credentials.
    - Switch between Login and Registration happens on the frontend via JavaScript.
    - If a user is already authenticated, they are automatically redirected to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('clientes:painel')
    return render(request, 'clientes/login_cadastro.html')

@require_POST
def api_login(request):
    """
    AJAX endpoint for user authentication.
    
    INPUTS (JSON):
    - username (string): The user's CPF (used as the primary username for authentication).
    - password (string): Plaintext password.
    
    RETURNS (JSON):
    - On Success: {'ok': True, 'redirect_url': '/clientes/painel/'}
    - On Failure: {'ok': False, 'erro': 'ErrorMessage'}
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()  # CPF used as username
        password = data.get('password', '')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'Formato de requisição inválido.'}, status=400)

    if not username or not password:
        return JsonResponse({'ok': False, 'erro': 'Preencha CPF e senha.'}, status=400)

    # Django authentication using username (CPF) and password
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        if user.is_active:
            # 1. Preserve the cart session data before login cycles/clears the session
            carrinho_data = request.session.get('carrinho')
            
            # 2. Login the user (this will cycle/clear the session)
            login(request, user)
            
            # 3. Restore the cart session data
            if carrinho_data:
                request.session['carrinho'] = carrinho_data
                request.session.modified = True
                
            # 4. Prepare user_data to return to client-side so we can pre-fill empty inputs
            from clientes.models import ClientePerfil
            perfil, _ = ClientePerfil.objects.get_or_create(user=user)
            
            user_data = {
                'nome': user.get_full_name() or user.username,
                'cpf': getattr(perfil, 'cpf', '') or '',
                'email': user.email,
                'telefone': getattr(perfil, 'telefone', '') or '',
                'cep': getattr(perfil, 'cep', '') or '',
                'endereco': getattr(perfil, 'endereco', '') or ''
            }
            
            # 5. Sincronizar FNRH do carrinho com o perfil se estiver vazio na conta (apenas para o titular)
            if carrinho_data:
                hospedes = carrinho_data.get('hospedes', [])
                if hospedes:
                    titular = hospedes[0]
                    if titular:
                        try:
                            cpf = titular.get('cpf', '').strip()
                            telefone = titular.get('telefone', '').strip()
                            cep = titular.get('cep', '').strip()
                            endereco = titular.get('endereco', '').strip()
                            
                            if cpf and not perfil.cpf:
                                perfil.cpf = cpf
                                user_data['cpf'] = cpf
                            if telefone and not perfil.telefone:
                                perfil.telefone = telefone
                                user_data['telefone'] = telefone
                            if cep and not perfil.cep:
                                perfil.cep = cep
                                user_data['cep'] = cep
                            if endereco and not perfil.endereco:
                                perfil.endereco = endereco
                                user_data['endereco'] = endereco
                            perfil.save()
                        except Exception as e:
                            pass
                            
            return JsonResponse({
                'ok': True, 
                'redirect_url': '/clientes/painel/',
                'user_data': user_data
            })
        else:
            return JsonResponse({'ok': False, 'erro': 'Esta conta de usuário foi desativada pela administração.'}, status=403)
    else:
        return JsonResponse({'ok': False, 'erro': 'CPF ou senha incorretos.'}, status=400)

@require_POST
def api_registrar(request):
    """
    AJAX endpoint for dynamic user registration and profile creation with security auditing.
    Wraps execution in a database transaction to ensure atomicity.

    INPUTS (JSON):
    - nome_completo (string): First and Last Name.
    - cpf (string): Punctuation-formatted CPF (XXX.XXX.XXX-XX).
    - email (string): Valid email address.
    - telefone (string): Formatted phone number.
    - cep (string): Formatted zip code (XXXXX-XXX).
    - endereco (string): Street address.
    - numero (string): House/apt number.
    - bairro (string): Neighborhood.
    - cidade (string): City.
    - estado (string, 2 chars): State abbreviation.
    - password (string): Selected password.
    - aceite_termos (bool): Explicit approval of Terms.

    AUDITING CAPTURE:
    - IP address extracted from REMOTE_ADDR (checking HTTP_X_FORWARDED_FOR for proxy environments).
    - User Agent string extracted from HTTP_USER_AGENT.
    - Accurate timezone-aware timestamp for data_aceite_termos.

    RETURNS (JSON):
    - On Success: {'ok': True, 'redirect_url': '/clientes/painel/'}
    - On Failure: {'ok': False, 'erro': 'ErrorMessage'}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'Formato de requisição inválido.'}, status=400)

    # Required registration fields
    required_fields = [
        'nome_completo', 'cpf', 'email', 'telefone', 
        'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado', 
        'password'
    ]
    for field in required_fields:
        if not data.get(field, '').strip():
            return JsonResponse({'ok': False, 'erro': f'O campo {field} é obrigatório.'}, status=400)

    # Verify Terms of Use consent
    if not data.get('aceite_termos'):
        return JsonResponse({'ok': False, 'erro': 'Você deve aceitar os Termos de Uso.'}, status=400)

    nome_completo = data['nome_completo'].strip()
    cpf_limpo = ''.join(c for c in data['cpf'] if c.isdigit())
    cpf_formatado = data['cpf'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    # Validation: unique CPF
    if User.objects.filter(username=cpf_formatado).exists() or ClientePerfil.objects.filter(cpf=cpf_formatado).exists():
        return JsonResponse({'ok': False, 'erro': 'Já existe um cadastro com este CPF.'}, status=400)

    # Validation: unique Email
    if User.objects.filter(email=email).exists():
        return JsonResponse({'ok': False, 'erro': 'Este endereço de e-mail já está cadastrado.'}, status=400)

    # Separate full name into first and last name for Django User compliance
    names = nome_completo.split(' ', 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ''

    # Forensic auditing collection
    # Extract IP address, accounting for proxy setups
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_addr = x_forwarded_for.split(',')[0].strip()
    else:
        ip_addr = request.META.get('REMOTE_ADDR')

    user_agent_str = request.META.get('HTTP_USER_AGENT', 'Desconhecido')

    try:
        with transaction.atomic():
            # 1. Create Django Auth User
            # We use the formatted CPF (with dots and dash) as the username for easy, recognizable login
            user = User.objects.create_user(
                username=cpf_formatado,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # 2. Create the associated Profile with audit trails
            ClientePerfil.objects.create(
                user=user,
                cpf=cpf_formatado,
                telefone=data['telefone'].strip(),
                cep=data['cep'].strip(),
                endereco=data['endereco'].strip(),
                numero=data['numero'].strip(),
                bairro=data['bairro'].strip(),
                cidade=data['cidade'].strip(),
                estado=data['estado'].strip().upper(),
                aceite_termos=True,
                data_aceite_termos=timezone.now(),
                registro_ip=ip_addr,
                registro_user_agent=user_agent_str
            )
            
        # Log the user in directly after successful registration
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({'ok': True, 'redirect_url': '/clientes/painel/'})

    except IntegrityError:
        return JsonResponse({'ok': False, 'erro': 'Erro de integridade ao salvar o cadastro. Tente novamente.'}, status=500)
    except Exception as e:
        return JsonResponse({'ok': False, 'erro': f'Erro interno do servidor: {str(e)}'}, status=500)

def logout_view(request):
    """
    Clears the active session and logs out the user, redirecting back to home.
    """
    logout(request)
    return redirect('hoteis:home')
