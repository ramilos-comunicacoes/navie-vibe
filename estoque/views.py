import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db import transaction
from datetime import date, datetime
from django.db.models import Sum, Q

from hoteis.models import Hotel, ProdutoConsumo
from financeiro.models import TransacaoFinanceira
from .models import CategoriaProduto, Fornecedor, Produto, Compra, DocumentoCompra, ItemCompra, MovimentoEstoque

# --- PRODUTOS ---

@login_required(login_url='hoteis:partner_login')
def criar_produto(request):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        unidade_medida = request.POST.get('unidade_medida', 'UN')
        finalidade = request.POST.get('finalidade', 'interno')
        preco_venda_str = request.POST.get('preco_venda', '').replace(',', '.').strip()
        estoque_minimo_str = request.POST.get('estoque_minimo', '0').replace(',', '.').strip()
        
        # Novas informações do item
        codigo_barras = request.POST.get('codigo_barras', '').strip() or None
        localizacao = request.POST.get('localizacao', '').strip() or None
        imagem = request.FILES.get('imagem')
        
        preco_venda = None
        if finalidade in ['venda', 'ambos'] and preco_venda_str:
            try:
                preco_venda = float(preco_venda_str)
            except ValueError:
                preco_venda = 0.00
                
        try:
            estoque_minimo = float(estoque_minimo_str)
        except ValueError:
            estoque_minimo = 0.00
            
        categoria = None
        if categoria_id:
            categoria = get_object_or_404(CategoriaProduto, id=categoria_id, hotel=hotel)
            
        with transaction.atomic():
            produto = Produto.objects.create(
                hotel=hotel,
                categoria=categoria,
                nome=nome,
                descricao=descricao,
                imagem=imagem,
                codigo_barras=codigo_barras,
                localizacao=localizacao,
                unidade_medida=unidade_medida,
                finalidade=finalidade,
                preco_venda=preco_venda,
                estoque_minimo=estoque_minimo,
                alerta_validade=True
            )
            
            # Sincronizar com ProdutoConsumo (Cardápio / Frigobar) se for para venda
            if finalidade in ['venda', 'ambos']:
                # Mapeia finalidade para tipo de ProdutoConsumo
                tipo_consumo = 'bebida'
                if categoria and 'comida' in categoria.nome.lower():
                    tipo_consumo = 'comida'
                elif categoria and 'serviço' in categoria.nome.lower():
                    tipo_consumo = 'servico'
                
                ProdutoConsumo.objects.create(
                    hotel=hotel,
                    estoque_produto=produto,
                    nome=produto.nome,
                    descricao=produto.descricao,
                    preco=preco_venda or 0.00,
                    tipo=tipo_consumo,
                    disponivel=True
                )
                
        messages.success(request, f"Item '{nome}' cadastrado com sucesso!")
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'estoque/partials/success_modal.html', {
                'titulo': 'Sucesso!',
                'mensagem': f"O item '{nome}' foi cadastrado com sucesso."
            })
        return redirect('hoteis:partner_dashboard')
        
    categorias = CategoriaProduto.objects.filter(hotel=hotel)
    unidades = Produto.UNIDADES_MEDIDA
    finalidades = Produto.FINALIDADES
    
    context = {
        'categorias': categorias,
        'unidades': unidades,
        'finalidades': finalidades,
    }
    return render(request, 'estoque/partials/modal_produto.html', context)

