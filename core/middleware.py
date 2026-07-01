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
            host_lower = host.lower()
            identifier = None
            
            if 'navievibe.com' in host_lower:
                # É um subdomínio de navievibe.com
                parts = host_lower.split('.')
                if len(parts) >= 3:
                    if parts[0] == 'www' and len(parts) >= 4:
                        identifier = parts[1]
                    else:
                        identifier = parts[0]
            else:
                # É um domínio próprio (ex: manacadaserra.com ou www.manacadaserra.com)
                parts = host_lower.split('.')
                if parts[0] == 'www' and len(parts) >= 3:
                    identifier = parts[1]
                else:
                    identifier = parts[0]
            
            reservados = ['www', 'admin', 'accounts', 'api', 'clientes', 'hospedagens', 'hotelaria', 'static', 'media', 'dashboard', 'navievibe']
            if identifier and identifier not in reservados:
                # Constrói o host pai sem o subdomínio se estiver no domínio principal
                if 'navievibe.com' in host_lower:
                    first_dot = full_host.find('.')
                    if first_dot != -1:
                        parent_host = full_host[first_dot + 1:]
                        if parent_host.startswith('www.'):
                            parent_host = parent_host[4:]
                        request.base_host = parent_host
                        request.parent_host_url = f"{request.scheme}://{parent_host}"

                # 1. Verifica se é um subdomínio de portal de rede unificado
                from core.models import Empresa
                empresa = Empresa.objects.filter(slug=identifier, modalidade_portal='unificado').first()
                if empresa:
                    request.subdomain = identifier
                    request.empresa_atual = empresa
                else:
                    from hoteis.models import Hotel
                    # 2. Verifica se existe um hotel com o slug igual ao subdomínio
                    hotel = Hotel.objects.filter(slug=identifier).first()
                    if hotel:
                        request.subdomain = identifier
                        request.hotel_atual = hotel
                    else:
                        from restaurantes.models import Restaurante
                        # 3. Verifica se existe um restaurante correspondente
                        restaurante = Restaurante.objects.using('restaurantes').filter(slug=identifier, ativo=True).first()
                        if not restaurante:
                            normalized_identifier = identifier.replace('-', '').replace('_', '')
                            for r in Restaurante.objects.using('restaurantes').filter(ativo=True):
                                if r.slug_normalized == normalized_identifier:
                                    restaurante = r
                                    break
                        
                        if restaurante:
                            request.subdomain = identifier
                            request.restaurante_atual = restaurante
                        else:
                            # Se não for uma rota estática, de mídia, api ou admin, levanta 404
                            if not any(request.path.startswith(prefix) for prefix in ['/static/', '/media/', '/api/', '/sistemadeadministracao/', '/accounts/', '/hospedagens/', '/restaurantes/']):
                                from django.http import Http404
                                raise Http404("Página não encontrada.")
        
        response = self.get_response(request)
        return response
