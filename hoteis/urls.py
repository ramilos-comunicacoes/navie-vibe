from django.urls import path
from . import views
from financeiro import views as financeiro_views

app_name = 'hoteis'

urlpatterns = [
    path('', views.home, name='home'),
    path('hotel/<int:hotel_id>/', views.detalhe, name='detalhe'),
    path('hotel/<int:hotel_id>/acomodacao/<slug:quarto_slug>/', views.quarto_detalhe, name='quarto_detalhe'),
    path('api/hotel/<int:hotel_id>/check_disponibilidade/', views.api_check_disponibilidade, name='check_disponibilidade'),
    path('api/hotel/<int:hotel_id>/datas_ocupadas/', views.api_datas_ocupadas, name='datas_ocupadas'),
    path('hotelaria/', views.hotelaria, name='hotelaria'),
    
    # Gestão Hoteleira (Naviê Hospedagens)
    path('hospedagens/auth/', views.partner_auth, name='partner_login'),
    path('hospedagens/logout/', views.partner_logout, name='partner_logout'),
    path('hospedagens/sistema/', views.partner_dashboard, name='partner_dashboard'),
    path('hospedagens/ia_chat/', views.ia_enviar_chat, name='ia_enviar_chat'),
    path('hospedagens/atividades/criar/', views.partner_criar_tarefa, name='partner_criar_tarefa'),
    path('hospedagens/atividades/editar/<int:tarefa_id>/', views.partner_editar_tarefa, name='partner_editar_tarefa'),
    path('hospedagens/atividades/deletar/<int:tarefa_id>/', views.partner_deletar_tarefa, name='partner_deletar_tarefa'),
    path('hospedagens/atividades/mudar-status/<int:tarefa_id>/', views.partner_mudar_status_tarefa, name='partner_mudar_status_tarefa'),
    path('hospedagens/configuracoes/salvar/', views.partner_salvar_configuracoes, name='partner_salvar_configuracoes'),
    path('hospedagens/configuracoes/geral/salvar/', views.partner_salvar_configuracoes_geral, name='partner_salvar_configuracoes_geral'),
    path('hospedagens/financeiro/mp/conectar/', financeiro_views.view_mp_conectar, name='mp_conectar'),
    path('hospedagens/financeiro/mp/conectar-sandbox/', financeiro_views.view_mp_conectar_sandbox, name='mp_conectar_sandbox'),
    path('hospedagens/financeiro/mp/callback/', financeiro_views.view_mp_callback, name='mp_callback'),
    path('hospedagens/financeiro/mp/webhook/', financeiro_views.view_mp_webhook, name='mp_webhook'),
    
    # Gestão de Quartos (Reativa via HTMX)
    path('hospedagens/quartos/formulario/', views.partner_quarto_formulario, name='partner_quarto_formulario'),
    path('hospedagens/quartos/formulario/<int:quarto_id>/', views.partner_quarto_formulario, name='partner_quarto_formulario'),
    path('hospedagens/quartos/lista/', views.partner_quarto_lista, name='partner_quarto_lista'),
    path('hospedagens/quartos/salvar/', views.partner_quarto_salvar, name='partner_quarto_salvar'),
    path('hospedagens/quartos/deletar/<int:quarto_id>/', views.partner_quarto_deletar, name='partner_quarto_deletar'),
    path('hospedagens/quartos/liberar/<int:unidade_id>/', views.partner_liberar_quarto, name='partner_liberar_quarto'),
    path('hospedagens/quartos/detalhe-modal/<int:unidade_id>/', views.partner_detalhe_quarto_modal, name='partner_detalhe_quarto_modal'),
    path('hospedagens/quartos/atualizar-disponibilidade/<int:unidade_id>/', views.partner_atualizar_disponibilidade_quarto, name='partner_atualizar_disponibilidade_quarto'),
    path('hospedagens/quartos/imagem/deletar/<int:imagem_id>/', views.partner_quarto_deletar_imagem, name='partner_quarto_deletar_imagem'),
    
    # Carrinho e Checkout (B2C)
    path('carrinho/adicionar/<int:quarto_id>/', views.carrinho_adicionar, name='carrinho_adicionar'),
    path('carrinho/remover/', views.carrinho_remover, name='carrinho_remover'),
    path('carrinho/salvar-fnrh/', views.carrinho_salvar_fnrh, name='carrinho_salvar_fnrh'),
    path('carrinho/hospedes/definir/', views.carrinho_definir_hospedes, name='carrinho_definir_hospedes'),
    path('carrinho/veiculo/salvar/', views.carrinho_salvar_veiculo, name='carrinho_salvar_veiculo'),
    path('carrinho/checkout/', views.checkout_processar, name='checkout_processar'),
    path('carrinho/sucesso/<uuid:reserva_id>/', views.checkout_sucesso, name='checkout_sucesso'),
    
    # Operações de Portaria & Reservas B2B
    path('hospedagens/reservas/criar/', views.partner_reserva_criar, name='partner_reserva_criar'),
    path('hospedagens/reservas/<uuid:reserva_id>/', views.partner_reserva_detalhe, name='partner_reserva_detalhe'),
    path('hospedagens/reservas/<uuid:reserva_id>/salvar/', views.partner_reserva_salvar, name='partner_reserva_salvar'),
    path('hospedagens/reservas/<uuid:reserva_id>/checkin/', views.partner_reserva_checkin, name='partner_reserva_checkin'),
    path('hospedagens/reservas/<uuid:reserva_id>/checkout/', views.partner_reserva_checkout, name='partner_reserva_checkout'),
    path('hospedagens/reservas/<uuid:reserva_id>/checkout-mapa/', views.partner_checkout_quarto_mapa, name='partner_checkout_quarto_mapa'),
    path('hospedagens/reservas/<uuid:reserva_id>/cancelar/', views.partner_reserva_cancelar, name='partner_reserva_cancelar'),
    
    # Atendimento ao Hóspede, Concierge & Consumo
    path('hospedagens/hospedes/pedidos/', views.partner_hospedes_pedidos, name='partner_hospedes_pedidos'),
    path('hospedagens/hospedes/pedido/<int:pedido_id>/status/', views.partner_hospedes_atualizar_status, name='partner_hospedes_atualizar_status'),
    path('hospedagens/hospedes/reserva/<uuid:reserva_id>/lancar/', views.partner_hospedes_lancar_consumo, name='partner_hospedes_lancar_consumo'),
    
    # Gestão de Seções Modulares (CMS do Anfitrião)
    path('hospedagens/secoes/destaques/salvar/', views.partner_secao_destaques_salvar, name='partner_secao_destaques_salvar'),
    path('hospedagens/secoes/salvar/', views.partner_secao_salvar, name='partner_secao_salvar'),
    path('hospedagens/secoes/salvar/<int:secao_id>/', views.partner_secao_salvar, name='partner_secao_salvar'),
    path('hospedagens/secoes/deletar/<int:secao_id>/', views.partner_secao_deletar, name='partner_secao_deletar'),
    path('hospedagens/secoes/itens/salvar/', views.partner_secao_item_salvar, name='partner_secao_item_salvar'),
    path('hospedagens/secoes/itens/salvar/<int:item_id>/', views.partner_secao_item_salvar, name='partner_secao_item_salvar'),
    path('hospedagens/secoes/itens/deletar/<int:item_id>/', views.partner_secao_item_deletar, name='partner_secao_item_deletar'),
    
    path('cidade/<slug:cidade_slug>/', views.cidade_detalhe, name='cidade_detalhe'),
    path('api/hotel/verificar-subdominio/', views.api_verificar_subdominio, name='verificar_subdominio'),
    path('api/hotel/<int:hotel_id>/buscar-quartos/', views.api_buscar_quartos, name='api_buscar_quartos'),
    path('api/empresa/<int:empresa_id>/buscar-quartos/', views.api_buscar_quartos_grupo, name='api_buscar_quartos_grupo'),
    path('acomodacao/<slug:quarto_slug>/', views.quarto_detalhe_subdomain, name='quarto_detalhe_subdomain'),
    path('teste-404/', views.teste_404, name='teste_404'),
    path('<slug:slug>/', views.vanity_url, name='vanity_url'),
]


