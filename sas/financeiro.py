from decimal import Decimal
from django.db import models
from sas.models import RegraTaxa
from core.models import PlataformaConfig

def calcular_taxas_reserva(empresa, categoria, valor_unitario, noites=1):
    """
    Motor central de taxas do Naviê Vibe (SAS).
    Calcula split de pagamentos, taxas de serviço, taxas de gateway e margens da plataforma.
    """
    # Converter para Decimal caso venha como float ou int
    valor_unitario = Decimal(str(valor_unitario))
    noites = Decimal(str(noites))
    
    # 1. Buscar regras aplicáveis (específicas do parceiro ou globais da categoria)
    regras = RegraTaxa.objects.filter(
        ativo=True,
        categoria=categoria
    ).filter(
        models.Q(empresa=empresa) | models.Q(empresa__isnull=True)
    ).order_by('-ordem_prioridade', '-empresa_id', 'valor_minimo')
    
    # 2. Match com faixa de preço (tier)
    regra_aplicada = None
    for r in regras:
        val_min = r.valor_minimo
        val_max = r.valor_maximo
        if val_min <= valor_unitario and (val_max is None or valor_unitario <= val_max):
            regra_aplicada = r
            break
            
    # 3. Calcular taxa cobrada do cliente
    if regra_aplicada:
        if regra_aplicada.tipo_taxa == 'percentual':
            subtotal = valor_unitario * noites
            taxa_servico = subtotal * (regra_aplicada.valor / Decimal('100.00'))
        else:
            if regra_aplicada.cobranca_por_diaria and categoria == 'hospedagem':
                taxa_servico = regra_aplicada.valor * noites
            else:
                taxa_servico = regra_aplicada.valor
    else:
        # Fallback usando comissão do PlataformaConfig
        config = PlataformaConfig.get_solo()
        percentual = Decimal('10.00')
        if categoria == 'hospedagem':
            percentual = config.taxa_hospedagem
        elif categoria == 'cinema':
            percentual = config.taxa_cinema
        elif categoria == 'eventos':
            percentual = config.taxa_eventos
        elif categoria == 'parques':
            percentual = config.taxa_parques
            
        subtotal = valor_unitario * noites
        taxa_servico = subtotal * (Decimal(str(percentual)) / Decimal('100.00'))
        
    subtotal = valor_unitario * noites
    total_cliente = subtotal + taxa_servico
    
    # 4. Calcular Taxa do Gateway (Mercado Pago, padrão 3%)
    config = PlataformaConfig.get_solo()
    gateway_pct = getattr(config, 'taxa_gateway_percentual', Decimal('3.00'))
    taxa_gateway = total_cliente * (gateway_pct / Decimal('100.00'))
    
    # 5. Split Financeiro: Parceiro recebe 100% da diária, Naviê absorve o gateway
    repasse_parceiro = subtotal
    ganho_liquido = taxa_servico - taxa_gateway
    
    # Arredondar para duas casas decimais
    return {
        'subtotal': subtotal.quantize(Decimal('0.01')),
        'taxa_servico': taxa_servico.quantize(Decimal('0.01')),
        'total_cliente': total_cliente.quantize(Decimal('0.01')),
        'taxa_gateway': taxa_gateway.quantize(Decimal('0.01')),
        'repasse_parceiro': repasse_parceiro.quantize(Decimal('0.01')),
        'ganho_liquido': ganho_liquido.quantize(Decimal('0.01')),
        'regra_id': regra_aplicada.id if regra_aplicada else None
    }
