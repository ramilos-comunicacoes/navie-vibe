from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from sistema.models import Pousada, CategoriaQuarto, Quarto, QuartoImagem
from sistema.views.dashboard_views import obter_contexto_pousada
from sistema.decorators import direcao_required

# ==============================================================================
# 1. VIEW: LISTAGEM DE QUARTOS & TARIFAS (PMS)
# Suporta requisições normais (GET) e assíncronas (HTMX) para atualizar o grid.
# ==============================================================================
@direcao_required
def quarto_list(request):
    """
    Exibe a listagem de categorias de quartos da pousada ativa.
    Se a requisição for HTMX, retorna apenas o grid de cartões para swap.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if pousada_ativa:
        categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True).prefetch_related('imagens', 'quartos')
    else:
        categorias = CategoriaQuarto.objects.none()
        
    context = {
        **pousada_ctx,
        'categorias': categorias,
        'quartos_qs': CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True) # Para compatibilidade com a sidebar
    }
    
    # Se for requisição HTMX para atualizar a listagem
    if request.headers.get('HX-Request'):
        return render(request, 'sistema/quartos/partials/quarto_grid.html', context)
        
    return render(request, 'sistema/quartos/quarto_list.html', context)


# ==============================================================================
# 2. VIEW: CARREGAMENTO DO FORMULÁRIO (Criação ou Edição)
# Retorna o fragmento HTML do formulário completo via HTMX para swap no painel.
# ==============================================================================
@direcao_required
def partner_quarto_formulario(request, quarto_id=None):
    """
    Exibe o formulário completo de criação ou edição de CategoriaQuarto.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    categoria = None
    if quarto_id:
        categoria = get_object_or_404(CategoriaQuarto, id=quarto_id, pousada=pousada_ativa)
        
    # Listas auxiliares fornecidas pelo Naviê
    tags_disponiveis = ["Família", "Casal", "Romântico", "Serra", "Trabalho Remoto", "Pet Friendly", "Silencioso", "Café da Manhã"]
    comodidades_disponiveis = ["Ar Condicionado", "Wi-Fi de Alta Velocidade", "Copa Completa", "Piscina Privativa", "Hidromassagem", "Frigobar Abastecido", "Café no Quarto"]
    
    # Split de tags e comodidades do objeto existente para checked states no form
    categoria_tags = [t.strip() for t in categoria.tags.split(',') if t.strip()] if categoria else []
    categoria_comodidades = [c.strip() for c in categoria.comodidades.split(',') if c.strip()] if categoria else []
    
    # Mapeamento de slots de mídias (0 a 9)
    imagens_slots = [None] * 10
    if categoria:
        for img in categoria.imagens.all():
            if 0 <= img.ordem < 10:
                imagens_slots[img.ordem] = img
                
    context = {
        **pousada_ctx,
        'categoria': categoria,
        'categoria_tags': categoria_tags,
        'categoria_comodidades': categoria_comodidades,
        'capacidades': [1, 2, 3, 4, 5, 6, 7, 8],
        'tags_disponiveis': tags_disponiveis,
        'comodidades_disponiveis': comodidades_disponiveis,
        'imagens_slots': imagens_slots,
        'slot_range': range(10)
    }
    
    return render(request, 'sistema/quartos/partials/quarto_formulario.html', context)


