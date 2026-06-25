from django.urls import path
from . import views

app_name = 'administracao'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('solicitacao/<int:pk>/', views.solicitacao_detail_view, name='solicitacao_detail'),
    path('solicitacao/<int:pk>/status/', views.solicitacao_update_status_view, name='solicitacao_update_status'),
    path('documentos/', views.documentos_list_view, name='documentos_list'),
    path('documento/<int:pk>/editar/', views.documento_edit_view, name='documento_edit'),
    path('hoteis/', views.hoteis_list_view, name='hoteis_list'),
    path('hoteis/novo/', views.hotel_create_view, name='hotel_create'),
    path('hoteis/<int:pk>/editar/', views.hotel_edit_view, name='hotel_edit'),
    path('hoteis/<int:pk>/salvar-configuracao-admin/', views.hotel_salvar_configuracao_admin, name='hotel_salvar_configuracao_admin'),
    path('hoteis/<int:pk>/documentos/adicionar/', views.hotel_documento_adicionar, name='hotel_documento_adicionar'),
    path('hoteis/documentos/<int:doc_pk>/excluir/', views.hotel_documento_excluir, name='hotel_documento_excluir'),
    path('hoteis/<int:pk>/termos/registrar/', views.hotel_termo_registrar, name='hotel_termo_registrar'),
    path('hoteis/<int:pk>/tarifas-faixa/salvar/', views.hotel_tarifas_faixa_salvar, name='hotel_tarifas_faixa_salvar'),
    path('hoteis/tarifas-faixa/<int:faixa_pk>/excluir/', views.hotel_tarifa_faixa_excluir, name='hotel_tarifa_faixa_excluir'),
    path('configuracao/salvar-padroes/', views.salvar_configuracao_sistema, name='salvar_configuracao_sistema'),
]
