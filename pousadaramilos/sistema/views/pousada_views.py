from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from sistema.views.dashboard_views import obter_contexto_pousada
from sistema.models import Pousada, SiteConfig
from sistema.decorators import direcao_required

# ==============================================================================
# VIEW: LISTAGEM DE POUSADAS (CRUD Pousadas)
# Permite ao administrador gerenciar as 3 pousadas da rede Ramiros.
# ==============================================================================
@direcao_required
def pousada_list(request):
    """
    Exibe a listagem de pousadas cadastradas no sistema.
    Atualmente operando como visualizador inicial integrado ao template global.
    """
    pousada_ctx = obter_contexto_pousada(request)
    tab = request.GET.get('tab', 'pousadas')
    
    # Administradores têm acesso a gerenciar todas as pousadas
    todas_pousadas = Pousada.objects.all()
    
    config = SiteConfig.objects.first()
    if not config:
        config = SiteConfig.objects.create()
    
    context = {
        **pousada_ctx,
        'todas_pousadas': todas_pousadas,
        'config': config,
        'active_tab': tab,
    }
    
    return render(request, 'sistema/pousada_list.html', context)


# ==============================================================================
# VIEW: CARREGAMENTO DO FORMULÁRIO (Modal Configuração)
# Retorna o fragmento HTML do modal completo via HTMX para swap no painel.
# ==============================================================================
@direcao_required
def partner_pousada_formulario(request):
    """
    Exibe o formulário de cadastro ou edição de Pousada com o seletor Leaflet.js.
    """
    pousada_ctx = obter_contexto_pousada(request)
    pousada_id = request.GET.get('pousada_id')
    
    pousada = None
    if pousada_id:
        # Administradores gerenciam qualquer pousada
        pousada = get_object_or_404(Pousada, id=pousada_id)
        
    context = {
        **pousada_ctx,
        'pousada': pousada,
    }
    
    return render(request, 'sistema/partials/modal_pousada_formulario.html', context)


# ==============================================================================
# VIEW: SALVAR / ATUALIZAR POUSADA (POST)
# Grava a Pousada e redireciona o cliente.
# ==============================================================================
@direcao_required
@require_POST
def partner_pousada_salvar(request):
    """
    Salva ou atualiza os dados da Pousada.
    """
    pousada_id = request.POST.get('pousada_id')
    
    if pousada_id:
        pousada = get_object_or_404(Pousada, id=pousada_id)
    else:
        pousada = Pousada()
        
    pousada.nome = request.POST.get('nome', '').strip()
    pousada.endereco = request.POST.get('endereco', '').strip()
    pousada.telefone_whatsapp = request.POST.get('telefone_whatsapp', '').strip()
    pousada.cnpj = request.POST.get('cnpj', '').strip() or None
    pousada.cor_primaria_hex = request.POST.get('cor_primaria_hex', '#2563eb').strip()
    
    # Coordenadas do mapa Leaflet
    lat_raw = request.POST.get('mapa_latitude', '').replace(',', '.')
    lng_raw = request.POST.get('mapa_longitude', '').replace(',', '.')
    
    try:
        pousada.mapa_latitude = float(lat_raw) if lat_raw else None
    except ValueError:
        pousada.mapa_latitude = None
        
    try:
        pousada.mapa_longitude = float(lng_raw) if lng_raw else None
    except ValueError:
        pousada.mapa_longitude = None
        
    # Salvar Imagem de Destaque se enviada
    if 'imagem_destaque' in request.FILES:
        pousada.imagem_destaque = request.FILES['imagem_destaque']
        
    if request.POST.get('limpar_imagem_destaque') == 'true':
        if pousada.imagem_destaque:
            pousada.imagem_destaque.delete(save=False)
        pousada.imagem_destaque = None

    pousada.save()
    
    messages.success(request, f"Pousada '{pousada.nome}' configurada com sucesso!")
    
    # Retorna redirecionamento compatível com HTMX
    if request.headers.get('HX-Request'):
        response = HttpResponse()
        response['HX-Redirect'] = reverse('sistema:pousada_list')
        return response
        
    return HttpResponseRedirect(reverse('sistema:pousada_list'))


# ==============================================================================
# VIEW: SALVAR CONFIGURAÇÃO DO SITE PÚBLICO (POST)
# ==============================================================================
@direcao_required
@require_POST
def partner_site_salvar(request):
    """
    Salva as configurações de exibição da página pública.
    """
    config = SiteConfig.objects.first()
    if not config:
        config = SiteConfig()

    config.hero_titulo = request.POST.get('hero_titulo', '').strip()
    config.hero_subtitulo = request.POST.get('hero_subtitulo', '').strip()
    config.hero_video_url = request.POST.get('hero_video_url', '').strip() or None

    # Vídeo local upload
    if 'hero_video_arquivo' in request.FILES:
        config.hero_video_arquivo = request.FILES['hero_video_arquivo']

    if request.POST.get('limpar_video_arquivo') == 'true':
        if config.hero_video_arquivo:
            config.hero_video_arquivo.delete(save=False)
        config.hero_video_arquivo = None

    config.save()
    messages.success(request, "Configurações da página pública salvas com sucesso!")
    return HttpResponseRedirect(reverse('sistema:pousada_list') + '?tab=site')
