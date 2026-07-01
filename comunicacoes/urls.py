from django.urls import path
from . import views

app_name = 'comunicacoes'

urlpatterns = [
    path('testar/', views.testar_email_reserva, name='testar_email'),
]
