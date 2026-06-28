from django.urls import path
from . import views

app_name = 'restaurantes'

urlpatterns = [
    path('auth/', views.partner_auth, name='partner_login'),
    path('logout/', views.partner_logout, name='partner_logout'),
    path('sistema/', views.partner_dashboard, name='partner_dashboard'),
]
