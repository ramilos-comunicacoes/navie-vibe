from django.contrib import admin
from .models import Produtor, Local, Hotel, HotelImagem, Quarto, QuartoImagem, UnidadeQuarto, Reserva, BloqueioQuarto, HomeSlide

class HotelImagemInline(admin.TabularInline):
    model = HotelImagem
    extra = 1

class QuartoInline(admin.TabularInline):
    model = Quarto
    extra = 1

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'local', 'status', 'destaque', 'data_inicio')
    list_filter = ('status', 'destaque')
    search_fields = ('nome', 'local__nome')
    inlines = [HotelImagemInline, QuartoInline]

admin.site.register(Produtor)
admin.site.register(Local)

class UnidadeQuartoInline(admin.TabularInline):
    model = UnidadeQuarto
    extra = 1

@admin.register(Quarto)
class QuartoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'preco')
    inlines = [UnidadeQuartoInline]

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'unidade', 'data_checkin', 'data_checkout', 'status', 'valor_total')
    list_filter = ('status', 'data_checkin')

@admin.register(BloqueioQuarto)
class BloqueioQuartoAdmin(admin.ModelAdmin):
    list_display = ('unidade', 'data_inicio', 'data_fim', 'motivo')

@admin.register(HomeSlide)
class HomeSlideAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_midia', 'data_texto', 'local_texto', 'ordem', 'ativo')
    list_filter = ('ativo', 'tipo_midia')
    ordering = ('ordem', 'id')

