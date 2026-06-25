from django.urls import path
from sistema import views

app_name = 'sistema'

urlpatterns = [
    # Autenticação e Sessão
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard Geral
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Pousadas
    path('pousadas/', views.pousada_list, name='pousada_list'),
    path('pousadas/formulario/', views.partner_pousada_formulario, name='partner_pousada_formulario'),
    path('pousadas/salvar/', views.partner_pousada_salvar, name='partner_pousada_salvar'),
    path('site/salvar/', views.partner_site_salvar, name='partner_site_salvar'),
    
    # Quartos & Tarifas (B2B Naviê)
    path('quartos/', views.quarto_list, name='quarto_list'),
    path('quartos/formulario/', views.partner_quarto_formulario, name='partner_quarto_formulario'),
    path('quartos/formulario/<int:quarto_id>/', views.partner_quarto_formulario, name='partner_quarto_formulario'),
    path('quartos/salvar/', views.partner_quarto_salvar, name='partner_quarto_salvar'),
    path('quartos/deletar/<int:quarto_id>/', views.partner_quarto_deletar, name='partner_quarto_deletar'),
    path('quartos/imagem/deletar/<int:imagem_id>/', views.partner_quarto_deletar_imagem, name='partner_quarto_deletar_imagem'),

    # Módulo de Reservas & Portaria (PMS Grid)
    path('reservas/', views.partner_reserva_list, name='partner_reserva_list'),
    path('reservas/grid/', views.partner_reserva_grid, name='partner_reserva_grid'),
    path('reservas/detalhe/<int:reserva_id>/', views.partner_reserva_detalhe, name='partner_reserva_detalhe'),
    path('reservas/detalhe/nova/', views.partner_reserva_detalhe, name='partner_reserva_detalhe_nova'),
    path('reservas/formulario/', views.partner_reserva_formulario, name='partner_reserva_formulario'),
    path('reservas/formulario/<int:reserva_id>/', views.partner_reserva_formulario, name='partner_reserva_formulario'),
    path('reservas/salvar/', views.partner_reserva_salvar, name='partner_reserva_salvar'),
    path('reservas/checkin/<int:reserva_id>/', views.partner_reserva_checkin, name='partner_reserva_checkin'),
    path('reservas/checkout/<int:reserva_id>/', views.partner_reserva_checkout, name='partner_reserva_checkout'),
    path('reservas/cancelar/<int:reserva_id>/', views.partner_reserva_cancelar, name='partner_reserva_cancelar'),
    path('reservas/excluir/<int:reserva_id>/', views.partner_reserva_excluir, name='partner_reserva_excluir'),
    path('reservas/hospede/salvar/<uuid:hospede_id>/', views.partner_salvar_hospede_fnrh, name='partner_salvar_hospede_fnrh'),
    path('reservas/hospede/documento/deletar/<uuid:documento_id>/', views.partner_deletar_documento_hospede, name='partner_deletar_documento_hospede'),
    path('reservas/salvar-estadia/<int:reserva_id>/', views.partner_salvar_estadia_veiculo, name='partner_salvar_estadia_veiculo'),
    path('reservas/pagamento/toggle/<int:reserva_id>/', views.partner_reserva_toggle_pagamento, name='partner_reserva_toggle_pagamento'),
    
    # Módulo de Serviço Unificado (Limpeza & Manutenção)
    path('servico/', views.servico_painel, name='servico_painel'),
    path('servico/limpeza/<int:tarefa_id>/status/', views.servico_limpeza_status, name='servico_limpeza_status'),
    path('servico/manutencao/<int:chamado_id>/status/', views.servico_manutencao_status, name='servico_manutencao_status'),
    path('servico/atividade/<int:tarefa_id>/concluir/', views.servico_completar_atividade, name='servico_completar_atividade'),
]
