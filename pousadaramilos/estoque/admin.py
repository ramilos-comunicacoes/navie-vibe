from django.contrib import admin
from .models import CategoriaProduto, Fornecedor, Produto, Compra, ItemCompra, MovimentoEstoque, ProdutoConsumo

@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'icone')
    search_fields = ('nome', 'hotel__nome')
    list_filter = ('hotel',)

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'telefone', 'email', 'ativo')
    search_fields = ('nome', 'hotel__nome', 'cnpj_cpf')
    list_filter = ('ativo', 'hotel')

class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'categoria', 'unidade_medida', 'finalidade', 'estoque_atual', 'estoque_minimo', 'ativo')
    search_fields = ('nome', 'hotel__nome', 'categoria__nome')
    list_filter = ('ativo', 'finalidade', 'unidade_medida', 'hotel')

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'hotel', 'fornecedor', 'data_compra', 'valor_total', 'status')
    search_fields = ('id', 'fornecedor__nome', 'hotel__nome')
    list_filter = ('status', 'data_compra', 'hotel')
    inlines = [ItemCompraInline]

@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'hotel', 'tipo', 'quantidade', 'referencia', 'criado_em')
    search_fields = ('produto__nome', 'referencia', 'hotel__nome')
    list_filter = ('tipo', 'hotel')

@admin.register(ProdutoConsumo)
class ProdutoConsumoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'estoque_produto', 'preco', 'tipo', 'disponivel')
    search_fields = ('nome', 'hotel__nome')
    list_filter = ('disponivel', 'tipo', 'hotel')