@login_required(login_url='hoteis:partner_login')
def editar_produto(request, produto_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    produto = get_object_or_404(Produto, id=produto_id, hotel=hotel)
    
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        unidade_medida = request.POST.get('unidade_medida', 'UN')
        finalidade = request.POST.get('finalidade', 'interno')
        preco_venda_str = request.POST.get('preco_venda', '').replace(',', '.').strip()
        estoque_minimo_str = request.POST.get('estoque_minimo', '0').replace(',', '.').strip()
        
        # Novas informações do item
        codigo_barras = request.POST.get('codigo_barras', '').strip() or None
        localizacao = request.POST.get('localizacao', '').strip() or None
        
        preco_venda = None
        if finalidade in ['venda', 'ambos'] and preco_venda_str:
            try:
                preco_venda = float(preco_venda_str)
            except ValueError:
                preco_venda = 0.00
                
        try:
            estoque_minimo = float(estoque_minimo_str)
        except ValueError:
            estoque_minimo = 0.00
            
        categoria = None
        if categoria_id:
            categoria = get_object_or_404(CategoriaProduto, id=categoria_id, hotel=hotel)
            
        with transaction.atomic():
            produto.categoria = categoria
            produto.nome = nome
            produto.descricao = descricao
            produto.unidade_medida = unidade_medida
            produto.finalidade = finalidade
            produto.preco_venda = preco_venda
            produto.estoque_minimo = estoque_minimo
            produto.codigo_barras = codigo_barras
            produto.localizacao = localizacao
            
            if 'imagem' in request.FILES:
                produto.imagem = request.FILES['imagem']
            elif request.POST.get('remover_imagem') == 'true':
                produto.imagem = None
                
            produto.save()
            
            # Sincronizar com ProdutoConsumo
            consumo_vinculados = ProdutoConsumo.objects.filter(estoque_produto=produto)
            if finalidade in ['venda', 'ambos']:
                tipo_consumo = 'bebida'
                if categoria and 'comida' in categoria.nome.lower():
                    tipo_consumo = 'comida'
                elif categoria and 'serviço' in categoria.nome.lower():
                    tipo_consumo = 'servico'
                
                if consumo_vinculados.exists():
                    consumo = consumo_vinculados.first()
                    consumo.nome = nome
                    consumo.descricao = descricao
                    consumo.preco = preco_venda or 0.00
                    consumo.tipo = tipo_consumo
                    consumo.disponivel = True
                    consumo.save()
                else:
                    ProdutoConsumo.objects.create(
                        hotel=hotel,
                        estoque_produto=produto,
                        nome=nome,
                        descricao=descricao,
                        preco=preco_venda or 0.00,
                        tipo=tipo_consumo,
                        disponivel=True
                    )
            else:
                # Desativa ou remove o consumo se não for mais para venda
                consumo_vinculados.update(disponivel=False)
                
        messages.success(request, f"Item '{nome}' atualizado!")
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'estoque/partials/success_modal.html', {
                'titulo': 'Salvo!',
                'mensagem': f"As alterações do item '{nome}' foram salvas."
            })
        return redirect('hoteis:partner_dashboard')
        
    categorias = CategoriaProduto.objects.filter(hotel=hotel)
    unidades = Produto.UNIDADES_MEDIDA
    finalidades = Produto.FINALIDADES
    
    context = {
        'produto': produto,
        'categorias': categorias,
        'unidades': unidades,
        'finalidades': finalidades,
    }
    return render(request, 'estoque/partials/modal_produto.html', context)

@login_required(login_url='hoteis:partner_login')
@require_POST
def excluir_produto(request, produto_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    produto = get_object_or_404(Produto, id=produto_id, hotel=hotel)
    
    with transaction.atomic():
        produto.ativo = False
        produto.save()
        # Desativa produto de consumo correspondente
        ProdutoConsumo.objects.filter(estoque_produto=produto).update(disponivel=False)
        
    messages.success(request, f"Produto '{produto.nome}' removido do catálogo!")
    return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))


# --- CATEGORIAS ---

@login_required(login_url='hoteis:partner_login')
def criar_categoria(request):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        icone = request.POST.get('icone', 'box').strip() or 'box'
        
        if nome:
            CategoriaProduto.objects.create(
                hotel=hotel,
                nome=nome,
                icone=icone
            )
            messages.success(request, f"Categoria '{nome}' criada!")
            
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'estoque/partials/success_modal.html', {
                'titulo': 'Sucesso!',
                'mensagem': f"A categoria '{nome}' foi criada com sucesso."
            })
        return redirect('hoteis:partner_dashboard')
        
    return render(request, 'estoque/partials/modal_categoria.html')


