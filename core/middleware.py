class SubdomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        full_host = request.get_host()
        
        # Define o base_host padrão
        request.base_host = full_host
        request.subdomains_supported = not host.replace('.', '').isdigit()
        
        # Ignorar endereços IP diretos
        if request.subdomains_supported:
            parts = host.split('.')
            if len(parts) > 1:
                # O subdomínio será a primeira parte do host
                possible_subdomain = parts[0]
                
                # Termos reservados que não devem ser interpretados como subdomínios de pousadas
                reservados = ['www', 'admin', 'accounts', 'api', 'clientes', 'hospedagens', 'hotelaria', 'static', 'media', 'dashboard', 'navievibe']
                if possible_subdomain not in reservados:
                    # Constrói o host pai sem o subdomínio de qualquer forma
                    first_dot = full_host.find('.')
                    if first_dot != -1:
                        parent_host = full_host[first_dot + 1:]
                        request.base_host = parent_host
                        request.parent_host_url = f"{request.scheme}://{parent_host}"

                    # 1. Verifica se é um subdomínio de portal de rede unificado
                    from core.models import Empresa
                    empresa = Empresa.objects.filter(slug=possible_subdomain, modalidade_portal='unificado').first()
                    if empresa:
                        request.subdomain = possible_subdomain
                        request.empresa_atual = empresa
                    else:
                        from hoteis.models import Hotel
                        # 2. Verifica se existe um hotel com o slug igual ao subdomínio
                        hotel = Hotel.objects.filter(slug=possible_subdomain).first()
                        if hotel:
                            request.subdomain = possible_subdomain
                            request.hotel_atual = hotel
                        else:
                            from restaurantes.models import Restaurante
                            # 3. Verifica se existe um restaurante correspondente ao subdomínio
                            restaurante = Restaurante.objects.using('restaurantes').filter(slug=possible_subdomain, ativo=True).first()
                            if not restaurante:
                                normalized_subdomain = possible_subdomain.replace('-', '').replace('_', '')
                                for r in Restaurante.objects.using('restaurantes').filter(ativo=True):
                                    if r.slug.replace('-', '').replace('_', '') == normalized_subdomain:
                                        restaurante = r
                                        break
                            
                            if restaurante:
                                request.subdomain = possible_subdomain
                                request.restaurante_atual = restaurante
                            else:
                                # Se não for uma rota estática, de mídia, api ou admin, levanta 404
                                if not any(request.path.startswith(prefix) for prefix in ['/static/', '/media/', '/api/', '/sistemadeadministracao/', '/accounts/', '/hospedagens/', '/restaurantes/']):
                                    from django.http import Http404
                                    raise Http404("Página não encontrada.")
        
        response = self.get_response(request)
        return response
