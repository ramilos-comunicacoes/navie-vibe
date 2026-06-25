from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def direcao_required(view_func):
    """
    Permite apenas usuários com cargo 'DIRECAO' ou superusuários.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('sistema:login')
        if request.user.is_superuser or request.user.role == 'DIRECAO':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view

def portaria_required(view_func):
    """
    Permite apenas usuários com cargo 'DIRECAO', 'PORTARIA' ou superusuários.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('sistema:login')
        if request.user.is_superuser or request.user.role in ['DIRECAO', 'PORTARIA']:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view

def servico_required(view_func):
    """
    Permite apenas usuários com cargo 'DIRECAO', 'SERVICO' ou superusuários.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('sistema:login')
        if request.user.is_superuser or request.user.role in ['DIRECAO', 'SERVICO']:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view
