from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    path('api/validar/', views.validar_voucher_api, name='validar_voucher_api'),
    path('api/confirmar/<uuid:voucher_id>/', views.processar_entrada_voucher, name='processar_entrada_voucher'),
]
