from django.urls import path
from . import views

app_name = 'agenda'

urlpatterns = [
    path('', views.painel_atividades, name='painel_atividades'),
    path('nova/', views.nova_tarefa, name='nova_tarefa'),
    path('<int:pk>/editar/', views.editar_tarefa, name='editar_tarefa'),
    path('<int:pk>/status/', views.mudar_status, name='mudar_status'),
    path('<int:pk>/deletar/', views.deletar_tarefa, name='deletar_tarefa'),
]
