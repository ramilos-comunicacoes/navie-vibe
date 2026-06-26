from datetime import timedelta
from django.db.models import Q
from hoteis.models import UnidadeQuarto, Reserva, BloqueioQuarto, Quarto

def verifica_disponibilidade_unidade(unidade, checkin, checkout):
    if not unidade.ativa or not getattr(unidade, 'disponivel', True):
        return False
        
    # Check bloqueios
    bloqueios = BloqueioQuarto.objects.filter(
        unidade=unidade,
        data_inicio__lt=checkout,
        data_fim__gt=checkin
    ).exists()
    if bloqueios: return False
    
    # Check reservas
    reservas = Reserva.objects.filter(
        unidade=unidade,
        data_checkin__lt=checkout,
        data_checkout__gt=checkin
    ).exclude(status='cancelada').exists()
    if reservas: return False
    
    return True

def checar_disponibilidade_quarto(quarto, checkin, checkout):
    """Retorna True se houver pelo menos uma unidade livre nesta categoria."""
    unidades = quarto.unidades.filter(ativa=True, disponivel=True)
    if not unidades.exists(): return False # Sem unidades cadastradas
    
    for uni in unidades:
        if verifica_disponibilidade_unidade(uni, checkin, checkout):
            return True # Achou uma livre
    return False

def buscar_datas_proximas(quarto, data_alvo_in, noites):
    """Tenta buscar +- 30 dias para sugerir uma data em que esse tipo de quarto esteja vago."""
    
    sugestao_antes = None
    sugestao_depois = None
    
    # Busca para trás
    for d in range(1, 40):
        t_in = data_alvo_in - timedelta(days=d)
        t_out = t_in + timedelta(days=noites)
        # Nao sugerir data no passado
        # if t_in < datetime.today().date(): break # Ignorando isso por enquanto mock
        if checar_disponibilidade_quarto(quarto, t_in, t_out):
            sugestao_antes = t_in
            break
            
    # Busca para frente
    for d in range(1, 40):
        t_in = data_alvo_in + timedelta(days=d)
        t_out = t_in + timedelta(days=noites)
        if checar_disponibilidade_quarto(quarto, t_in, t_out):
            sugestao_depois = t_in
            break
            
    return sugestao_antes, sugestao_depois
