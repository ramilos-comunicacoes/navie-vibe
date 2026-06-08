from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # Produtos
    path('produto/criar/', views.criar_produto, name='criar_produto'),
    path('produto/<int:produto_id>/editar/', views.editar_produto, name='editar_produto'),
    path('produto/<int:produto_id>/excluir/', views.excluir_produto, name='excluir_produto'),
    
    # Categorias
    path('categoria/criar/', views.criar_categoria, name='criar_categoria'),
    
    # Fornecedores
    path('fornecedor/criar/', views.criar_fornecedor, name='criar_fornecedor'),
    
    # Compras
    path('compra/criar/', views.criar_compra, name='criar_compra'),
    path('compra/<int:compra_id>/receber/', views.receber_compra, name='receber_compra'),
    path('compra/<int:compra_id>/cancelar/', views.cancelar_compra, name='cancelar_compra'),
    path('compra/<int:compra_id>/toggle-pago/', views.toggle_compra_pago, name='toggle_compra_pago'),
    path('compra/<int:compra_id>/toggle-recebido/', views.toggle_compra_recebido, name='toggle_compra_recebido'),
    
    # Movimentos
    path('movimento/registrar/', views.registrar_movimento, name='registrar_movimento'),
    path('movimento/<int:movimento_id>/reverter/', views.reverter_movimento, name='reverter_movimento'),
    path('movimento/<int:movimento_id>/relancar/', views.relancar_movimento, name='relancar_movimento'),
]
