from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Voucher

@login_required(login_url='hoteis:partner_login')
def validar_voucher_api(request):
    """
    API universal de validação de QR codes da plataforma Naviê Vibe.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return JsonResponse({'success': False, 'error': 'Acesso restrito a contas corporativas parceiras.'}, status=403)
        
    # Obtém o hotel e a empresa dona do hotel logado
    hotel = request.user.perfil_parceiro.hotel
    empresa_logada = hotel.empresa
    
    payload = request.GET.get('payload', '').strip()
    if not payload:
        return JsonResponse({'success': False, 'error': 'Conteúdo do QR Code vazio.'}, status=400)
        
    # Tenta buscar o voucher pelo UUID (id) ou código_seguro correspondente
    import re
    uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', payload.lower())
    if not uuid_match:
        return JsonResponse({'success': False, 'error': 'QR Code com assinatura ou formato inválido.'}, status=400)
        
    voucher_id = uuid_match.group(1)
    
    try:
        voucher = Voucher.objects.get(id=voucher_id)
    except Voucher.DoesNotExist:
        # Tenta buscar por object_id (UUID da reserva vindo de QR codes antigos ou diretos)
        try:
            voucher = Voucher.objects.get(object_id=voucher_id)
        except Voucher.DoesNotExist:
            # Tenta verificar se é uma Reserva real e gerar o Voucher on-the-fly para retrocompatibilidade!
            from hoteis.models import Reserva
            try:
                reserva = Reserva.objects.get(id=voucher_id, unidade__quarto__hotel=hotel)
                # Criar o Voucher retroativo
                cpf_limpo = ''.join(c for c in (reserva.hospede_cpf or "") if c.isdigit())
                cpf_ocultado = f"***.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-**" if len(cpf_limpo) == 11 else "USER-UNKNOWN"
                
                # Se a reserva já estiver hospedada/concluída, marcar o voucher como utilizado
                utilizado = reserva.status in ['hospedado', 'concluido']
                utilizado_em = reserva.checkin_realizado_em if utilizado else None
                
                voucher = Voucher.objects.create(
                    empresa=reserva.unidade.quarto.hotel.empresa,
                    tipo='hospedagem',
                    object_id=str(reserva.id),
                    codigo_seguro=f"VALIDA-RESERVA-{reserva.id}-{reserva.unidade.identificador}-{cpf_ocultado}",
                    titulo_exibicao=f"{reserva.unidade.identificador} ({reserva.unidade.quarto.nome})",
                    subtitulo_exibicao=reserva.unidade.quarto.hotel.nome,
                    nome_beneficiario=reserva.hospede_nome or "Hóspede",
                    documento_beneficiario=cpf_ocultado,
                    utilizado=utilizado,
                    utilizado_em=utilizado_em,
                    detalhes_json={
                        'checkin': reserva.data_checkin.strftime('%d/%m/%Y'),
                        'checkout': reserva.data_checkout.strftime('%d/%m/%Y'),
                        'noites': reserva.noites,
                        'reserva_id': str(reserva.id)
                    }
                )
            except Reserva.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Voucher inexistente ou cancelado.'}, status=404)
        
    # 🚨 BLINDAGEM DE SEGURANÇA MULTI-TENANT 🚨
    # Impede que o atendente do Hotel A escaneie e veja dados de um voucher do Hotel B ou de um Show de outra produtora
    if voucher.empresa != empresa_logada:
        return JsonResponse({
            'success': False, 
            'error': 'Acesso Negado: Este voucher pertence a outro estabelecimento e não pode ser lido por este painel.'
        }, status=403)
        
    if voucher.utilizado:
        return JsonResponse({
            'success': False, 
            'error': f'Voucher já utilizado anteriormente em {voucher.utilizado_em.strftime("%d/%m/%Y às %H:%M")}.'
        }, status=400)
        
    # Retorna o payload limpo e seguro contendo somente os dados públicos de visualização
    return JsonResponse({
        'success': True,
        'voucher_id': str(voucher.id),
        'tipo': voucher.tipo,
        'tipo_display': voucher.get_tipo_display(),
        'titulo': voucher.titulo_exibicao,
        'subtitulo': voucher.subtitulo_exibicao,
        'beneficiario': voucher.nome_beneficiario,
        'documento': voucher.documento_beneficiario,
        'detalhes': voucher.detalhes_json,
        'object_id': voucher.object_id,
    })

@login_required(login_url='hoteis:partner_login')
@require_POST
def processar_entrada_voucher(request, voucher_id):
    """
    API universal para consumir/utilizar o voucher e realizar a ação de entrada correspondente.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    empresa_logada = hotel.empresa
    
    voucher = get_object_or_404(Voucher, id=voucher_id, empresa=empresa_logada)
    
    if voucher.utilizado:
        return JsonResponse({'success': False, 'error': 'Este voucher já foi consumido.'}, status=400)
        
    # Consumir o voucher
    voucher.utilizado = True
    voucher.utilizado_em = timezone.now()
    voucher.utilizado_por = request.user
    voucher.save()
    
    # Disparar ação lógica dependendo do tipo do voucher
    if voucher.tipo == 'hospedagem':
        from hoteis.models import Reserva, ReservaLog
        try:
            reserva = Reserva.objects.get(id=voucher.object_id)
            reserva.status = 'hospedado'
            reserva.checkin_realizado_em = timezone.now()
            reserva.save()
            
            # Registrar auditoria
            ReservaLog.objects.create(
                reserva=reserva,
                usuario=request.user,
                acao='checkin',
                detalhes=f"Check-in automático via Scanner de Portaria QR Code."
            )
        except Reserva.DoesNotExist:
            pass
            
    # Futuras integrações para outras verticais:
    # elif voucher.tipo == 'show':
    #     ... (marcar ingresso do show como utilizado)
    # elif voucher.tipo == 'cinema':
    #     ... (marcar cadeira de cinema como ocupada na portaria)
        
    return JsonResponse({'success': True, 'message': 'Voucher validado e consumido com sucesso!'})
