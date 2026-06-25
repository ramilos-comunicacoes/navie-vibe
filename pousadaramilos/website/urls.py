from django.urls import path
from website import views

app_name = 'website'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('carrinho/adicionar/<int:categoria_id>/', views.carrinho_adicionar, name='carrinho_adicionar'),
    path('carrinho/remover/', views.carrinho_remover, name='carrinho_remover'),
    path('carrinho/definir-hospedes/', views.carrinho_definir_hospedes, name='carrinho_definir_hospedes'),
    path('carrinho/salvar-fnrh/', views.carrinho_salvar_fnrh, name='carrinho_salvar_fnrh'),
    path('checkout/processar/', views.checkout_processar, name='checkout_processar'),
    path('checkout/sucesso/<int:reserva_id>/', views.checkout_sucesso, name='checkout_sucesso'),
    path('quartos/<slug:slug>/', views.quarto_detalhe, name='quarto_detalhe'),
    path('pousada/<int:pousada_id>/', views.pousada_detalhe, name='pousada_detalhe'),
]