# ==============================================================================
# 3. VIEW: SALVAR / ATUALIZAR CATEGORIA & UNIDADES FÍSICAS (HTMX)
# Grava a CategoriaQuarto, faz upload de fotos, e sincroniza os Quartos físicos.
# ==============================================================================
@direcao_required
@require_POST
def partner_quarto_salvar(request):
    """
    Salva ou atualiza a CategoriaQuarto ativa na Pousada.
    Sincroniza automaticamente a grade física de Quartos (Unidades).
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    if not pousada_ativa:
        return HttpResponse("Nenhuma pousada selecionada.", status=400)
        
    quarto_id = request.POST.get('quarto_id')
    
    if quarto_id:
        categoria = get_object_or_404(CategoriaQuarto, id=quarto_id, pousada=pousada_ativa)
    else:
        categoria = CategoriaQuarto(pousada=pousada_ativa)
        
    categoria.nome = request.POST.get('nome', '').strip()
    categoria.descricao = request.POST.get('descricao', '').strip()
    
    # Preço base monetário
    preco_raw = request.POST.get('preco', '0').replace(',', '.')
    try:
        categoria.preco_base = float(preco_raw)
    except ValueError:
        categoria.preco_base = 0.00
        
    categoria.video_url = request.POST.get('video_url', '').strip() or None
    
    # Tour de vídeo local (Upload)
    if request.POST.get('remover_video') == 'true':
        categoria.video_arquivo = None
    elif 'video_arquivo' in request.FILES:
        vid_file = request.FILES['video_arquivo']
        if vid_file.size <= 30 * 1024 * 1024:  # Limite máximo de 30MB
            categoria.video_arquivo = vid_file
    
    # Capacidade máxima
    try:
        categoria.capacidade_adultos = int(request.POST.get('capacidade_pessoas', '2'))
    except ValueError:
        categoria.capacidade_adultos = 2
        
    # Junta as tags e comodidades selecionadas em formato CSV
    tags_selecionadas = request.POST.getlist('tags')
    comodidades_selecionadas = request.POST.getlist('comodidades')
    
    categoria.tags = ",".join(tags_selecionadas)
    categoria.comodidades = ",".join(comodidades_selecionadas)
    
    # Descontos multidias
    categoria.tem_desconto_multidias = request.POST.get('tem_desconto_multidias') == 'true'
    try:
        categoria.dias_minimos_desconto = int(request.POST.get('dias_minimos_desconto', '3'))
    except ValueError:
        categoria.dias_minimos_desconto = 3
        
    desc_raw = request.POST.get('percentual_desconto', '0').replace(',', '.')
    try:
        categoria.percentual_desconto = float(desc_raw)
    except ValueError:
        categoria.percentual_desconto = 0.00
        
    # SEO e Assistentes de IA
    categoria.seo_titulo = request.POST.get('seo_titulo', '').strip() or None
    categoria.seo_descricao = request.POST.get('seo_descricao', '').strip() or None
    
    categoria.save()
    
    # =========================================================================
    # SINCRONIZAÇÃO INTELIGENTE DE QUARTOS FÍSICOS (UNIDADES)
    # =========================================================================
    unidades_ids = request.POST.getlist('unidades_ids')
    unidades_identificadores = request.POST.getlist('unidades_identificadores')
    
    submitted_pairs = []
    for uid, ident in zip(unidades_ids, unidades_identificadores):
        ident = ident.strip()
        if ident:
            submitted_pairs.append((uid, ident))
            
    if not submitted_pairs:
        # Se o usuário não incluiu nenhuma, cria um quarto número 101 por padrão
        submitted_pairs.append(('new', '101'))
        
    # Mapeia os quartos físicos existentes vinculados a esta categoria nesta pousada
    existing_rooms = {str(r.id): r for r in Quarto.objects.filter(categoria=categoria, pousada=pousada_ativa)}
    submitted_ids = set()
    
    for uid, ident in submitted_pairs:
        if uid in existing_rooms:
            # Atualiza o identificador/número do quarto
            room = existing_rooms[uid]
            room.numero = ident
            room.save()
            submitted_ids.add(uid)
        else:
            # Cria um novo quarto físico
            new_room = Quarto.objects.create(
                pousada=pousada_ativa,
                categoria=categoria,
                numero=ident,
                status='LIVRE',
                capacidade_maxima=categoria.capacidade_adultos
            )
            submitted_ids.add(str(new_room.id))
            
    # Remove fisicamente os quartos que o usuário excluiu da grade de unidades no formulário
    for uid, room in existing_rooms.items():
        if uid not in submitted_ids:
            try:
                room.delete()
            except Exception:
                # Caso o quarto já tenha reservas vinculadas, apenas muda para manutenção para tirá-lo de circulação
                room.status = 'MANUTENCAO'
                room.save()
                
    # =========================================================================
    # UP DE IMAGENS DO QUARTO POR SLOT (0 a 9)
    # =========================================================================
    for i in range(10):
        file_key = f'imagem_{i}'
        if file_key in request.FILES:
            img_file = request.FILES[file_key]
            # Remove a imagem antiga que ocupava este slot (se houver)
            QuartoImagem.objects.filter(categoria=categoria, ordem=i).delete()
            # Cria a nova imagem vinculada ao slot i
            QuartoImagem.objects.create(
                categoria=categoria,
                url_imagem=img_file,
                ordem=i
            )
        
    messages.success(request, f"Acomodação '{categoria.nome}' salva com sucesso!")
    
    # Atualiza as categorias da pousada ativa para repopular o grid
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True).prefetch_related('imagens', 'quartos')
    context = {
        **pousada_ctx,
        'categorias': categorias
    }
    
    return render(request, 'sistema/quartos/partials/quarto_grid.html', context)


# ==============================================================================
# 4. VIEW: DELETAR / EXCLUIR CATEGORIA DE QUARTO (HTMX)
# ==============================================================================
@direcao_required
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar(request, quarto_id):
    """
    Realiza a exclusão lógica (soft delete) da CategoriaQuarto com verificação de senha.
    Todos os registros de reservas e quartos físicos são mantidos intactos no banco.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    # Verifica a senha de confirmação do usuário logado
    senha = request.POST.get('password', '').strip()
    if not senha or not request.user.check_password(senha):
        return HttpResponse("Senha de confirmação incorreta. A exclusão foi abortada.", status=400)
        
    categoria = get_object_or_404(CategoriaQuarto, id=quarto_id, pousada=pousada_ativa)
    nome_categoria = categoria.nome
    
    # Soft delete: marca como inativo para preservar FKs de quartos e reservas existentes
    categoria.ativo = False
    categoria.save()
    
    messages.success(request, f"Acomodação '{nome_categoria}' excluída com sucesso!")
    
    # Repopula o grid de quartos ativos
    categorias = CategoriaQuarto.objects.filter(pousada=pousada_ativa, ativo=True).prefetch_related('imagens', 'quartos')
    context = {
        **pousada_ctx,
        'categorias': categorias
    }
    
    return render(request, 'sistema/quartos/partials/quarto_grid.html', context)


# ==============================================================================
# 5. VIEW: EXCLUIR IMAGEM DA GALERIA (HTMX)
# ==============================================================================
@direcao_required
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar_imagem(request, imagem_id):
    """
    Exclui uma imagem específica da galeria e retorna vazio (200 OK) via HTMX
    para removê-la da tela instantaneamente sem reload.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_ativa = pousada_ctx['active_pousada']
    
    img = get_object_or_404(QuartoImagem, id=imagem_id, categoria__pousada=pousada_ativa)
    img.delete()
    
    return HttpResponse("", status=200)
