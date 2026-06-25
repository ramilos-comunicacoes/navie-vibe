"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rota do super app da parte pública (Website)
    path('', include('website.urls')),
    
    # Rota do super app do sistema interno (PMS)
    path('sistema/', include('sistema.urls')),
    
    # Rota do módulo de estoque e compras
    path('sistema/estoque/', include('estoque.urls')),
    
    # Rota do módulo de agenda e kanban
    path('sistema/agenda/', include('agenda.urls')),
]

# Servir arquivos de mídia e estáticos localmente no ambiente de desenvolvimento (VPS/Local)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

