from django.urls import path
from . import views

app_name = 'restaurantes'

urlpatterns = [
    path('', views.restaurante_lista, name='restaurante_lista'),
    path('auth/', views.partner_auth, name='partner_login'),
    path('logout/', views.partner_logout, name='partner_logout'),
    path('sistema/', views.partner_dashboard, name='partner_dashboard'),
    path('sistema/configuracoes/salvar/', views.partner_salvar_configuracoes, name='partner_salvar_configuracoes'),
    path('sistema/atracoes/salvar/', views.partner_salvar_atracao, name='partner_salvar_atracao'),
    path('sistema/atracoes/deletar/<int:atracao_id>/', views.partner_deletar_atracao, name='partner_deletar_atracao'),
    path('<slug:slug>/', views.restaurante_detalhe, name='restaurante_detalhe'),
]
