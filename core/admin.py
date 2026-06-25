from django.contrib import admin
from .models import Empresa

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'cnpj', 'categoria', 'modalidade_portal', 'slug', 'ativa')
    list_filter = ('categoria', 'modalidade_portal', 'ativa')
    search_fields = ('nome_fantasia', 'cnpj', 'slug')
