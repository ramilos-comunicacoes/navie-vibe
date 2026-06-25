from django.urls import path
from . import views

# Routing namespace for the 'clientes' app.
# Allows standard reverse mapping like {% url 'clientes:painel' %}
app_name = 'clientes'

urlpatterns = [
    # ─── Page Render Views ───────────────────────────────────────────────────
    path('login/', views.login_cadastro_view, name='login_cadastro'),
    path('painel/', views.painel_view, name='painel'),
    
    # ─── AJAX API endpoints (Single Page authentication flow) ───────────────
    path('api/login/', views.api_login, name='api_login'),
    path('api/registrar/', views.api_registrar, name='api_registrar'),
    
    # ─── Social Moments & Profile Config ─────────────────────────────────────
    path('momentos/criar/', views.criar_post_view, name='criar_post'),
    path('momentos/like/<str:post_id>/', views.like_post_view, name='like_post'),
    path('momentos/comentar/<str:post_id>/', views.comentar_post_view, name='comentar_post'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    
    # ─── Session Destroy View ────────────────────────────────────────────────
    path('logout/', views.logout_view, name='logout'),
]
