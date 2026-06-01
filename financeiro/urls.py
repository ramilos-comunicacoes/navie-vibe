from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    # Rota para criação de lançamentos contábeis (compatível com formulários convencionais, chamadas Ajax e agentes de IA)
    path('api/transacao/nova/', views.criar_transacao_api, name='criar_transacao'),
]
