from django.shortcuts import render
from sistema.models import Pousada, CategoriaQuarto, Quarto

# ==============================================================================
# VIEW: PÁGINA INICIAL PÚBLICA (Website)
# Exibe a vitrine de quartos das Pousadas Ramiros no estilo Airbnb.
# ==============================================================================
def home_view(request):
    """
    Renderiza a landing page pública do website da Pousada Ramiros.
    Lista as pousadas e as categorias de quartos com base nos dados do PMS interno.
    Suporta filtros rápidos de busca de disponibilidade.
    """
    from sistema.models import SiteConfig
    config = SiteConfig.objects.first()
    if not config:
        config = SiteConfig.objects.create()

    pousadas = Pousada.objects.filter(ativo=True)
    categorias = CategoriaQuarto.objects.filter(ativo=True)
    
    # Se houver filtro de pousada na busca
    pousada_filtro = request.GET.get('pousada')
    quartos_disponiveis = Quarto.objects.filter(status='LIVRE')
    
    if pousada_filtro and pousada_filtro != 'todas':
        quartos_disponiveis = quartos_disponiveis.filter(pousada_id=pousada_filtro)
        
    context = {
        'pousadas': pousadas,
        'categorias': categorias,
        'quartos_disponiveis': quartos_disponiveis,
        'pousada_selecionada': pousada_filtro,
        'config': config,
    }
    
    # Se a requisição vier via HTMX para filtrar a listagem de quartos
    if request.headers.get('HX-Request'):
        return render(request, 'website/partials/room_list.html', context)
        
    return render(request, 'website/home.html', context)


# ==============================================================================
# VIEW: PÁGINA DE DETALHES DO QUARTO (B2C)
# Exibe galeria cinemática, tour de vídeo local, calendário e controle de carrinho.
# ==============================================================================
def quarto_detalhe(request, slug):
    """
    Exibe a página de detalhes para uma CategoriaQuarto específica identificada pelo slug.
    Calcula dinamicamente a disponibilidade de datas dos quartos físicos correspondentes.
    """
    from django.shortcuts import get_object_or_404
    import datetime
    import json
    from django.utils import timezone
    from sistema.models import CategoriaQuarto, QuartoImagem, Quarto, Reserva, BloqueioQuarto

    quarto = get_object_or_404(CategoriaQuarto, slug=slug, ativo=True)
    hotel = quarto.pousada
    
    # Busca imagens da galeria
    imagens = QuartoImagem.objects.filter(categoria=quarto).order_by('ordem')
    primeira_imagem = imagens.first() if imagens.exists() else None
    outras_imagens = list(imagens[1:]) if imagens.count() > 1 else []
    
    # Processa Tags e Comodidades
    tags_list = [t.strip() for t in quarto.tags.split(',') if t.strip()] if quarto.tags else []
    comodidades_list = [c.strip() for c in quarto.comodidades.split(',') if c.strip()] if quarto.comodidades else []
    
    # Motor de Disponibilidade Reativo (Próximos 180 dias)
    quartos_fisicos = Quarto.objects.filter(categoria=quarto)
    total_quartos = quartos_fisicos.count()
    
    occupied_dates = []
    if total_quartos > 0:
        today = timezone.localdate()
        for i in range(180):
            day = today + datetime.timedelta(days=i)
            
            # Reservas ativas que tocam este dia
            reservas_count = Reserva.objects.filter(
                quarto__categoria=quarto,
                data_checkin__lte=day,
                data_checkout__gt=day
            ).exclude(status='CANCELADA').count()
            
            # Bloqueios administrativos que cobrem este dia
            bloqueios_count = BloqueioQuarto.objects.filter(
                quarto__categoria=quarto,
                data_inicio__lte=day,
                data_fim__gte=day
            ).count()
            
            if (reservas_count + bloqueios_count) >= total_quartos:
                occupied_dates.append(day.strftime('%Y-%m-%d'))
                
    context = {
        'quarto': quarto,
        'hotel': hotel,
        'primeira_imagem': primeira_imagem,
        'outras_imagens': outras_imagens,
        'tags': tags_list,
        'comodidades': comodidades_list,
        'datas_ocupadas_json': json.dumps(occupied_dates),
        'solid_header': True,
    }
    
    return render(request, 'website/quarto_detalhe.html', context)


# ==============================================================================
# VIEW: VITRINE EXCLUSIVA DA POUSADA (B2C)
# Exibe quartos de uma única pousada física, mantendo cabeçalho sólido.
# ==============================================================================
def pousada_detalhe(request, pousada_id):
    """
    Exibe a vitrine de quartos exclusiva para uma pousada física B2C.
    Filtra e lista todos os quartos operacionais e livres pertencentes a esta unidade.
    """
    from django.shortcuts import get_object_or_404
    from sistema.models import Pousada, Quarto
    
    pousada = get_object_or_404(Pousada, id=pousada_id, ativo=True)
    quartos_disponiveis = Quarto.objects.filter(pousada=pousada, status='LIVRE').select_related('categoria', 'pousada')
    
    context = {
        'pousada': pousada,
        'quartos_disponiveis': quartos_disponiveis,
        'solid_header': True,
    }
    
    return render(request, 'website/pousada_detalhe.html', context)