# --- FORNECEDORES ---

@login_required(login_url='hoteis:partner_login')
def criar_fornecedor(request):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        email = request.POST.get('email', '').strip()
        cnpj_cpf = request.POST.get('cnpj_cpf', '').strip()
        
        if nome:
            Fornecedor.objects.create(
                hotel=hotel,
                nome=nome,
                telefone=telefone or None,
                email=email or None,
                cnpj_cpf=cnpj_cpf or None
            )
            messages.success(request, f"Fornecedor '{nome}' cadastrado!")
            
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'estoque/partials/success_modal.html', {
                'titulo': 'Sucesso!',
                'mensagem': f"O fornecedor '{nome}' foi cadastrado com sucesso."
            })
        return redirect('hoteis:partner_dashboard')
        
    return render(request, 'estoque/partials/modal_fornecedor.html')


# --- COMPRAS ---

@login_required(login_url='hoteis:partner_login')
def criar_compra(request):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    fornecedores = Fornecedor.objects.filter(hotel=hotel, ativo=True)
    produtos = Produto.objects.filter(hotel=hotel, ativo=True)
    hoje = date.today().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        fornecedor_id = request.POST.get('fornecedor_id')
        data_compra_str = request.POST.get('data_compra')
        observacao = request.POST.get('observacao', '').strip()
        
        # Listas dinâmicas enviadas do formulário
        produto_ids = request.POST.getlist('item_produto_id')
        quantidades = request.POST.getlist('item_quantidade')
        valores_totais = request.POST.getlist('item_valor_total')
        validades = request.POST.getlist('item_validade')
        
        # Reconstrói os itens digitados para re-preencher o formulário em caso de erro
        itens_list = []
        for i in range(len(produto_ids)):
            p_id = produto_ids[i]
            qty_str = quantidades[i] if i < len(quantidades) else '1'
            val_tot_str = valores_totais[i] if i < len(valores_totais) else '0,00'
            val_date_str = validades[i].strip() if i < len(validades) else ''
            
            itens_list.append({
                'produto_id': p_id,
                'quantidade_raw': qty_str,
                'valor_total_raw': val_tot_str,
                'validade': val_date_str
            })
            
        if not itens_list:
            itens_list.append({
                'produto_id': '',
                'quantidade_raw': '1',
                'valor_total_raw': '0,00',
                'validade': ''
            })
            
        itens_json = json.dumps(itens_list)
        
        data_compra = date.today()
        if data_compra_str:
            try:
                data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        fornecedor = None
        if fornecedor_id:
            try:
                fornecedor = Fornecedor.objects.get(id=fornecedor_id, hotel=hotel)
            except Fornecedor.DoesNotExist:
                pass
                
        # Validação: Pelo menos um item válido
        valid_items_count = 0
        for i in range(len(produto_ids)):
            p_id = produto_ids[i]
            qty_str = quantidades[i].replace('.', '').replace(',', '.').strip() if i < len(quantidades) else ''
            val_tot_str = valores_totais[i].replace('.', '').replace(',', '.').strip() if i < len(valores_totais) else ''
            if p_id and qty_str and val_tot_str:
                valid_items_count += 1
                
        if valid_items_count == 0:
            context = {
                'fornecedores': fornecedores,
                'produtos': produtos,
                'hoje': data_compra_str or hoje,
                'observacao': observacao,
                'fornecedor_selected_id': fornecedor_id,
                'itens_json': itens_json,
                'error_message': 'A compra deve possuir pelo menos um item válido com produto, quantidade e valor total informados!'
            }
            return render(request, 'estoque/partials/form_compra.html', context)
            
        try:
            with transaction.atomic():
                compra = Compra.objects.create(
                    hotel=hotel,
                    fornecedor=fornecedor,
                    data_compra=data_compra,
                    observacao=observacao,
                    status='pendente',
                    criado_por=request.user
                )
                
                valor_total = 0
                for i in range(len(produto_ids)):
                    p_id = produto_ids[i]
                    qty_str = quantidades[i].replace('.', '').replace(',', '.').strip() if i < len(quantidades) else ''
                    val_tot_str = valores_totais[i].replace('.', '').replace(',', '.').strip() if i < len(valores_totais) else ''
                    val_date_str = validades[i].strip() if i < len(validades) else ''
                    
                    if not p_id or not qty_str or not val_tot_str:
                        continue
                        
                    prod = get_object_or_404(Produto, id=p_id, hotel=hotel)
                    qty = float(qty_str)
                    v_tot = float(val_tot_str)
                    
                    # Autocalcula o preço unitário
                    p_unit = v_tot / qty if qty > 0 else 0.0
                    
                    val_date = None
                    if val_date_str:
                        try:
                            val_date = datetime.strptime(val_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    
                    ItemCompra.objects.create(
                        compra=compra,
                        produto=prod,
                        quantidade=qty,
                        preco_unitario=p_unit,
                        subtotal=v_tot,
                        validade=val_date
                    )
                    valor_total += v_tot
                    
                compra.valor_total = valor_total
                compra.save()
                
                # Salva arquivos de documentação/comprovantes anexados
                arquivos = request.FILES.getlist('arquivos')
                for arq in arquivos:
                    DocumentoCompra.objects.create(
                        compra=compra,
                        arquivo=arq,
                        nome=arq.name
                    )
                
            messages.success(request, "Compra registrada como Pendente!")
            if request.headers.get('HX-Request') == 'true':
                return render(request, 'estoque/partials/success_modal.html', {
                    'titulo': 'Sucesso!',
                    'mensagem': 'A compra foi registrada como Pendente com sucesso.'
                })
            return redirect('hoteis:partner_dashboard')
            
        except Exception as e:
            context = {
                'fornecedores': fornecedores,
                'produtos': produtos,
                'hoje': data_compra_str or hoje,
                'observacao': observacao,
                'fornecedor_selected_id': fornecedor_id,
                'itens_json': itens_json,
                'error_message': f'Erro ao salvar a compra: {str(e)}'
            }
            return render(request, 'estoque/partials/form_compra.html', context)
            
    context = {
        'fornecedores': fornecedores,
        'produtos': produtos,
        'hoje': hoje,
        'itens_json': json.dumps([{
            'produto_id': '',
            'quantidade_raw': '1',
            'valor_total_raw': '0,00',
            'validade': ''
        }])
    }
    return render(request, 'estoque/partials/form_compra.html', context)

@login_required(login_url='hoteis:partner_login')
@require_POST
def receber_compra(request, compra_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    compra = get_object_or_404(Compra, id=compra_id, hotel=hotel)
    
    if compra.status != 'pendente':
        messages.error(request, "Esta compra não está pendente!")
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))
        
    with transaction.atomic():
        compra.status = 'recebida'
        compra.pago = True
        compra.recebido = True
        compra.save()
        
        # Atualiza estoque físico e gera movimentações
        for item in compra.itens.all():
            produto = item.produto
            produto.estoque_atual += item.quantidade
            produto.save()
            
            MovimentoEstoque.objects.create(
                hotel=hotel,
                produto=produto,
                tipo='entrada',
                quantidade=item.quantidade,
                referencia=f"Entrada por Compra #{compra.id}",
                criado_por=request.user
            )
            
        # Lança automaticamente no financeiro
        TransacaoFinanceira.objects.create(
            hotel=hotel,
            tipo='despesa',
            categoria='outro_despesa',
            valor=compra.valor_total,
            descricao=f"Compra #{compra.id} recebida - Fornecedor: {compra.fornecedor.nome if compra.fornecedor else 'Sem Fornecedor'}",
            data_vencimento=compra.data_compra,
            data_pagamento=date.today(),
            criado_por=request.user
        )
        
    messages.success(request, f"Compra #{compra.id} recebida! Estoque abastecido e despesa lançada no financeiro.")
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
        return response
    return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

