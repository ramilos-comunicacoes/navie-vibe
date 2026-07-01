from .models import Hotel

class PartnerHotelMiddleware:
    """
    Middleware to handle multi-property switching for partners in Naviê Vibe.
    If the partner has a global role (proprietario, gerente), they can switch
    the active hotel via ?set_hotel=ID. Operatives are locked to their profile hotel.
    
    Dynamic Shadowing is applied to `request.user.perfil_parceiro.hotel` in memory,
    ensuring all existing views automatically fetch queries filtered by the active hotel.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'perfil_parceiro'):
            perfil = request.user.perfil_parceiro
            hotel_ativo = perfil.hotel
            hoteis_autorizados = []
            
            # Dynamic switch for portaria based on subdomain if in the same company
            if perfil.role == 'portaria' and hasattr(request, 'hotel_atual') and request.hotel_atual and perfil.hotel and perfil.hotel.empresa:
                if request.hotel_atual.empresa == perfil.hotel.empresa:
                    hotel_ativo = request.hotel_atual
            
            # Global roles can toggle active properties within the same company (Empresa)
            if (perfil.role in ['proprietario', 'gerente'] or request.user.is_superuser) and perfil.hotel and perfil.hotel.empresa:
                empresa = perfil.hotel.empresa
                hoteis_autorizados = Hotel.objects.filter(empresa=empresa, status='ativo')
                
                # Check for query parameter
                set_hotel_id = request.GET.get('set_hotel')
                if set_hotel_id:
                    try:
                        hotel_selecionado = Hotel.objects.get(id=set_hotel_id, empresa=empresa, status='ativo')
                        request.session['active_hotel_id'] = hotel_selecionado.id
                        hotel_ativo = hotel_selecionado
                    except (Hotel.DoesNotExist, ValueError):
                        pass
                else:
                    # Check in session
                    session_hotel_id = request.session.get('active_hotel_id')
                    if session_hotel_id:
                        try:
                            hotel_ativo = Hotel.objects.get(id=session_hotel_id, empresa=empresa, status='ativo')
                        except (Hotel.DoesNotExist, ValueError):
                            pass
            
            # Dynamic Shadowing: shadow the model field value on the instance in-memory for the current request
            perfil.hotel = hotel_ativo
            request.hotel_ativo = hotel_ativo
            request.hoteis_autorizados = list(hoteis_autorizados) if len(hoteis_autorizados) > 1 else []
        else:
            request.hotel_ativo = None
            request.hoteis_autorizados = []
            
        response = self.get_response(request)
        return response
