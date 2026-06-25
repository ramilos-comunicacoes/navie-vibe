from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from datetime import datetime
from sistema.models import CategoriaQuarto, Quarto, Reserva, HospedeReserva, VeiculoReserva, BloqueioQuarto
from sas.financeiro import calcular_taxas_reserva

def verifica_disponibilidade_quarto(quarto, data_checkin, data_checkout):
    """
    Verifica se há bloqueios ou reservas ativas conflitantes para o quarto físico.
    """
    bloqueios = BloqueioQuarto.objects.filter(
        quarto=quarto,
        data_inicio__lt=data_checkout,
        data_fim__gt=data_checkin
    ).exists()
    if bloqueios:
        return False
        
    reservas_conflito = Reserva.objects.filter(
        quarto=quarto,
        data_checkin__lt=data_checkout,
        data_checkout__gt=data_checkin
    ).exclude(status='CANCELADA').exists()
    if reservas_conflito:
        return False
        
    return True

@require_POST
def carrinho_adicionar(request, categoria_id):
    """
    Adiciona a acomodação selecionada (CategoriaQuarto) e o período de estadia ao carrinho.
    """
    categoria = get_object_or_404(CategoriaQuarto, id=categoria_id)
    checkin_str = request.POST.get('checkin')
    checkout_str = request.POST.get('checkout')
    
    if not checkin_str or not checkout_str:
        return JsonResponse({'success': False, 'error': 'Informe as datas de check-in e check-out.'}, status=400)
        
    capacidade_maxima = categoria.capacidade_adultos + categoria.capacidade_criancas
    
    request.session['carrinho'] = {
        'quarto_id': categoria.id,
        'checkin': checkin_str,
        'checkout': checkout_str,
        'quantidade_hospedes': capacidade_maxima,
        'hospedes': [{} for _ in range(capacidade_maxima)],
        'veiculo': {'placa': '', 'modelo': '', 'cor': ''}
    }
    request.session.modified = True
    return JsonResponse({'success': True})

def carrinho_remover(request):
    """
    Esvazia completamente o carrinho.
    """
    if 'carrinho' in request.session:
        del request.session['carrinho']
        request.session.modified = True
    messages.success(request, 'Reserva cancelada no carrinho.')
    return redirect('website:home')

@require_POST
def carrinho_definir_hospedes(request):
    """
    Atualiza a quantidade de hóspedes ativos no carrinho da sessão.
    """
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Carrinho vazio.'}, status=400)
        
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Quantidade inválida.'}, status=400)
        
    categoria = get_object_or_404(CategoriaQuarto, id=carrinho_data.get('quarto_id'))
    capacidade_maxima = categoria.capacidade_adultos + categoria.capacidade_criancas
    
    if quantidade < 1 or quantidade > capacidade_maxima:
        return JsonResponse({'success': False, 'error': f'Quantidade fora do limite (1-{capacidade_maxima}).'}, status=400)
        
    hospedes = carrinho_data.get('hospedes', [{}])
    while len(hospedes) < quantidade:
        hospedes.append({})
    while len(hospedes) > quantidade:
        hospedes.pop()
        
    carrinho_data['quantidade_hospedes'] = quantidade
    carrinho_data['hospedes'] = hospedes
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')
    return JsonResponse({'success': True})

@require_POST
def carrinho_salvar_fnrh(request):
    """
    Salva temporariamente na sessão os dados de FNRH digitados para um hóspede.
    """
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Carrinho vazio.'}, status=400)
        
    try:
        idx = int(request.GET.get('idx', 0))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Índice inválido.'}, status=400)
        
    hospedes = carrinho_data.get('hospedes', [])
    if idx < 0 or idx >= len(hospedes):
        return JsonResponse({'success': False, 'error': 'Hóspede não encontrado.'}, status=400)
        
    hospedes[idx] = {
        'nome': request.POST.get('hospede_nome', '').strip(),
        'cpf': request.POST.get('hospede_cpf', '').strip(),
        'email': request.POST.get('hospede_email', '').strip(),
        'telefone': request.POST.get('hospede_telefone', '').strip(),
        'rg': request.POST.get('hospede_rg', '').strip(),
        'nacionalidade': request.POST.get('hospede_nacionalidade', 'Brasileira').strip(),
        'profissao': request.POST.get('hospede_profissao', '').strip(),
        'cep': request.POST.get('hospede_cep', '').strip(),
        'endereco': request.POST.get('hospede_endereco', '').strip(),
    }
    
    # Se for o Titular (idx == 0), salva dados adicionais do veículo
    if idx == 0:
        carrinho_data['veiculo'] = {
            'placa': request.POST.get('veiculo_placa', '').strip().upper(),
            'modelo': request.POST.get('veiculo_modelo', '').strip(),
            'cor': request.POST.get('veiculo_cor', '').strip(),
        }
        
    carrinho_data['hospedes'] = hospedes
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    return JsonResponse({'success': True})

