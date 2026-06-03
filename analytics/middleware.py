import uuid

class TrackerMiddleware:
    """
    Middleware global para garantir que todos os visitantes (anônimos ou autenticados)
    tenham um identificador único de rastreamento (navie_tracker_id) nos cookies.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tracker_id = request.COOKIES.get('navie_tracker_id')
        
        # Ignorar caminhos estáticos ou de mídia para evitar processamento desnecessário
        is_static = any(request.path.startswith(prefix) for prefix in ['/static/', '/media/'])
        
        request.tracker_id = tracker_id
        request._set_tracker_cookie = None

        if not tracker_id and not is_static:
            # Gerar um novo UUID único para o rastreador
            new_id = str(uuid.uuid4())
            request.tracker_id = new_id
            request._set_tracker_cookie = new_id

        response = self.get_response(request)

        # Se foi gerado um novo tracker_id nesta requisição, define o cookie na resposta
        if getattr(request, '_set_tracker_cookie', None):
            # Define o cookie com duração de 365 dias, acessível por JavaScript (httponly=False)
            response.set_cookie(
                'navie_tracker_id',
                request._set_tracker_cookie,
                max_age=365 * 24 * 60 * 60,
                samesite='Lax',
                path='/'
            )
            
        return response