@login_required(login_url='hoteis:partner_login')
@require_POST
def cancelar_compra(request, compra_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    compra = get_object_or_404(Compra, id=compra_id, hotel=hotel)
    
    if compra.status == 'cancelada':
        messages.error(request, "Esta compra já está cancelada!")
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))
        
    with transaction.atomic():
        # Revert payment if paid
        if compra.pago:
            desc = f"Compra #{compra.id} recebida - Fornecedor: {compra.fornecedor.nome if compra.fornecedor else 'Sem Fornecedor'}"
            TransacaoFinanceira.objects.filter(hotel=hotel, tipo='despesa', descricao=desc).delete()
            compra.pago = False
            
        # Revert stock if received
        if compra.recebido:
            for item in compra.itens.all():
                produto = item.produto
                produto.estoque_atual -= item.quantidade
                produto.save()
                
                ref = f"Entrada por Compra #{compra.id}"
                MovimentoEstoque.objects.filter(hotel=hotel, produto=produto, tipo='entrada', referencia=ref).delete()
            compra.recebido = False
            
        compra.status = 'cancelada'
        compra.save()
        
    messages.success(request, f"Compra #{compra.id} cancelada com sucesso.")
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
        return response
    return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))


# --- MOVIMENTAÇÕES MANUAIS (SAÍDAS / AJUSTES) ---

