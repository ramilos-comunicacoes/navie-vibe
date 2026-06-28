from django.urls import path
from . import views

app_name = 'restaurantes'

urlpatterns = [
    path('auth/', views.partner_auth, name='partner_login'),
    path('logout/', views.partner_logout, name='partner_logout'),
    path('sistema/', views.partner_dashboard, name='partner_dashboard'),
    path('sistema/configuracoes/salvar/', views.partner_salvar_configuracoes, name='partner_salvar_configuracoes'),
    path('<slug:slug>/', views.restaurante_detalhe, name='restaurante_detalhe'),
]
