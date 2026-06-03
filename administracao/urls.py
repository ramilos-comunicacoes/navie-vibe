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
]
