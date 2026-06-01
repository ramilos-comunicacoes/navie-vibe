from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib import messages
from decimal import Decimal
import datetime
from .models import TransacaoFinanceira, AnexoTransacao
from hoteis.models import UnidadeQuarto, Reserva

@login_required(login_url='hoteis:partner_login')
@require_POST
def criar_transacao_api(request):
    """
    [AI-ACCESSIBLE ACTION VIEW]
    Registra uma nova receita ou despesa no caixa real do hotel multitenant do parceiro logado.
    
    ESTA VIEW É TOTALMENTE COMPATÍVEL COM AGENTES DE IA E CHATBOTS.
    Para que um agente de IA (como bot de WhatsApp ou assistente de voz) crie uma transação,
    ela deve enviar uma requisição POST com os seguintes parâmetros:
    
    1. 'tipo': String ('receita' para entrada de caixa, 'despesa' para saída de caixa).
    2. 'categoria': String. Valores permitidos:
       - Para receitas: 'diarias', 'walk_in', 'frigobar', 'room_service', 'spa_lazer', 'outro_receita'.
       - Para despesas: 'salarios', 'manutencao', 'energia_agua', 'amenities', 'taxa_marketplace', 'outro_despesa'.
    3. 'valor': String ou Float. Ex: "150.00" ou "R$ 1.500,50" (o sistema trata a formatação brasileira).
    4. 'descricao': String. Descrição livre detalhando o motivo do lançamento (máx 255 caracteres).
    5. 'data_vencimento': String no formato 'YYYY-MM-DD' (Data obrigatória de vencimento).
    6. 'data_pagamento': String no formato 'YYYY-MM-DD' (Data opcional de quitação).
    7. 'unidade': ID inteiro (opcional) da unidade de quarto física associada.
    8. 'reserva': UUID string (opcional) da reserva/hóspede associado.
    9. 'arquivos': Upload de múltiplos arquivos físicos (comprovantes).
    
    RETORNOS SEMÂNTICOS:
    - Sucesso: Redireciona ou retorna 'HX-Refresh' para recarregar a tela do painel do hotel.
    - Erro de Validação: Retorna JsonResponse com {'success': False, 'error': '<mensagem de erro>'} (status 400).
    - Não Autorizado: Retorna JsonResponse com {'success': False, 'error': '<motivo>'} (status 403).
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return JsonResponse({
            'success': False, 
            'error': 'Acesso negado. Apenas parceiros comerciais hoteleiros autenticados podem realizar lançamentos contábeis.'
        }, status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    
    tipo = request.POST.get('tipo', '').strip().lower()
    categoria = request.POST.get('categoria', '').strip().lower()
    valor_raw = request.POST.get('valor', '0').strip()
    descricao = request.POST.get('descricao', '').strip()
    
    data_vencimento_str = request.POST.get('data_vencimento', '').strip()
    data_pagamento_str = request.POST.get('data_pagamento', '').strip()
    
    unidade_id = request.POST.get('unidade', '').strip()
    reserva_id = request.POST.get('reserva', '').strip()
    
    # 1. Validação do Tipo
    if tipo not in ['receita', 'despesa']:
        return JsonResponse({
            'success': False, 
            'error': "Parâmetro 'tipo' inválido. Envie exatamente 'receita' ou 'despesa'."
        }, status=400)
        
    # 2. Validação da Categoria
    categorias_permitidas = [c[0] for c in TransacaoFinanceira.CATEGORIA_CHOICES]
    if categoria not in categorias_permitidas:
        return JsonResponse({
            'success': False, 
            'error': f"Categoria '{categoria}' inválida. Consulte a documentação para obter a lista de categorias aceitas."
        }, status=400)
        
    # 3. Tratamento e Validação do Valor Financeiro (Formatação BR para float seguro)
    try:
        valor_limpo = valor_raw.replace('R$', '').replace(' ', '')
        # Se for formato BR com pontos de milhar e vírgula decimal (ex: 1.500,50)
        if ',' in valor_limpo:
            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
        valor = Decimal(valor_limpo)
        if valor <= 0:
            raise ValueError()
    except Exception:
        return JsonResponse({
            'success': False, 
            'error': "O 'valor' enviado é inválido. Envie um número decimal positivo (ex: 150.00)."
        }, status=400)
        
    # 4. Validação da Descrição
    if not descricao:
        return JsonResponse({
            'success': False, 
            'error': "A 'descricao' da transação é obrigatória para fins de auditoria de caixa."
        }, status=400)
        
    # 5. Tratamento das datas (Vencimento e Pagamento)
    try:
        if data_vencimento_str:
            data_vencimento = datetime.datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
        else:
            data_vencimento = datetime.date.today()
    except Exception:
        return JsonResponse({
            'success': False, 
            'error': "A 'data_vencimento' enviada está em formato inválido. Use exatamente o formato 'YYYY-MM-DD'."
        }, status=400)
        
    data_pagamento = None
    if data_pagamento_str:
        try:
            data_pagamento = datetime.datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        except Exception:
            return JsonResponse({
                'success': False, 
                'error': "A 'data_pagamento' enviada está em formato inválido. Use exatamente o formato 'YYYY-MM-DD'."
            }, status=400)
            
    # 6. Associações Contábeis (Quarto e Reserva/Hóspede)
    unidade = None
    if unidade_id:
        try:
            unidade = UnidadeQuarto.objects.get(id=unidade_id, quarto__hotel=hotel)
        except (ValueError, UnidadeQuarto.DoesNotExist):
            pass
            
    reserva = None
    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id, unidade__quarto__hotel=hotel)
        except (ValueError, Reserva.DoesNotExist):
            pass
        
    # 7. Gravação segura do Lançamento
    transacao = TransacaoFinanceira.objects.create(
        hotel=hotel,
        tipo=tipo,
        categoria=categoria,
        valor=valor,
        descricao=descricao,
        data_vencimento=data_vencimento,
        data_pagamento=data_pagamento,
        unidade=unidade,
        reserva=reserva,
        criado_por=request.user
    )
    
    # 8. Salvamento dos Comprovantes/Arquivos
    arquivos = request.FILES.getlist('arquivos')
    for arq in arquivos:
        AnexoTransacao.objects.create(
            transacao=transacao,
            arquivo=arq
        )
    
    # 9. Resposta reativa compatível com HTMX
    if request.headers.get('HX-Request') == 'true':
        # Retorna cabeçalho do HTMX que instrui a página principal a recarregar de forma limpa
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response
        
    messages.success(request, f"Lançamento {transacao.codigo} registrado com sucesso!")
    return redirect('hoteis:partner_dashboard')

