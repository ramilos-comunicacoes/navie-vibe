import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import UserInteraction
from .analytics import limpar_historico_antigo

@csrf_exempt
@require_POST
def api_registrar_interacao(request):
    """
    Recebe requisições assíncronas do frontend (beacons) para registrar dados de visualizações
    e o tempo de permanência ativa nas páginas da plataforma.
    """
    # 1. Recuperar o tracker_id (prioridade para cookies, depois cabeçalhos)
    tracker_id = request.COOKIES.get('navie_tracker_id') or request.headers.get('X-Tracker-ID')
    
    # 2. Processar o payload (pode ser JSON bruto ou POST urlencoded do beacon)
    data = {}
    content_type = request.content_type or ''
    
    if 'application/json' in content_type:
        try:
            data = json.loads(request.body)
        except Exception:
            pass
    else:
        # Tentar ler o corpo como JSON mesmo sem cabeçalho específico (muito comum em beacons)
        try:
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
            
        # Fallback para formulário post convencional se o JSON falhar
        if not data:
            data = {k: v for k, v in request.POST.items()}
            
    if not data:
        return JsonResponse({'success': False, 'error': 'Payload vazio'}, status=400)

    url = data.get('url', '')
    path = data.get('path', '')
    time_spent = int(data.get('time_spent', 0))
    interaction_type = data.get('interaction_type', 'page_view')
    category = data.get('category')
    item_id = data.get('item_id')
    parent_id = data.get('parent_id')
    metadata = data.get('metadata', {})
    
    # Se não foi pego via cookies/headers, tentar extrair do próprio payload
    if not tracker_id:
        tracker_id = data.get('tracker_id')
        
    if not tracker_id:
        return JsonResponse({'success': False, 'error': 'tracker_id não fornecido'}, status=400)
        
    # Evita gravar interações do tipo page_view com 0 segundos (como quando abrem e fecham a aba imediatamente)
    # Mas permite registrar interações pontuais instantâneas como 'cart_add' ou 'checkout_start' com tempo 0
    if time_spent == 0 and interaction_type in ['page_view', 'item_detail']:
        return JsonResponse({'success': True, 'ignored': True, 'message': 'Tempo gasto igual a zero. Registro ignorado.'})

    usuario = request.user if request.user.is_authenticated else None

    # 3. Criar registro de interação
    interaction = UserInteraction.objects.create(
        tracker_id=tracker_id,
        usuario=usuario,
        interaction_type=interaction_type,
        category=category,
        item_id=str(item_id) if item_id else None,
        parent_id=str(parent_id) if parent_id else None,
        url=url,
        path=path,
        time_spent=time_spent,
        metadata=metadata
    )

    # 4. Controle de limpeza do histórico (mantendo 30 dias ativos)
    # Para otimização extrema, a limpeza roda apenas uma vez por dia ativo por sessão
    hoje_str = timezone.now().date().isoformat()
    ultimo_cleanup = request.session.get('navie_analytics_last_cleanup')
    
    if ultimo_cleanup != hoje_str:
        try:
            limpar_historico_antigo(tracker_id, usuario)
            request.session['navie_analytics_last_cleanup'] = hoje_str
            request.session.modified = True
        except Exception:
            # Protege a gravação em caso de qualquer falha menor na exclusão
            pass

    return JsonResponse({
        'success': True,
        'interaction_id': interaction.id,
        'message': 'Interação gravada com sucesso.'
    })
