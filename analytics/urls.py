from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('track/', views.api_registrar_interacao, name='api_registrar_interacao'),
]