@login_required(login_url='hoteis:partner_login')
def registrar_movimento(request):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        produto_id = request.POST.get('produto_id')
        tipo = request.POST.get('tipo', 'saida') # saida ou ajuste
        quantidade_str = request.POST.get('quantidade', '0').replace(',', '.').strip()
        motivo = request.POST.get('motivo', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        
        from decimal import Decimal, InvalidOperation
        try:
            quantidade = Decimal(quantidade_str)
        except (ValueError, InvalidOperation):
            quantidade = Decimal('0.0')
            
        if not produto_id or quantidade <= 0:
            messages.error(request, "Produto e quantidade válidos são obrigatórios!")
            return redirect('hoteis:partner_dashboard')
            
        produto = get_object_or_404(Produto, id=produto_id, hotel=hotel)
        
        with transaction.atomic():
            if tipo == 'saida':
                # Subtrai do estoque
                produto.estoque_atual -= quantidade
                produto.save()
                
                final_ref = referencia or f"Saída manual: {motivo}"
                MovimentoEstoque.objects.create(
                    hotel=hotel,
                    produto=produto,
                    tipo='saida',
                    quantidade=quantidade,
                    referencia=final_ref,
                    criado_por=request.user
                )
                
                # Se for do tipo 'venda' (Venda de balcão), lançar receita no financeiro
                if motivo == 'venda' and produto.preco_venda:
                    valor_venda = produto.preco_venda * quantidade
                    TransacaoFinanceira.objects.create(
                        hotel=hotel,
                        tipo='receita',
                        categoria='frigobar',
                        valor=valor_venda,
                        descricao=f"Venda direta: {quantidade}x {produto.nome}",
                        data_vencimento=date.today(),
                        data_pagamento=date.today(),
                        criado_por=request.user
                    )
                    messages.success(request, f"Saída registrada! Lançado R$ {valor_venda:.2f} de receita no financeiro.")
                else:
                    messages.success(request, f"Saída de {quantidade} {produto.unidade_medida} registrada com sucesso!")
                    
            elif tipo == 'ajuste':
                # Ajuste direto de inventário
                diferenca = quantidade - produto.estoque_atual
                produto.estoque_atual = quantidade
                produto.save()
                
                MovimentoEstoque.objects.create(
                    hotel=hotel,
                    produto=produto,
                    tipo='ajuste',
                    quantidade=abs(diferenca),
                    referencia=referencia or f"Ajuste físico de estoque para {quantidade} {produto.unidade_medida}",
                    criado_por=request.user
                )
                messages.success(request, f"Estoque ajustado para {quantidade} {produto.unidade_medida}!")
                
        if request.headers.get('HX-Request') == 'true':
            msg = f"Movimentação de {produto.nome} registrada com sucesso."
            if tipo == 'saida':
                msg = f"Saída de {quantidade} {produto.unidade_medida} de {produto.nome} registrada."
            elif tipo == 'ajuste':
                msg = f"Estoque de {produto.nome} ajustado para {quantidade} {produto.unidade_medida}."
            return render(request, 'estoque/partials/success_modal.html', {
                'titulo': 'Sucesso!',
                'mensagem': msg
            })
        return redirect('hoteis:partner_dashboard')
        
    produtos = Produto.objects.filter(hotel=hotel, ativo=True)
    context = {
        'produtos': produtos,
    }
    return render(request, 'estoque/partials/modal_movimento.html', context)


def qty_dec_cast(val):
    from decimal import Decimal
    return Decimal(str(val))


@login_required(login_url='hoteis:partner_login')
@require_POST
def toggle_compra_pago(request, compra_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    compra = get_object_or_404(Compra, id=compra_id, hotel=hotel)
    
    if compra.status == 'cancelada':
        return HttpResponse("Compra cancelada não pode ser alterada.", status=400)
        
    with transaction.atomic():
        compra.pago = not compra.pago
        compra.save()
        
        desc = f"Compra #{compra.id} recebida - Fornecedor: {compra.fornecedor.nome if compra.fornecedor else 'Sem Fornecedor'}"
        if compra.pago:
            tx_exists = TransacaoFinanceira.objects.filter(
                hotel=hotel, 
                tipo='despesa', 
                descricao=desc
            ).exists()
            if not tx_exists:
                TransacaoFinanceira.objects.create(
                    hotel=hotel,
                    tipo='despesa',
                    categoria='outro_despesa',
                    valor=compra.valor_total,
                    descricao=desc,
                    data_vencimento=compra.data_compra,
                    data_pagamento=date.today(),
                    criado_por=request.user
                )
        else:
            TransacaoFinanceira.objects.filter(
                hotel=hotel, 
                tipo='despesa', 
                descricao=desc
            ).delete()
            
    status_label = "paga" if compra.pago else "não paga"
    messages.success(request, f"Status de pagamento da Compra #{compra.id} alterado para {status_label}.")
    
    return render(request, 'estoque/partials/compra_row.html', {'compra': compra})


@login_required(login_url='hoteis:partner_login')
@require_POST
def toggle_compra_recebido(request, compra_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    compra = get_object_or_404(Compra, id=compra_id, hotel=hotel)
    
    if compra.status == 'cancelada':
        return HttpResponse("Compra cancelada não pode ser alterada.", status=400)
        
    with transaction.atomic():
        compra.recebido = not compra.recebido
        
        if compra.recebido:
            compra.status = 'recebida'
            compra.save()
            
            # Add to stock
            for item in compra.itens.all():
                produto = item.produto
                produto.estoque_atual += item.quantidade
                produto.save()
                
                ref = f"Entrada por Compra #{compra.id}"
                if not MovimentoEstoque.objects.filter(hotel=hotel, produto=produto, tipo='entrada', referencia=ref).exists():
                    MovimentoEstoque.objects.create(
                        hotel=hotel,
                        produto=produto,
                        tipo='entrada',
                        quantidade=item.quantidade,
                        referencia=ref,
                        criado_por=request.user
                    )
        else:
            compra.status = 'pendente'
            compra.save()
            
            # Remove from stock
            for item in compra.itens.all():
                produto = item.produto
                produto.estoque_atual -= item.quantidade
                produto.save()
                
                ref = f"Entrada por Compra #{compra.id}"
                MovimentoEstoque.objects.filter(hotel=hotel, produto=produto, tipo='entrada', referencia=ref).delete()
                
    status_label = "recebida" if compra.status == 'recebida' else "pendente"
    messages.success(request, f"Status de recebimento da Compra #{compra.id} alterado para {status_label}.")
    
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
        return response
    return render(request, 'estoque/partials/compra_row.html', {'compra': compra})


@login_required(login_url='hoteis:partner_login')
@require_POST
def reverter_movimento(request, movimento_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    movimento = get_object_or_404(MovimentoEstoque, id=movimento_id, hotel=hotel)

    if movimento.tipo != 'saida':
        msg = "Apenas movimentações de saída podem ser revertidas!"
        messages.error(request, msg)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

    if movimento.reversoes.exists():
        msg = "Esta movimentação já foi revertida!"
        messages.error(request, msg)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

    with transaction.atomic():
        produto = movimento.produto
        # Devolve o estoque
        produto.estoque_atual += movimento.quantidade
        produto.save()

        # Cria movimento de reversão (tipo entrada)
        reversao = MovimentoEstoque.objects.create(
            hotel=hotel,
            produto=produto,
            tipo='entrada',
            quantidade=movimento.quantidade,
            referencia=f"Reversão da Saída #{movimento.id}",
            movimento_origem=movimento,
            criado_por=request.user
        )

        # Estorna receita financeira correspondente se houver
        desc_busca = f"Venda direta: {movimento.quantidade}x {produto.nome}"
        TransacaoFinanceira.objects.filter(
            hotel=hotel, 
            tipo='receita', 
            descricao=desc_busca, 
            valor=produto.preco_venda * movimento.quantidade if produto.preco_venda else 0
        ).delete()

    msg = f"Saída de {movimento.quantidade} {produto.unidade_medida} de {produto.nome} revertida!"
    messages.success(request, msg)
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
        return response

    return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))


@login_required(login_url='hoteis:partner_login')
@require_POST
def relancar_movimento(request, movimento_id):
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    reversao = get_object_or_404(MovimentoEstoque, id=movimento_id, hotel=hotel)

    if reversao.tipo != 'entrada' or not reversao.movimento_origem:
        msg = "Apenas reversões de saída podem ser relançadas!"
        messages.error(request, msg)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

    if reversao.reversoes.exists():
        msg = "Esta reversão já foi relançada!"
        messages.error(request, msg)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

    origem = reversao.movimento_origem
    produto = reversao.produto

    # Verifica estoque
    if produto.estoque_atual < reversao.quantidade:
        msg = f"Estoque insuficiente para relançar a saída de {reversao.quantidade} {produto.unidade_medida}!"
        messages.error(request, msg)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
            return response
        return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))

    with transaction.atomic():
        # Deduz estoque
        produto.estoque_atual -= reversao.quantidade
        produto.save()

        # Cria movimento de relançamento
        relancado = MovimentoEstoque.objects.create(
            hotel=hotel,
            produto=produto,
            tipo='saida',
            quantidade=reversao.quantidade,
            referencia=f"Re-lançamento da Saída #{origem.id} (Ref: #{reversao.id})",
            movimento_origem=reversao,
            criado_por=request.user
        )

        # Se a origem ou o produto fossem venda, relança receita financeira
        era_venda = False
        if origem.referencia and "Venda direta:" in origem.referencia:
            era_venda = True
        elif produto.finalidade in ['venda', 'ambos'] and produto.preco_venda:
            era_venda = True

        if era_venda and produto.preco_venda:
            valor_venda = produto.preco_venda * reversao.quantidade
            TransacaoFinanceira.objects.create(
                hotel=hotel,
                tipo='receita',
                categoria='frigobar',
                valor=valor_venda,
                descricao=f"Venda direta: {reversao.quantidade}x {produto.nome}",
                data_vencimento=date.today(),
                data_pagamento=date.today(),
                criado_por=request.user
            )

    msg = f"Saída de {reversao.quantidade} {produto.unidade_medida} de {produto.nome} relançada com sucesso!"
    messages.success(request, msg)
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Location'] = '/hospedagens/sistema/?tab=estoque'
        return response

    return HttpResponseRedirect(reverse('hoteis:partner_dashboard'))