@login_required(login_url='sistema:login')
def checkout_processar(request):
    """
    Valida as fichas FNRH completas, aloca uma cabana/quarto físico livre,
    calcula os repasses finais e persiste a reserva no banco de dados.
    """
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        messages.error(request, 'Seu carrinho está vazio.')
        return redirect('website:home')
        
    quantidade_hospedes = carrinho_data.get('quantidade_hospedes', 1)
    hospedes = carrinho_data.get('hospedes', [{}])
    
    # Validação rigorosa no backend
    required_titular = ['nome', 'cpf', 'email', 'telefone', 'cep', 'endereco']
    required_acompanhante = ['nome', 'cpf']
    
    for idx, h in enumerate(hospedes):
        req_fields = required_titular if idx == 0 else required_acompanhante
        # Acompanhantes em branco são ignorados (não preenchidos);
        # Mas se houver qualquer dado preenchido neles, valida os obrigatórios
        h_tem_dados = any(h.get(f) for f in required_titular + ['rg', 'nacionalidade', 'profissao'])
        
        if idx == 0 or h_tem_dados:
            if not all(h.get(f) for f in req_fields):
                messages.error(request, f'Preencha todos os dados obrigatórios do hóspede {idx+1}.')
                return redirect('website:home')
                
    categoria = get_object_or_404(CategoriaQuarto, id=carrinho_data['quarto_id'])
    
    try:
        checkin = datetime.strptime(carrinho_data['checkin'], '%Y-%m-%d').date()
        checkout = datetime.strptime(carrinho_data['checkout'], '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Período de estadia inválido.')
        return redirect('website:home')
        
    # Alocação física de quarto livre
    quarto_alocado = None
    for q in categoria.quartos.all():
        if verifica_disponibilidade_quarto(q, checkin, checkout):
            quarto_alocado = q
            break
            
    if not quarto_alocado:
        messages.error(request, 'Lamentamos, mas não há acomodações físicas disponíveis no período escolhido.')
        return redirect('website:home')
        
    noites = (checkout - checkin).days or 1
    
    # Cálculo de taxas
    fin = calcular_taxas_reserva(categoria, noites)
    
    # Salva Reserva
    titular_fnrh = hospedes[0]
    reserva = Reserva.objects.create(
        quarto=quarto_alocado,
        usuario=request.user,
        data_checkin=checkin,
        data_checkout=checkout,
        status='CONFIRMADA',
        subtotal=fin['subtotal'],
        taxas=fin['taxa_servico'],
        valor_total=fin['total_cliente'],
        taxa_servico_plataforma=fin['taxa_servico'],
        taxa_gateway=fin['taxa_gateway'],
        repasse_parceiro=fin['repasse_parceiro'],
        ganho_liquido_plataforma=fin['ganho_liquido'],
        hospede_nome=titular_fnrh['nome'],
        hospede_cpf=titular_fnrh['cpf'],
        hospede_email=titular_fnrh['email'],
        hospede_telefone=titular_fnrh['telefone'],
        hospede_rg=titular_fnrh.get('rg', ''),
        hospede_nacionalidade=titular_fnrh.get('nacionalidade', 'Brasileira'),
        hospede_profissao=titular_fnrh.get('profissao', ''),
        hospede_endereco=f"{titular_fnrh['endereco']} (CEP: {titular_fnrh['cep']})",
        quantidade_hospedes=quantidade_hospedes,
        canal_origem='WEBSITE_DIRETO'
    )
    
    # Salva Fichas dos Acompanhantes
    for idx, h in enumerate(hospedes):
        h_tem_dados = any(h.get(f) for f in required_titular + ['rg', 'nacionalidade', 'profissao'])
        if idx == 0 or h_tem_dados:
            endereco_completo = h.get('endereco', '')
            if h.get('cep'):
                endereco_completo = f"{endereco_completo} (CEP: {h['cep']})".strip()
                
            HospedeReserva.objects.create(
                reserva=reserva,
                ordem=idx + 1,
                nome=h['nome'],
                cpf=h['cpf'],
                email=h.get('email', ''),
                telefone=h.get('telefone', ''),
                rg=h.get('rg', ''),
                nacionalidade=h.get('nacionalidade', 'Brasileira'),
                profissao=h.get('profissao', ''),
                endereco=endereco_completo
            )
            
    # Salva Veículo
    veiculo_data = carrinho_data.get('veiculo', {})
    if veiculo_data and veiculo_data.get('placa'):
        VeiculoReserva.objects.create(
            reserva=reserva,
            placa=veiculo_data['placa'].upper(),
            modelo=veiculo_data.get('modelo', ''),
            cor=veiculo_data.get('cor', '')
        )
        
    # Esvazia o carrinho na sessão
    if 'carrinho' in request.session:
        del request.session['carrinho']
        request.session.modified = True
        
    return redirect('website:checkout_sucesso', reserva_id=reserva.id)

@login_required(login_url='sistema:login')
def checkout_sucesso(request, reserva_id):
    """
    Exibe a tela de confirmação e resumo da reserva realizada.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    return render(request, 'website/checkout_sucesso.html', {
        'reserva': reserva,
        'pousada': reserva.quarto.pousada
    })
