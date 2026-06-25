from sistema.views.auth_views import login_view, logout_view
from sistema.views.dashboard_views import dashboard_view, obter_contexto_pousada
from sistema.views.pousada_views import pousada_list, partner_pousada_formulario, partner_pousada_salvar, partner_site_salvar
from sistema.views.quarto_views import (
    quarto_list, partner_quarto_formulario, partner_quarto_salvar,
    partner_quarto_deletar, partner_quarto_deletar_imagem
)
from sistema.views.reserva_views import (
    partner_reserva_list, partner_reserva_grid, partner_reserva_detalhe,
    partner_reserva_formulario, partner_reserva_salvar,
    partner_reserva_checkin, partner_reserva_checkout, partner_reserva_cancelar,
    partner_salvar_hospede_fnrh, partner_deletar_documento_hospede,
    partner_salvar_estadia_veiculo, partner_reserva_excluir,
    partner_reserva_toggle_pagamento
)
from sistema.views.servico_views import servico_painel, servico_limpeza_status, servico_manutencao_status, servico_completar_atividade
