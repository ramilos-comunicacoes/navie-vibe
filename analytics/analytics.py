from django.db import models
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count
from django.utils import timezone
from .models import UserInteraction, CarrinhoStatus, RegistroConsumo

def limpar_historico_antigo(tracker_id, usuario=None):
    """
    Mantém apenas as interações dos últimos 30 dias ativos de uso para o tracker_id ou usuario.
    Um 'dia ativo' é uma data única em que houve pelo menos uma interação registrada.
    """
    q_filter = models.Q(tracker_id=tracker_id)
    if usuario and usuario.is_authenticated:
        q_filter |= models.Q(usuario=usuario)
        
    # Obtém as datas únicas em que houve interação, ordenadas do mais recente ao mais antigo
    datas_ativas = list(
        UserInteraction.objects.filter(q_filter)
        .annotate(data=TruncDate('criado_em'))
        .values_list('data', flat=True)
        .order_by('-data')
        .distinct()
    )
    
    if len(datas_ativas) > 30:
        # A 30ª data mais recente é o limite
        cutoff_date = datas_ativas[29]
        # Deleta registros com data estritamente menor que a cutoff_date
        UserInteraction.objects.filter(q_filter, criado_em__date__lt=cutoff_date).delete()


def registrar_consumo_unificado(usuario, tracker_id, category, item_id, nome, preco, quantidade=1):
    """
    Cria um registro unificado de consumo no banco de dados.
    """
    user_val = usuario if (usuario and usuario.is_authenticated) else None
    return RegistroConsumo.objects.create(
        usuario=user_val,
        tracker_id=tracker_id,
        category=category,
        item_id=str(item_id),
        nome=nome,
        preco=preco,
        quantidade=quantidade
    )


def obter_perfil_interesses_usuario(tracker_id, usuario=None):
    """
    Consolida o perfil de interesses do usuário cruzando visualizações de página, 
    carrinhos abandonados e histórico de consumo.
    Retorna uma estrutura pronta para alimentar motores de sugestões.
    """
    q_filter = models.Q(tracker_id=tracker_id)
    if usuario and usuario.is_authenticated:
        q_filter |= models.Q(usuario=usuario)

    # 1. Agrupar as páginas visitadas por categoria e item_id, somando o tempo gasto e contagem
    visualizacoes = (
        UserInteraction.objects.filter(q_filter)
        .values('category', 'item_id', 'parent_id')
        .annotate(
            total_tempo=Sum('time_spent'),
            total_visitas=Count('id')
        )
        .order_by('-total_tempo', '-total_visitas')
    )

    # 2. Obter carrinhos atualmente abandonados (não recuperados)
    carrinhos_pendentes = (
        CarrinhoStatus.objects.filter(q_filter, recuperado=False)
        .values('category', 'item_id', 'quantidade', 'metadata', 'criado_em')
        .order_by('-criado_em')
    )

    # 3. Obter itens consumidos historicamente
    q_filter_consumo = models.Q(tracker_id=tracker_id)
    if usuario and usuario.is_authenticated:
        q_filter_consumo |= models.Q(usuario=usuario)
        
    consumos = (
        RegistroConsumo.objects.filter(q_filter_consumo)
        .values('category', 'item_id', 'nome')
        .annotate(
            quantidade_total=Sum('quantidade'),
            gasto_total=Sum(models.F('quantidade') * models.F('preco'), output_field=models.DecimalField())
        )
        .order_by('-quantidade_total')
    )

    # Categorias mais visitadas baseado no tempo de tela
    categorias_tempo = (
        UserInteraction.objects.filter(q_filter)
        .values('category')
        .annotate(total_tempo=Sum('time_spent'))
        .order_by('-total_tempo')
    )
    categorias_preferidas = [c['category'] for c in categorias_tempo if c['category']]

    return {
        'categorias_preferidas': categorias_preferidas,
        'itens_mais_visualizados': list(visualizacoes),
        'carrinhos_abandonados': list(carrinhos_pendentes),
        'historico_consumo': list(consumos)
    }
