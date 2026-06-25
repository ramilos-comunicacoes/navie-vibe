# -*- coding: utf-8 -*-
"""
Clientes Views Package Initialization.
Imports and exposes all client-scoped views for clean routing configurations.

PURPOSE FOR AI AGENTS:
This file aggregates view functions from auth.py and dashboard.py.
"""
from .auth import login_cadastro_view, api_login, api_registrar, logout_view
from .dashboard import painel_view, criar_post_view, like_post_view, comentar_post_view, editar_perfil_view

__all__ = [
    'login_cadastro_view',
    'api_login',
    'api_registrar',
    'logout_view',
    'painel_view',
    'criar_post_view',
    'like_post_view',
    'comentar_post_view',
    'editar_perfil_view'
]
