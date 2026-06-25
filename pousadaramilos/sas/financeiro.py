from decimal import Decimal

def calcular_taxas_reserva(categoria, noites=1):
    """
    Calcula as taxas de serviço da plataforma (5%) e splits financeiros
    de repasse ao parceiro. Incorpora descontos progressivos se aplicáveis.
    """
    preco_diaria = Decimal(str(categoria.preco_base))
    
    # Aplica o desconto progressivo de diárias se aplicável
    if categoria.tem_desconto_multidias and int(noites) >= int(categoria.dias_minimos_desconto):
        desconto = preco_diaria * (Decimal(str(categoria.percentual_desconto)) / Decimal('100.00'))
        preco_diaria = preco_diaria - desconto
        
    subtotal = preco_diaria * int(noites)
    
    # Sem taxa de serviço ou gateway (sistema isolado)
    taxa_servico = Decimal('0.00')
    taxa_gateway = Decimal('0.00')
    
    total_cliente = subtotal
    repasse_parceiro = subtotal
    ganho_liquido = Decimal('0.00')
    
    return {
        'subtotal': subtotal,
        'taxa_servico': taxa_servico,
        'taxa_gateway': taxa_gateway,
        'total_cliente': total_cliente,
        'repasse_parceiro': repasse_parceiro,
        'ganho_liquido': ganho_liquido
    }
