from sistema.models import CategoriaQuarto
from datetime import datetime
from sas.financeiro import calcular_taxas_reserva

def carrinho(request):
    """
    Context processor para gerenciar o estado global do carrinho público na sessão.
    Garante sincronização reativa de dados, cálculos financeiros e validação de FNRH.
    """
    carrinho_data = request.session.get('carrinho', None)
    if not carrinho_data:
        return {'carrinho': None, 'carrinho_qtd': 0}
        
    try:
        quarto_id = carrinho_data.get('quarto_id')
        # quarto no B2C é a Categoria de Acomodação (CategoriaQuarto)
        quarto = CategoriaQuarto.objects.get(id=quarto_id)
        
        checkin_str = carrinho_data.get('checkin')
        checkout_str = carrinho_data.get('checkout')
        
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        
        noites = (checkout - checkin).days
        if noites <= 0:
            noites = 1
            
        # Lógica Financeira (sas/financeiro.py)
        fin = calcular_taxas_reserva(quarto, noites)
        subtotal = fin['subtotal']
        taxas = fin['taxa_servico']
        total = fin['total_cliente']
        
        # Capacidade máxima do quarto
        capacidade_maxima = quarto.capacidade_adultos + quarto.capacidade_criancas
        quantidade_hospedes = carrinho_data.get('quantidade_hospedes', capacidade_maxima)
        
        # Redimensiona lista de hóspedes
        hospedes = carrinho_data.get('hospedes', [{}])
        while len(hospedes) < quantidade_hospedes:
            hospedes.append({})
        while len(hospedes) > quantidade_hospedes:
            hospedes.pop()
            
        # Sincroniza sessão
        if carrinho_data.get('quantidade_hospedes') != quantidade_hospedes or len(carrinho_data.get('hospedes', [])) != quantidade_hospedes:
            carrinho_data['quantidade_hospedes'] = quantidade_hospedes
            carrinho_data['hospedes'] = hospedes
            request.session['carrinho'] = carrinho_data
            request.session.modified = True
            
        # Autofill do titular logado (hóspede 0)
        if request.user.is_authenticated and not hospedes[0].get('nome'):
            try:
                perfil = getattr(request.user, 'perfil', None)
                hospedes[0] = {
                    'nome': request.user.nome_completo or request.user.get_full_name() or request.user.username,
                    'cpf': getattr(perfil, 'cpf', '') if perfil else '',
                    'email': request.user.email,
                    'telefone': getattr(perfil, 'telefone', '') if perfil else '',
                    'cep': getattr(perfil, 'cep', '') if perfil else '',
                    'endereco': f"{getattr(perfil, 'endereco', '') or ''}".strip() if perfil else '',
                    'rg': '',
                    'nacionalidade': 'Brasileira',
                    'profissao': ''
                }
                carrinho_data['hospedes'] = hospedes
                request.session['carrinho'] = carrinho_data
                request.session.modified = True
            except Exception:
                pass
                
        # Validação homogênea de FNRH
        hospedes_validados = []
        todos_hospedes_completos = True
        required_fields = ['nome', 'cpf', 'email', 'telefone', 'cep', 'endereco']
        required_acompanhante = ['nome', 'cpf'] # Acompanhantes precisam de menos dados no checklist
        
        for idx, h in enumerate(hospedes):
            h_tem_dados = any(h.get(f) for f in required_fields + ['rg', 'nacionalidade', 'profissao'])
            
            if idx == 0:
                h_completo = all(h.get(f) for f in required_fields)
                if not h_completo:
                    todos_hospedes_completos = False
            else:
                if h_tem_dados:
                    h_completo = all(h.get(f) for f in required_acompanhante)
                    if not h_completo:
                        todos_hospedes_completos = False
                else:
                    h_completo = True # Acompanhante não preenchido é aceitável (opcional)
                    
            h_info = h.copy()
            h_info['completo'] = h_completo
            h_info['index'] = idx
            h_info['ordem'] = idx + 1
            hospedes_validados.append(h_info)
            
        carrinho_info = {
            'quarto': quarto,
            'checkin': checkin,
            'checkout': checkout,
            'checkin_formatted': checkin.strftime('%Y-%m-%d'),
            'checkout_formatted': checkout.strftime('%Y-%m-%d'),
            'checkin_show': checkin.strftime('%d/%m/%Y'),
            'checkout_show': checkout.strftime('%d/%m/%Y'),
            'noites': noites,
            'subtotal': subtotal,
            'taxas': taxas,
            'total': total,
            'quantidade_hospedes': quantidade_hospedes,
            'capacidade_maxima': capacidade_maxima,
            'hospedes': hospedes_validados,
            'todos_hospedes_completos': todos_hospedes_completos,
            'veiculo': carrinho_data.get('veiculo', {'placa': '', 'modelo': '', 'cor': ''}),
            'fnrh': hospedes_validados[0] if hospedes_validados else {},
            'fnrh_completo': todos_hospedes_completos,
        }
        return {'carrinho': carrinho_info, 'carrinho_qtd': 1}
        
    except Exception as e:
        # Se houver erro de inconsistência na sessão, limpa e continua
        request.session['carrinho'] = None
        request.session.modified = True
        return {'carrinho': None, 'carrinho_qtd': 0}
