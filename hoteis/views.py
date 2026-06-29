from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, date, timedelta
from django.db import models
from .models import Hotel, ParceiroUsuario, Reserva, Quarto, UnidadeQuarto, Tarefa, HospedeReserva, VeiculoReserva, ReservaLog, ProdutoConsumo, PedidoServico, ItemPedidoServico, HotelSecao, HotelSecaoItem, HotelImagem
from .utils import checar_disponibilidade_quarto, buscar_datas_proximas
from decimal import Decimal

class UnifiedPortalWrapper:
    def __init__(self, empresa, first_hotel):
        self.empresa = empresa
        self.first_hotel = first_hotel
        self.id = first_hotel.id # Resolves B2C detail redirect safely
        self.nome = empresa.nome_fantasia
        self.descricao = getattr(empresa, 'descricao_portal', '') or "Rede de Pousadas e Hospedagens."
        if not self.descricao:
            self.descricao = f"Conheça as acomodações do {empresa.nome_fantasia}."
        self.banner = empresa.banner or first_hotel.banner
        self.logo = empresa.logo or first_hotel.logo
        self.slug = empresa.slug
        self.sorting_id = first_hotel.id
        self.is_rede = True
        
        # Represent multiple locations
        hotéis = empresa.hoteis.filter(status='ativo')
        cidades = list(set(h.local.cidade for h in hotéis if h.local))
        estados = list(set(h.local.estado for h in hotéis if h.local))
        
        class LocalMock:
            def __init__(self, cidade, estado):
                self.nome = "Vários Destinos"
                self.cidade = cidade
                self.estado = estado
                self.endereco = "Vários Endereços"
        
        cidade_str = ", ".join(cidades) if cidades else "Serra da Ibiapaba"
        estado_str = ", ".join(estados) if estados else "CE"
        self.local = LocalMock(cidade_str, estado_str)

    @property
    def imagens(self):
        class AllMock:
            def all(self):
                return []
        return AllMock()


def home(request):
    # Se acessado via subdomínio de rede unificada, exibe o portal do grupo
    empresa_atual = getattr(request, 'empresa_atual', None)
    if empresa_atual:
        return portal_grupo(request)

    # Se acessado via subdomínio de hotel individual, exibe a vitrine B2C diretamente
    hotel_atual = getattr(request, 'hotel_atual', None)
    if hotel_atual:
        return vanity_url(request, slug=hotel_atual.slug)

    # Incrementa contador de visualizações global da plataforma
    from core.models import PlataformaConfig
    try:
        config = PlataformaConfig.get_solo()
        config.visualizacoes += 1
        config.save(update_fields=['visualizacoes'])
    except Exception:
        pass

    # Carrega slides do carrossel da home
    from .models import HomeSlide
    slides = list(HomeSlide.objects.filter(ativo=True))
    
    # Se não houver nenhum slide cadastrado, injeta fallbacks dinâmicos de alta definição
    if not slides:
        class MockSlide:
            def __init__(self, id, titulo, subtitulo, tipo_midia, imagem_url, video_url, data_texto, local_texto, texto_cta, link_cta):
                self.id = id
                self.titulo = titulo
                self.subtitulo = subtitulo
                self.tipo_midia = tipo_midia
                self.imagem_url = imagem_url
                self.video_url = video_url
                self.data_texto = data_texto
                self.local_texto = local_texto
                self.texto_cta = texto_cta
                self.link_cta = link_cta

            @property
            def banner(self):
                # Mock object helper to mimic banner.url interface
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.imagem_url) if self.imagem_url else None

            @property
            def hero_video(self):
                # Mock object helper to mimic hero_video.url interface
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.video_url) if self.video_url else None

        slides = [
            MockSlide(
                id=1,
                titulo="Viva a Essência da Serra da Ibiapaba",
                subtitulo="Descubra chalés rústicos, pousadas charmosas e resorts cercados pela natureza exuberante.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Temporada de Inverno",
                local_texto="Serra da Ibiapaba, CE",
                texto_cta="Explorar Hotéis",
                link_cta="/hotelaria/"
            ),
            MockSlide(
                id=2,
                titulo="Chalés Exclusivos com Vista Panorâmica",
                subtitulo="Aproveite o clima frio e aconchegante da serra em acomodações de alto padrão com todo o conforto.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Finais de Semana Especiais",
                local_texto="Tianguá, Ceará",
                texto_cta="Reservar Chalé",
                link_cta="/hotelaria/?tipo=chale"
            ),
            MockSlide(
                id=3,
                titulo="Refúgios & Pousadas Boutique de Luxo",
                subtitulo="Viva momentos inesquecíveis com experiências completas de bem-estar, lazer e alta gastronomia.",
                tipo_midia="imagem",
                imagem_url="https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=1920&q=80",
                video_url="",
                data_texto="Pacotes Exclusivos",
                local_texto="Ubajara, Ceará",
                texto_cta="Ver Pousadas",
                link_cta="/hotelaria/?tipo=pousada"
            )
        ]

    # Carrega cidades para o carrossel de cidades da Ibiapaba
    from .models import Cidade
    cidades = list(Cidade.objects.all())
    if not cidades:
        class MockCidade:
            def __init__(self, nome, slug, imagem_url, descricao=""):
                self.nome = nome
                self.slug = slug
                self.imagem_url = imagem_url
                self.descricao = descricao

            @property
            def imagem(self):
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.imagem_url)
                
        cidades = [
            MockCidade("Tianguá", "tiangua", "/static/images/cidades/tiangua.png", "Portal da Serra da Ibiapaba"),
            MockCidade("Ubajara", "ubajara", "/static/images/cidades/ubajara.png", "Cidade das Flores e Bondinho"),
            MockCidade("Viçosa do Ceará", "vicosa-do-ceara", "/static/images/cidades/vicosa.png", "Patrimônio Histórico e Cachaça Premium"),
            MockCidade("São Benedito", "sao-benedito", "/static/images/cidades/sao_benedito.png", "Capital das Rosas"),
            MockCidade("Guaraciaba do Norte", "guaraciaba-do-norte", "https://images.unsplash.com/photo-1498307818166-5248f52068f6?auto=format&fit=crop&w=800&q=80", "Polo Hortifrutigranjeiro"),
            MockCidade("Ipu", "ipu", "/static/images/cidades/ipu.png", "Bica do Ipu e Iracema"),
            MockCidade("Carnaubal", "carnaubal", "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?auto=format&fit=crop&w=800&q=80", "Belezas e Trilhas Ecológicas"),
            MockCidade("Croatá", "croata", "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80", "Acolhedora e Produtiva"),
            MockCidade("Ibiapina", "ibiapina", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80", "Cachoeiras e Clima Agradável")
        ]

    destaque = Hotel.objects.filter(destaque=True, status='ativo').first()
    
    # Agrupa hotéis com portal unificado em um único card de rede/empresa
    from core.models import Empresa
    from django.db.models import Q
    
    empresas_unificadas = Empresa.objects.filter(modalidade_portal='unificado', ativa=True)
    
    # Decoplar relação cruzada para evitar cross-database join
    empresas_individuais_ids = list(Empresa.objects.filter(
        Q(modalidade_portal='individual') | Q(modalidade_portal__isnull=True)
    ).values_list('id', flat=True))
    
    hoteis_individuais = Hotel.objects.filter(
        status='ativo'
    ).filter(
        Q(empresa_id__isnull=True) | Q(empresa_id__in=empresas_individuais_ids)
    )
    
    items = []
    for empresa in empresas_unificadas:
        first_hotel = empresa.hoteis.filter(status='ativo').first()
        if first_hotel:
            items.append(UnifiedPortalWrapper(empresa, first_hotel))
            
    for hotel in hoteis_individuais:
        items.append(hotel)
        
    # Ordena mantendo os itens estáveis com base no ID
    items.sort(key=lambda x: getattr(x, 'sorting_id', getattr(x, 'id', 0)))
    proximos = items[:16]
    
    # Carrega restaurantes para a seção B2C na Home do app de restaurantes
    from restaurantes.models import Restaurante as RealRestaurante
    restaurantes_reais = list(RealRestaurante.objects.filter(ativo=True)[:16])
    
    # Criamos os mocks para manter o grid preenchido se houverem menos de 8
    class MockRestaurante:
        def __init__(self, id, nome, especialidade, imagem_url, cidade_nome, endereco, whatsapp):
            self.id = id
            self.nome = nome
            self.especialidade = especialidade
            self.imagem_url = imagem_url
            self.cidade_nome = cidade_nome
            self.endereco = endereco
            self.whatsapp = whatsapp

        @property
        def imagem(self):
            class UrlHelper:
                def __init__(self, url):
                    self.url = url
            return UrlHelper(self.imagem_url) if self.imagem_url else None

    mocks = [
        MockRestaurante(
            id=101,
            nome="Cantina da Serra",
            especialidade="Massas & Vinho",
            imagem_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Tianguá",
            endereco="Av. Central, 120",
            whatsapp="88999990011"
        ),
        MockRestaurante(
            id=102,
            nome="Sabor da Terra",
            especialidade="Culinária Regional",
            imagem_url="https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Ubajara",
            endereco="Rua das Flores, 45",
            whatsapp="88999990022"
        ),
        MockRestaurante(
            id=103,
            nome="Pizzaria Bella Vista",
            especialidade="Pizzas no Forno a Lenha",
            imagem_url="https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Viçosa do Ceará",
            endereco="Mirante da Serra",
            whatsapp="88999990033"
        ),
        MockRestaurante(
            id=104,
            nome="Espaço Gourmet",
            especialidade="Carnes Nobres & Parrilla",
            imagem_url="https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",
            cidade_nome="São Benedito",
            endereco="Av. Pinheiro, 200",
            whatsapp="88999990044"
        ),
        MockRestaurante(
            id=105,
            nome="Serra Bistrô",
            especialidade="Gastronomia Contemporânea",
            imagem_url="https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Guaraciaba do Norte",
            endereco="Rua do Comércio, 88",
            whatsapp="88999990055"
        ),
        MockRestaurante(
            id=106,
            nome="Estação do Sabor",
            especialidade="Self-Service & Petiscos",
            imagem_url="https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Ipu",
            endereco="Praça de Fátima, 10",
            whatsapp="88999990066"
        ),
        MockRestaurante(
            id=107,
            nome="Café Colonial Ibiapaba",
            especialidade="Cafés & Doces Artesanais",
            imagem_url="https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Ibiapina",
            endereco="Av. Independência, 340",
            whatsapp="88999990077"
        ),
        MockRestaurante(
            id=108,
            nome="Churrascaria do Sol",
            especialidade="Rodízio Completo",
            imagem_url="https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80",
            cidade_nome="Croatá",
            endereco="BR-222, Km 10",
            whatsapp="88999990088"
        ),
    ]
    
    restaurantes = restaurantes_reais + mocks[:max(0, 8 - len(restaurantes_reais))]
    
    context = {
        'destaque': destaque,
        'proximos': proximos,
        'restaurantes': restaurantes,
        'slides': slides,
        'cidades': cidades,
    }
    return render(request, 'hoteis/home.html', context)


def cidade_detalhe(request, cidade_slug):
    """
    Exibe o portal de experiências B2C exclusivo de uma cidade da Ibiapaba.
    Exibe carrosséis temáticos para: Shows/Eventos, Pousadas, Restaurantes e Cinema.
    """
    from .models import Cidade, Hotel, Restaurante
    from eventos.models import Evento
    from cinema.models import Filme
    
    cidade = Cidade.objects.filter(slug=cidade_slug).first()
    
    # Fallback caso a cidade não exista no banco
    if not cidade:
        class MockCidade:
            def __init__(self, nome, slug, banner_url, descricao=""):
                self.nome = nome
                self.slug = slug
                self.banner_url = banner_url
                self.descricao = descricao

            @property
            def banner(self):
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.banner_url)

        # Determina os metadados de fallback com base no slug
        nome_cidade = cidade_slug.replace('-', ' ').title()
        banner_url = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1920&q=80"
        if cidade_slug == 'tiangua':
            nome_cidade = "Tianguá"
            banner_url = "/static/images/cidades/tiangua.png"
        elif cidade_slug == 'ubajara':
            nome_cidade = "Ubajara"
            banner_url = "/static/images/cidades/ubajara.png"
        elif cidade_slug == 'vicosa-do-ceara':
            nome_cidade = "Viçosa do Ceará"
            banner_url = "/static/images/cidades/vicosa.png"
        elif cidade_slug == 'sao-benedito':
            nome_cidade = "São Benedito"
            banner_url = "/static/images/cidades/sao_benedito.png"
        elif cidade_slug == 'ipu':
            nome_cidade = "Ipu"
            banner_url = "/static/images/cidades/ipu.png"
            
        cidade = MockCidade(
            nome=nome_cidade,
            slug=cidade_slug,
            banner_url=banner_url,
            descricao=f"Descubra o melhor de {nome_cidade}: shows imperdíveis, as melhores pousadas da serra, gastronomia e cinema."
        )

    # 1. Pousadas e Hotéis da Cidade (Reais com fallback dinâmico)
    pousadas = list(Hotel.objects.filter(local__cidade__iexact=cidade.nome, status='ativo'))
    if not pousadas:
        pousadas = Hotel.objects.filter(status='ativo')[:4]  # fallback com os hotéis ativos gerais
        
    # 2. Shows e Eventos (Reais com fallback dinâmico)
    shows = list(Evento.objects.filter(local_nome__icontains=cidade.nome).exclude(status__in=['cancelado', 'encerrado']))
    if not shows:
        # Cria eventos mockados dinâmicos e deslumbrantes específicos da cidade
        class MockEvento:
            def __init__(self, id, nome, descricao, banner_url, data_evento, local_nome):
                self.id = id
                self.nome = nome
                self.descricao = descricao
                self.banner_url = banner_url
                self.data_evento = data_evento
                self.local_nome = local_nome

            @property
            def banner(self):
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.banner_url)

        shows = [
            MockEvento(
                id=1,
                nome="Ibiapaba Jazz Festival",
                descricao="O maior festival de música instrumental da serra, reunindo artistas nacionais e internacionais.",
                banner_url="https://images.unsplash.com/photo-1511192336575-5a79af67a629?auto=format&fit=crop&w=800&q=80",
                data_evento=datetime.now() + timedelta(days=15),
                local_nome=f"Arena Central, {cidade.nome}"
            ),
            MockEvento(
                id=2,
                nome="Festival Gastronômico da Serra",
                descricao="Sabores regionais, oficinas culinárias com chefs renomados e apresentações culturais.",
                banner_url="https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80",
                data_evento=datetime.now() + timedelta(days=30),
                local_nome=f"Parque da Cidade, {cidade.nome}"
            )
        ]

    # 3. Restaurantes (Reais com fallback dinâmico)
    restaurantes = list(Restaurante.objects.filter(cidade_nome__iexact=cidade.nome, ativo=True))
    if not restaurantes:
        class MockRestaurante:
            def __init__(self, nome, especialidade, imagem_url, endereco, whatsapp):
                self.nome = nome
                self.especialidade = especialidade
                self.imagem_url = imagem_url
                self.endereco = endereco
                self.whatsapp = whatsapp

            @property
            def imagem(self):
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.imagem_url)

        restaurantes = [
            MockRestaurante(
                nome="Cantina da Serra",
                especialidade="Massas & Vinho",
                imagem_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
                endereco=f"Av. Central, 120 - {cidade.nome}",
                whatsapp="88999990011"
            ),
            MockRestaurante(
                nome="Sabor da Terra",
                especialidade="Culinária Regional",
                imagem_url="https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
                endereco=f"Rua das Flores, 45 - {cidade.nome}",
                whatsapp="88999990022"
            ),
            MockRestaurante(
                nome="Pizzaria Bella Vista",
                especialidade="Pizzas no Forno a Lenha",
                imagem_url="https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80",
                endereco=f"Mirante da Serra - {cidade.nome}",
                whatsapp="88999990033"
            )
        ]

    # 4. Cinema / Filmes em Cartaz no Cine Ibiapaba (Reais com fallback dinâmico)
    filmes = list(Filme.objects.filter(em_cartaz=True))
    if not filmes:
        class MockFilme:
            def __init__(self, titulo, genero, poster_url, duracao_minutos, classificacao_indicativa):
                self.titulo = titulo
                self.genero = genero
                self.poster_url = poster_url
                self.duracao_minutos = duracao_minutos
                self.classificacao_indicativa = classificacao_indicativa

            @property
            def poster(self):
                class UrlHelper:
                    def __init__(self, url):
                        self.url = url
                return UrlHelper(self.poster_url)

        filmes = [
            MockFilme(
                titulo="O Mistério da Serra",
                genero="Aventura / Suspense",
                poster_url="https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=800&q=80",
                duracao_minutos=110,
                classificacao_indicativa="12 anos"
            ),
            MockFilme(
                titulo="Coração de Criança",
                genero="Comédia / Família",
                poster_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80",
                duracao_minutos=95,
                classificacao_indicativa="Livre"
            ),
            MockFilme(
                titulo="Trilhas do Destino",
                genero="Drama / Romance",
                poster_url="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80",
                duracao_minutos=125,
                classificacao_indicativa="14 anos"
            )
        ]
        
    context = {
        'cidade': cidade,
        'pousadas': pousadas,
        'shows': shows,
        'restaurantes': restaurantes,
        'filmes': filmes,
    }
    return render(request, 'hoteis/cidade_detalhe.html', context)

@xframe_options_exempt
def detalhe(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    hotel.visualizacoes += 1
    hotel.save(update_fields=['visualizacoes'])
    
    # Incrementa visualizações da Empresa associada
    if hotel.empresa:
        hotel.empresa.visualizacoes += 1
        hotel.empresa.save(update_fields=['visualizacoes'])
    
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    # Seção de destaques personalizada
    destaques_personalizado = hotel.secoes.filter(tipo='destaques', ativa=True).first()
    
    # 3 quartos com mais visualizações (destaque) - Garantir exatamente 3 cards repetindo se houver menos
    quartos_destaque_qs = hotel.quartos.all().order_by('-visualizacoes')
    quartos_destaque = list(quartos_destaque_qs[:3])
    if len(quartos_destaque) > 0:
        while len(quartos_destaque) < 3:
            quartos_destaque.append(quartos_destaque[len(quartos_destaque) % len(quartos_destaque_qs)])
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'quartos_destaque': quartos_destaque,
        'imagens': imagens,
        'destaques_personalizado': destaques_personalizado,
    }
    return render(request, 'hoteis/detalhe.html', context)

@xframe_options_exempt
def vanity_url(request, slug):
    """
    Exibe a vitrine B2C pública do hotel a partir do seu slug customizado (vanity URL),
    ou o portal de rede unificado se o slug pertencer a uma empresa com portal unificado.
    """
    from core.models import Empresa
    empresa = Empresa.objects.filter(slug=slug, modalidade_portal='unificado').first()
    if empresa:
        return portal_grupo(request, slug=slug)

    hotel = get_object_or_404(Hotel, slug=slug)
    
    hotel.visualizacoes += 1
    hotel.save(update_fields=['visualizacoes'])
    
    # Incrementa visualizações da Empresa associada
    if hotel.empresa:
        hotel.empresa.visualizacoes += 1
        hotel.empresa.save(update_fields=['visualizacoes'])
    
    quartos = hotel.quartos.all()
    imagens = hotel.imagens.all()
    
    # Seção de destaques personalizada
    destaques_personalizado = hotel.secoes.filter(tipo='destaques', ativa=True).first()
    
    # 3 quartos com mais visualizações (destaque) - Garantir exatamente 3 cards repetindo se houver menos
    quartos_destaque_qs = hotel.quartos.all().order_by('-visualizacoes')
    quartos_destaque = list(quartos_destaque_qs[:3])
    if len(quartos_destaque) > 0:
        while len(quartos_destaque) < 3:
            quartos_destaque.append(quartos_destaque[len(quartos_destaque) % len(quartos_destaque_qs)])
    
    context = {
        'hotel': hotel,
        'quartos': quartos,
        'quartos_destaque': quartos_destaque,
        'imagens': imagens,
        'destaques_personalizado': destaques_personalizado,
    }
    return render(request, 'hoteis/detalhe.html', context)

def api_check_disponibilidade(request, hotel_id):
    checkin_str = request.GET.get('checkin')
    checkout_str = request.GET.get('checkout')
    
    if not checkin_str or not checkout_str:
        return JsonResponse({'error': 'Datas invalidas'}, status=400)
    
    try:
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato invalido'}, status=400)
        
    if checkout <= checkin:
        return JsonResponse({'error': 'Checkout deve ser depois de Checkin'}, status=400)
        
    noites = (checkout - checkin).days
    
    hotel = get_object_or_404(Hotel, id=hotel_id)
    resultado = []
    
    for quarto in hotel.quartos.all():
        disp = checar_disponibilidade_quarto(quarto, checkin, checkout)
        item = {
            'quarto_id': quarto.id,
            'disponivel': disp,
            'sugestao_antes': None,
            'sugestao_depois': None,
            'preco_total': float(quarto.preco * noites),
            'noites': noites
        }
        
        if not disp:
            ant, dep = buscar_datas_proximas(quarto, checkin, noites)
            if ant: item['sugestao_antes'] = ant.strftime('%Y-%m-%d')
            if dep: item['sugestao_depois'] = dep.strftime('%Y-%m-%d')
            
        resultado.append(item)
        
    return JsonResponse({'resultados': resultado})


def api_datas_ocupadas(request, hotel_id):
    """Retorna uma lista de datas em que TODOS os quartos do hotel estao indisponiveis."""
    mes_str = request.GET.get('mes')   # YYYY-MM
    if not mes_str:
        return JsonResponse({'error': 'Param mes obrigatorio'}, status=400)
    
    try:
        ano, mes = int(mes_str.split('-')[0]), int(mes_str.split('-')[1])
    except Exception:
        return JsonResponse({'error': 'Formato invalido. Use YYYY-MM'}, status=400)
    
    hotel = get_object_or_404(Hotel, id=hotel_id)
    quartos = list(hotel.quartos.all())
    
    # Primeiro e ultimo dia do mes
    primeiro = date(ano, mes, 1)
    if mes == 12:
        ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo = date(ano, mes + 1, 1) - timedelta(days=1)
    
    datas_ocupadas = []
    d = primeiro
    while d <= ultimo:
        checkout_d = d + timedelta(days=1)
        # Uma data e ocupada se nenhum quarto tem unidade livre
        todos_ocupados = all(
            not checar_disponibilidade_quarto(q, d, checkout_d)
            for q in quartos
        )
        if todos_ocupados:
            datas_ocupadas.append(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)
    
    return JsonResponse({'datas_ocupadas': datas_ocupadas})

def partner_auth(request):
    """
    Controla o login e a solicitação de parceria para donos e equipes de hotéis/pousadas.
    Usa HTMX para transições fluidas de tela inteira sem recarregamento.
    """
    from django.http import HttpResponse
    from django.urls import reverse
    
    is_htmx = request.headers.get('HX-Request') == 'true' or 'form' in request.GET
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_parceiro'):
            if is_htmx:
                response = HttpResponse()
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
        # Usuários logados como cliente comum não são redirecionados mais para poderem se logar como parceiros!

    # Se for requisição HTMX do tipo GET para trocar de formulário
    if request.method == 'GET' and is_htmx:
        form_type = request.GET.get('form', 'login')
        if form_type == 'register':
            return render(request, 'hoteis/auth/partner_register_form.html')
        return render(request, 'hoteis/auth/partner_login_form.html')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'login':
            username_or_email = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            # Tenta autenticar pelo username direto
            user = authenticate(request, username=username_or_email, password=password)
            
            # Se falhar, tenta autenticar buscando pelo e-mail
            if user is None and '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
                    
            if user is not None:
                # Checa se o usuário possui perfil de parceiro
                if hasattr(user, 'perfil_parceiro'):
                    perfil = user.perfil_parceiro
                    if perfil.ativo:
                        auth_login(request, user)
                        messages.success(request, f"Bem-vindo de volta, {user.first_name or user.username}!")
                        if is_htmx:
                            response = HttpResponse()
                            response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                            return response
                        return redirect('hoteis:partner_dashboard')
                    else:
                        msg = "Sua conta de parceiro está aguardando aprovação dos administradores."
                else:
                    msg = "Este portal é exclusivo para parceiros de hospedagem. Acesse a área de Clientes Comuns."
            else:
                msg = "Credenciais inválidas. Verifique seu login e senha."
                
            if is_htmx:
                # Retorna apenas o formulário com a mensagem de erro injetada
                context = {'error_message': msg, 'username_entered': username_or_email}
                return render(request, 'hoteis/auth/partner_login_form.html', context)
            else:
                messages.error(request, msg)
                
        elif action == 'register':
            nome_hotel = request.POST.get('nome_hotel', '').strip()
            tipo_hotel = request.POST.get('tipo_hotel', '').strip()
            cnpj = request.POST.get('cnpj', '').strip()
            responsavel = request.POST.get('responsavel_nome', '').strip()
            cpf = request.POST.get('responsavel_cpf', '').strip()
            email = request.POST.get('responsavel_email', '').strip()
            telefone = request.POST.get('responsavel_telefone', '').strip()
            username = request.POST.get('username_solicitado', '').strip()
            
            if nome_hotel and responsavel and email and telefone:
                if is_htmx:
                    context = {
                        'nome_hotel': nome_hotel,
                        'responsavel': responsavel,
                        'email': email,
                    }
                    return render(request, 'hoteis/auth/partner_register_success.html', context)
                else:
                    messages.success(request, "Solicitação de parceria enviada com sucesso! Nossa equipe analisará seus dados.")
            else:
                msg = "Preencha todos os campos obrigatórios para enviar a solicitação."
                if is_htmx:
                    context = {'error_message': msg}
                    return render(request, 'hoteis/auth/partner_register_form.html', context)
                else:
                    messages.error(request, msg)

    return render(request, 'hoteis/auth/partner_login.html')

@login_required(login_url='hoteis:partner_login')
@never_cache
def partner_dashboard(request):
    """
    O painel B2B adaptativo do parceiro hoteleiro.
    Renderiza informações financeiras, quartos, equipe, reservas e o módulo reativo de Atividades (Kanban & Calendário).
    """
    from django.db.models import Q
    import calendar as pycalendar
    
    if not hasattr(request.user, 'perfil_parceiro'):
        messages.error(request, "Acesso negado. Portal exclusivo para parceiros.")
        return redirect('clientes:painel')
        
    perfil = request.user.perfil_parceiro
    if not perfil.ativo:
        messages.error(request, "Sua conta está inativa ou pendente de aprovação.")
        return redirect('hoteis:partner_login')
        
    hotel = perfil.hotel
    hotel_imagens = list(hotel.imagens.all()[:10])
    galeria_slots = [hotel_imagens[i] if i < len(hotel_imagens) else None for i in range(10)]
    hoje = date.today()
    
    # Coleta de dados operacionais
    quartos = hotel.quartos.all()
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    secoes_qs = hotel.secoes.all().prefetch_related('itens')
    destaques_secao = secoes_qs.filter(tipo='destaques').first()
    secoes = secoes_qs.exclude(tipo='destaques')
    tem_destaques_personalizado = destaques_secao is not None

    # === CENTRAL DE HÓSPEDES & CONCIERGE ===
    from .models import ProdutoConsumo, PedidoServico
    hospedes_ativos = Reserva.objects.filter(unidade__quarto__hotel=hotel, status='hospedado').order_by('unidade__identificador')
    pedidos_ativos = PedidoServico.objects.filter(hotel=hotel).order_by('-criado_em')
    produtos_consumo = ProdutoConsumo.objects.filter(hotel=hotel, disponivel=True)

    # === SISTEMA DE ESTOQUE & ALMOXARIFADO ===
    from django.db.models import Sum
    from estoque.models import Produto, CategoriaProduto, Fornecedor, Compra, MovimentoEstoque
    produtos_estoque = Produto.objects.filter(hotel=hotel, ativo=True).select_related('categoria')
    categorias_estoque = CategoriaProduto.objects.filter(hotel=hotel)
    fornecedores_estoque = Fornecedor.objects.filter(hotel=hotel, ativo=True)
    compras_estoque = Compra.objects.filter(hotel=hotel).select_related('fornecedor').prefetch_related('itens__produto').order_by('-data_compra', '-criado_em')
    movimentos_estoque = MovimentoEstoque.objects.filter(hotel=hotel).select_related('produto').order_by('-criado_em')

    total_produtos = produtos_estoque.count()
    total_baixo_estoque = sum(1 for p in produtos_estoque if p.precisa_reposicao)
    total_venda = produtos_estoque.filter(finalidade__in=['venda', 'ambos']).count()
    total_interno = produtos_estoque.filter(finalidade__in=['interno', 'ambos']).count()

    total_compras = compras_estoque.count()
    total_compras_pendentes = compras_estoque.filter(status='pendente').count()
    total_compras_recebidas = compras_estoque.filter(status='recebida').count()
    valor_compras_mes = Compra.objects.filter(
        hotel=hotel, 
        status='recebida', 
        data_compra__month=hoje.month, 
        data_compra__year=hoje.year
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    # === SISTEMA DE RESERVAS & PMS GRID (CABANAS) ===
    # 1. Categoria selecionada (Quarto)
    quarto_id = request.GET.get('quarto_id')
    selected_quarto = None
    if quarto_id:
        try:
            selected_quarto = hotel.quartos.get(id=quarto_id)
        except Exception:
            pass
    if not selected_quarto:
        selected_quarto = hotel.quartos.first()
        
    # 2. Filtro de Período (Default: Hoje até hoje + 7 dias)
    data_inicio = hoje
    data_fim = hoje + timedelta(days=7)
    
    # Aceita params separados (novo) ou período unificado (legado)
    di_str = request.GET.get('data_inicio', '')
    df_str = request.GET.get('data_fim', '')
    periodo_str = request.GET.get('periodo', '')
    
    if di_str and df_str:
        try:
            data_inicio = datetime.strptime(di_str.strip(), '%Y-%m-%d').date()
            data_fim = datetime.strptime(df_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    elif periodo_str:
        try:
            if " to " in periodo_str:
                parts = periodo_str.split(" to ")
            elif " a " in periodo_str:
                parts = periodo_str.split(" a ")
            else:
                parts = [periodo_str]
                
            if len(parts) == 2:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        data_inicio = datetime.strptime(parts[0].strip(), fmt).date()
                        data_fim = datetime.strptime(parts[1].strip(), fmt).date()
                        break
                    except ValueError:
                        continue
            elif len(parts) == 1:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        data_inicio = datetime.strptime(parts[0].strip(), fmt).date()
                        data_fim = data_inicio
                        break
                    except ValueError:
                        continue
        except Exception:
            pass
            
    # 3. KPIs
    res_periodo = Reserva.objects.filter(
        unidade__quarto__hotel=hotel,
        data_checkin__lt=data_fim,
        data_checkout__gt=data_inicio
    ).exclude(status='cancelada')
    
    if selected_quarto:
        res_periodo_sel = res_periodo.filter(unidade__quarto=selected_quarto)
    else:
        res_periodo_sel = res_periodo.none()
        
    ativos_qtd = res_periodo_sel.count()
    hospedados_qtd = res_periodo_sel.filter(status='hospedado').aggregate(models.Sum('quantidade_hospedes'))['quantidade_hospedes__sum'] or 0
    pendentes_qtd = res_periodo_sel.filter(data_checkin__gte=data_inicio, data_checkin__lte=data_fim, status__in=['confirmada', 'pendente']).count()
    
    # 4. Colunas de Quarto Físico (Cabanas)
    # 4. Colunas de Quarto Físico (Cabanas & Gantt Timeline)
    dias_gantt = []
    curr = data_inicio
    for _ in range(7):
        dias_gantt.append(curr)
        curr += timedelta(days=1)

    unidades_data = []
    if selected_quarto:
        for uni in selected_quarto.unidades.filter(ativa=True):
            res_uni = Reserva.objects.filter(
                unidade=uni,
                data_checkin__lt=data_fim,
                data_checkout__gt=data_inicio
            ).exclude(status='cancelada').order_by('data_checkin')
            
            reservas_list = []
            for r in res_uni:
                start_date = max(r.data_checkin, data_inicio)
                end_date = min(r.data_checkout, data_fim)
                dias_exibidos = (end_date - start_date).days
                if dias_exibidos <= 0:
                    dias_exibidos = 1
                offset_days = (start_date - data_inicio).days
                
                r.gantt_left = offset_days * 14.2857
                r.gantt_width = dias_exibidos * 14.2857
                r.gantt_continua_antes = r.data_checkin < data_inicio
                r.gantt_continua_depois = r.data_checkout > data_fim
                reservas_list.append(r)
                
            unidades_data.append({
                'unidade': uni,
                'reservas': reservas_list
            })
    
    # Tarefas Reais
    tarefas_qs = Tarefa.objects.filter(hotel=hotel).select_related('responsavel', 'unidade', 'unidade__quarto').prefetch_related('responsavel__user')
    
    # Divisão por colunas Kanban
    overdue = tarefas_qs.filter(data_vencimento__lt=hoje).exclude(status='done').order_by('data_vencimento')
    todo = tarefas_qs.filter(status='todo').filter(Q(data_vencimento__gte=hoje) | Q(data_vencimento__isnull=True)).order_by('prioridade')
    doing = tarefas_qs.filter(status='doing').filter(Q(data_vencimento__gte=hoje) | Q(data_vencimento__isnull=True)).order_by('prioridade')
    done = tarefas_qs.filter(status='done').order_by('-atualizado_em')
    
    # Geração de Calendário
    try:
        mes_atual = int(request.GET.get('mes', hoje.month))
        ano_atual = int(request.GET.get('ano', hoje.year))
    except ValueError:
        mes_atual = hoje.month
        ano_atual = hoje.year
        
    if mes_atual == 1:
        mes_ant, ano_ant = 12, ano_atual - 1
    else:
        mes_ant, ano_ant = mes_atual - 1, ano_atual
        
    if mes_atual == 12:
        mes_prox, ano_prox = 1, ano_atual + 1
    else:
        mes_prox, ano_prox = mes_atual + 1, ano_atual
        
    meses_nomes = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    nome_mes = meses_nomes.get(mes_atual, "Mês")
    
    cal = pycalendar.Calendar(firstweekday=6) # Domingo
    semanas_matriz = cal.monthdatescalendar(ano_atual, mes_atual)
    
    dias_calendario = []
    for semana in semanas_matriz:
        semana_dias = []
        for d in semana:
            tarefas_do_dia = [t for t in tarefas_qs if t.data_vencimento == d]
            semana_dias.append({
                'dia': d.day,
                'data': d,
                'is_current_month': d.month == mes_atual,
                'is_today': d == hoje,
                'tarefas_preview': tarefas_do_dia[:2],
                'mais_tarefas': max(0, len(tarefas_do_dia) - 2)
            })
        dias_calendario.append(semana_dias)
        
    # === KPI FINANCEIRO REAL & ESTATÍSTICA HOTELEIRA ===
    from financeiro.models import TransacaoFinanceira
    
    # 1. Obter lançamentos contábeis reais do banco de dados
    transacoes_qs = TransacaoFinanceira.objects.filter(hotel=hotel)
    financeiro_lancamentos = transacoes_qs.order_by('-data', '-criado_em')[:50]
    
    faturamento_total = transacoes_qs.filter(tipo='receita').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    despesas_total = transacoes_qs.filter(tipo='despesa').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    lucro_total = faturamento_total - despesas_total
    
    # 2. Métricas de Performance Hoteleira (ADR, RevPAR, Ocupação)
    unidades_count = max(1, UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True).count())
    occupied_nights = Reserva.objects.filter(unidade__quarto__hotel=hotel, status__in=['hospedado', 'concluido']).count()
    diarias_faturamento = transacoes_qs.filter(categoria='diarias').aggregate(models.Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    if occupied_nights > 0:
        adr = diarias_faturamento / Decimal(occupied_nights)
    else:
        adr = Decimal('0.00')
    # RevPAR baseado no faturamento total de diárias dos últimos 30 dias distribuído pela capacidade mestre
    revpar = diarias_faturamento / Decimal(unidades_count * 30)
    
    reservas_hospedadas_count = Reserva.objects.filter(unidade__quarto__hotel=hotel, status='hospedado').count()
    taxa_ocupacao = min(100, int((reservas_hospedadas_count / unidades_count) * 100))
    
    # 3. Algoritmo de Ocupação & Forecasting de Faturamento Futuro (Projeção 12 dias para o Chart.js B2B)
    forecast_labels = []
    forecast_values = []
    current_projected = faturamento_total # Parte do acumulado real do caixa atual
    
    for i in range(12):
        dia = hoje + timedelta(days=i)
        # Filtra reservas cujas estadas ativas cobrem o dia projetado
        dia_reservas = Reserva.objects.filter(
            unidade__quarto__hotel=hotel,
            data_checkin__lte=dia,
            data_checkout__gt=dia,
            status__in=['confirmada', 'hospedado']
        )
        dia_faturamento = Decimal('0.00')
        for r in dia_reservas:
            duracao = max(1, (r.data_checkout - r.data_checkin).days)
            dia_faturamento += Decimal(r.valor_total) / duracao
            
        current_projected += dia_faturamento
        forecast_labels.append(dia.strftime('%d/%m'))
        forecast_values.append(float(current_projected))
        
    context = {
        'perfil': perfil,
        'hotel': hotel,
        'quartos': quartos,
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        
        # Dados Financeiros Reais
        'financeiro': financeiro_lancamentos,
        'faturamento_total': faturamento_total,
        'despesas_total': despesas_total,
        'lucro_total': lucro_total,
        
        # Métricas de Inteligência SaaS
        'adr': adr,
        'revpar': revpar,
        'taxa_ocupacao': taxa_ocupacao,
        'forecast_labels': forecast_labels,
        'forecast_values': forecast_values,
        
        # Atividades Kanban & Calendário:
        'overdue': overdue,
        'todo': todo,
        'doing': doing,
        'done': done,
        'nome_mes': nome_mes,
        'ano_atual': ano_atual,
        'mes_ant': mes_ant,
        'ano_ant': ano_ant,
        'mes_prox': mes_prox,
        'ano_prox': ano_prox,
        'dias_calendario': dias_calendario,
        
        # Reservas B2B PMS:
        'selected_quarto': selected_quarto,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'periodo_str': periodo_str,
        'ativos_qtd': ativos_qtd,
        'hospedados_qtd': hospedados_qtd,
        'pendentes_qtd': pendentes_qtd,
        'unidades_data': unidades_data,
        'dias_gantt': dias_gantt,
        
        # Central de Hóspedes & Pedidos B2B:
        'hospedes_ativos': hospedes_ativos,
        'pedidos_ativos': pedidos_ativos,
        'produtos_consumo': produtos_consumo,
        
        # Módulo de Estoque e Almoxarifado B2B:
        'produtos_estoque': produtos_estoque,
        'categorias_estoque': categorias_estoque,
        'fornecedores_estoque': fornecedores_estoque,
        'compras_estoque': compras_estoque,
        'movimentos_estoque': movimentos_estoque,
        'total_produtos': total_produtos,
        'total_baixo_estoque': total_baixo_estoque,
        'total_venda': total_venda,
        'total_interno': total_interno,
        'total_compras': total_compras,
        'total_compras_pendentes': total_compras_pendentes,
        'total_compras_recebidas': total_compras_recebidas,
        'valor_compras_mes': valor_compras_mes,
        'secoes': secoes,
        'destaques_secao': destaques_secao,
        'tem_destaques_personalizado': tem_destaques_personalizado,
        'galeria_slots': galeria_slots,
    }
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    view_type = request.GET.get('view')
    
    if is_htmx and view_type == 'calendario':
        return render(request, 'hoteis/atividades/partials/calendario.html', context)
    elif is_htmx and view_type == 'kanban':
        return render(request, 'hoteis/atividades/partials/kanban.html', context)
    elif is_htmx and view_type == 'reservas_grid':
        return render(request, 'hoteis/partials/reservas_grid.html', context)
        
    return render(request, 'hoteis/partner_dashboard.html', context)


def partner_logout(request):
    """
    Desloga o parceiro de hospedagem.
    """
    auth_logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('hoteis:partner_login')


def hotelaria(request):
    """
    Portal B2C dinâmico de Hotelaria do Naviê Vibe.
    Lista todas as pousadas, hotéis, chalés e resorts, com busca e filtros de categoria.
    """
    busca = request.GET.get('busca', '').strip()
    tipo = request.GET.get('tipo', '').strip()  # 'hotel', 'pousada', 'chale', 'resort'
    
    from core.models import Empresa
    from django.db.models import Q
    
    # 1. Filtra as empresas unificadas ativas
    empresas_qs = Empresa.objects.filter(modalidade_portal='unificado', ativa=True).prefetch_related('hoteis', 'hoteis__quartos')
    if busca:
        empresas_qs = empresas_qs.filter(
            Q(nome_fantasia__icontains=busca) | Q(razao_social__icontains=busca)
        )
        
    # 2. Filtra os hotéis individuais ativos (excluindo os que fazem parte de rede unificada)
    empresas_individuais_ids = list(Empresa.objects.filter(
        Q(modalidade_portal='individual') | Q(modalidade_portal__isnull=True)
    ).values_list('id', flat=True))
    
    hoteis_qs = Hotel.objects.filter(status='ativo').select_related('local').prefetch_related('imagens', 'quartos')
    hoteis_qs = hoteis_qs.filter(
        Q(empresa_id__isnull=True) | Q(empresa_id__in=empresas_individuais_ids)
    )
    if busca:
        hoteis_qs = hoteis_qs.filter(
            Q(nome__icontains=busca) | 
            Q(local__cidade__icontains=busca) | 
            Q(descricao__icontains=busca)
        )
        
    hoteis_list = []
    
    # Adiciona as redes unificadas
    for empresa in empresas_qs:
        first_hotel = empresa.hoteis.filter(status='ativo').first()
        if not first_hotel:
            continue
            
        wrapper = UnifiedPortalWrapper(empresa, first_hotel)
        
        # Encontra a menor diária da rede
        preco_minimo = None
        all_quartos = []
        for h in empresa.hoteis.filter(status='ativo'):
            all_quartos.extend(list(h.quartos.all()))
        if all_quartos:
            preco_minimo = min(q.preco for q in all_quartos)
            
        # Classifica redes como pousada por padrão para corresponder a filtros comuns
        h_type = 'pousada'
        h_type_label = 'Rede'
        
        if tipo and h_type != tipo:
            continue
            
        hoteis_list.append({
            'object': wrapper,
            'tipo': h_type,
            'tipo_label': h_type_label,
            'preco_minimo': preco_minimo,
        })
        
    # Adiciona os hotéis individuais
    for hotel in hoteis_qs:
        name_lower = hotel.nome.lower()
        desc_lower = hotel.descricao.lower()
        
        if 'pousada' in name_lower or 'pousada' in desc_lower:
            h_type = 'pousada'
            h_type_label = 'Pousada'
        elif 'chalé' in name_lower or 'chale' in name_lower or 'chalé' in desc_lower or 'chale' in desc_lower:
            h_type = 'chale'
            h_type_label = 'Chalé'
        elif 'resort' in name_lower or 'resort' in desc_lower:
            h_type = 'resort'
            h_type_label = 'Resort'
        else:
            h_type = 'hotel'
            h_type_label = 'Hotel'
            
        if tipo and h_type != tipo:
            continue
            
        preco_minimo = None
        quartos = hotel.quartos.all()
        if quartos.exists():
            preco_minimo = min(q.preco for q in quartos)
            
        hoteis_list.append({
            'object': hotel,
            'tipo': h_type,
            'tipo_label': h_type_label,
            'preco_minimo': preco_minimo,
        })
        
    context = {
        'hoteis': hoteis_list,
        'busca': busca,
        'tipo': tipo,
    }
    return render(request, 'hoteis/hotelaria.html', context)


@login_required(login_url='hoteis:partner_login')
def ia_enviar_chat(request):
    """
    Assistant Naviê AI B2B - Conversational Task & Room Operations Engine.
    ---------------------------------------------------------------------
    This controller receives a natural-language POST query from the hotel B2B interface 
    and simulates a fully autonomous, context-aware AI assistant. It actively parses 
    user intents to read, schedule, and complete operational hotel tasks, manage room status 
    (cleaning, maintenance, block/unblock), check room availability, create walk-in bookings, 
    and perform checkouts directly in the SQLite database.
    
    INTENTS PARSED:
    1. Room Status / Availability Query ('livre', 'disponiv', 'ocupad', 'vago', 'status', 'quartos', 'como estão', 'situação')
       - Lists all rooms with their respective statuses (Livre, Ocupado, Limpeza, Indisponível), or detail for a specific room.
    2. Room Checkout ('checkout', 'check-out', 'fechar conta', 'saída', 'saida')
       - Marks the active hosted reservation for a unit as completed.
    3. Block Room for Maintenance/Cleaning ('bloquear', 'interditar', 'indisponibilizar', 'indisponivel', 'indisponível')
       - Sets availability to False, assigns a reason, and spawns the corresponding task.
    4. Release Room ('liberar', 'desbloquear', 'disponibilizar', 'tornar disponível', 'tornar disponivel', 'ativar quarto')
       - Sets availability to True, clears reasons, and completes active operational tasks for that room.
    5. Book Room / Create Walk-in Reservation ('reservar', 'reserva', 'marcar hospedagem', 'agendar hospedagem', 'fazer reserva', 'nova reserva')
       - Extracts guest name, dates (checkin/checkout), computes total price from base rates, creates walk-in Reserva and ReservaLog.
    6. Move/Update Task Status ('conclua', 'concluir', 'feita', 'feito', 'pronto', 'concluída', 'mudar', 'alterar', 'atualizar', 'status', 'fazendo', 'progresso', 'fazer')
       - Extracts task ID and updates status to todo, doing, or done.
    7. Create Task ('criar', 'adicionar', 'marcar', 'atribuir', 'agendar')
       - Spawns operational task for the staff, mapping dates, responsible team member, and room unit.
    8. List Tasks ('listar', 'lista', 'tarefa', 'afazeres', 'pendente', 'hoje', 'urgente')
       - Retrieves list of tasks with filters (e.g. today, high priority).
       
    INPUTS:
    - request: HttpRequest object
    - request.POST.get('mensagem'): String command in Portuguese
    
    RETURNS:
    - HttpResponse rendering 'hoteis/ia_chat_response.html' with parsed string 'resposta_ia'
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado: Perfil de parceiro não encontrado.", status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method != 'POST':
        return redirect('hoteis:partner_dashboard')
        
    original_msg = request.POST.get('mensagem', '').strip()
    mensagem = original_msg.lower()
    
    import re
    from datetime import date, timedelta, datetime
    from django.utils import timezone
    from .models import Tarefa, UnidadeQuarto, ParceiroUsuario, Reserva, ReservaLog, HospedeReserva
    
    resposta = ""
    action_performed = False

    def formatar_quartos_grouped(unidades_list, hotel_nome, titulo_msg):
        from collections import defaultdict
        by_quarto = defaultdict(list)
        for u in unidades_list:
            by_quarto[u.quarto].append(u)
            
        html = f"{titulo_msg}<br>"
        html += '<div class="space-y-3 mt-3 w-full">'
        
        for q, units in by_quarto.items():
            units_sorted = sorted(units, key=lambda x: x.identificador)
            primeira_img = q.imagens.first()
            if primeira_img and primeira_img.url_imagem:
                img_url = primeira_img.url_imagem.url
            else:
                nome_lc = q.nome.lower()
                if any(k in nome_lc for k in ['single', 'solteiro', 'individual']):
                    img_url = "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=200&auto=format&fit=crop&q=60"
                elif any(k in nome_lc for k in ['casal', 'master', 'double', 'premium']):
                    img_url = "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=200&auto=format&fit=crop&q=60"
                else:
                    img_url = "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=200&auto=format&fit=crop&q=60"
                    
            html += f"""
            <div class="p-3 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/40 dark:border-white/5 flex items-start gap-3 text-left w-full shadow-sm">
                <img src="{img_url}" class="w-12 h-12 rounded-xl object-cover shrink-0 border border-slate-200/30 dark:border-white/10" alt="{q.nome}">
                <div class="flex-1 min-w-0">
                    <h4 class="text-xs font-black text-slate-800 dark:text-white uppercase tracking-wider truncate">{q.nome}</h4>
                    <p class="text-[9px] text-slate-400 dark:text-navie-textsec mt-0.5 leading-none">Diária: R$ {q.preco:.2f} • {q.capacidade_pessoas} {'pessoa' if q.capacidade_pessoas == 1 else 'pessoas'}</p>
                    <div class="flex flex-wrap gap-1.5 mt-2">
            """
            
            for u in units_sorted:
                st = u.status_mapa
                if st == 'livre':
                    pill_class = "bg-emerald-500/10 dark:bg-emerald-500/20 border-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                    title_tooltip = "Livre - Pronto para receber hóspedes"
                elif st == 'ocupado':
                    pill_class = "bg-rose-500/10 dark:bg-rose-500/20 border-rose-500/20 text-rose-600 dark:text-rose-400"
                    res = u.reserva_ativa
                    hospede = res.hospede_nome if res and res.hospede_nome else "Hóspede"
                    checkout_date_str = res.data_checkout.strftime('%d/%m/%Y') if res and res.data_checkout else ""
                    title_tooltip = f"Ocupado por {hospede} (Checkout: {checkout_date_str})" if checkout_date_str else f"Ocupado por {hospede}"
                elif st == 'limpeza':
                    pill_class = "bg-amber-500/10 dark:bg-amber-500/20 border-amber-500/20 text-amber-600 dark:text-amber-400"
                    title_tooltip = "Limpeza - Aguardando higienização"
                else:
                    pill_class = "bg-slate-500/10 dark:bg-slate-500/20 border-slate-300 dark:border-white/10 text-slate-600 dark:text-slate-400"
                    motivo_str = u.get_motivo_indisponivel_display() if u.motivo_indisponivel else "Bloqueado"
                    justif = u.justificativa_indisponivel or "Bloqueio operacional"
                    title_tooltip = f"{motivo_str} - {justif}"
                    
                html += f"""
                        <span class="px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider shrink-0 cursor-help transition-all hover:scale-105 {pill_class}" title="{title_tooltip}">
                            {u.identificador}
                        </span>
                """
                
            html += """
                    </div>
                </div>
            </div>
            """
            
        html += '</div>'
        return html

    # -------------------------------------------------------------
    # INTENT DETECTIONS
    # -------------------------------------------------------------
    
    # Determine if it's a task status update
    # Needs to match status keywords, containing a number (task ID) and NOT containing room operations keywords
    id_match = re.search(r'(?:tarefa\s+)?#?(\d+)', mensagem)
    is_task_status_update = False
    if id_match:
        # If it explicitly says 'tarefa' or if no room indicators are present in the text
        if 'tarefa' in mensagem or not any(r in mensagem for r in ['quarto', 'suite', 'suíte', 'chale', 'chalé', 'reserva', 'checkout', 'check-out', 'bloquear', 'liberar', 'desbloquear']):
            is_task_status_update = any(k in mensagem for k in ['conclua', 'concluir', 'feita', 'feito', 'pronto', 'concluída', 'mudar', 'alterar', 'atualizar', 'status', 'fazendo', 'progresso', 'fazer'])

    # 1. Task Status Update
    if is_task_status_update:
        task_id = int(id_match.group(1))
        tarefa = Tarefa.objects.filter(id=task_id, hotel=hotel).first()
        if tarefa:
            novo_status = None
            status_label = ""
            if any(k in mensagem for k in ['conclu', 'feita', 'feito', 'pronto', 'done']):
                novo_status = 'done'
                status_label = 'Concluído'
            elif any(k in mensagem for k in ['fazendo', 'progresso', 'doing']):
                novo_status = 'doing'
                status_label = 'Em Progresso'
            elif any(k in mensagem for k in ['fazer', 'todo', 'pendente']):
                novo_status = 'todo'
                status_label = 'A Fazer'
            
            if novo_status:
                tarefa.status = novo_status
                tarefa.save()
                action_performed = True
                resposta = f"Com certeza! Atualizei com sucesso o status da tarefa **#{tarefa.id} - {tarefa.titulo}** para **{status_label}** no banco de dados. *(Dica: Recarregue a página para atualizar o painel!)*"
            else:
                resposta = f"Encontrei a tarefa **#{tarefa.id} - {tarefa.titulo}** (Status atual: {tarefa.get_status_display()}). Qual status deseja definir? (A Fazer, Em Progresso ou Concluído)"
        else:
            resposta = f"Desculpe, não encontrei nenhuma tarefa com o ID **#{task_id}** vinculada à pousada **{hotel.nome}**."

    # 2. Room Checkout
    elif any(k in mensagem for k in ['checkout', 'check-out', 'fechar conta', 'saída', 'saida']) and any(r in mensagem for r in ['quarto', 'suite', 'suíte', 'chale', 'chalé', 'unidade']):
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                reserva = unidade.reserva_ativa
                if reserva:
                    reserva.status = 'concluido'
                    reserva.checkout_realizado_em = timezone.now()
                    reserva.save()
                    
                    ReservaLog.objects.create(
                        reserva=reserva,
                        usuario=request.user,
                        acao='checkout',
                        detalhes=f"Check-out realizado via assistente virtual Naviê AI pelo usuário {request.user.username}."
                    )
                    
                    if not Tarefa.objects.filter(reserva=reserva, titulo__icontains="Limpeza").exists():
                        Tarefa.objects.create(
                            hotel=hotel,
                            titulo=f"Limpeza e Preparação - {unidade.identificador}",
                            descricao=f"Realizar limpeza pós-checkout da reserva #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}.",
                            prioridade='alta',
                            status='todo',
                            unidade=unidade,
                            reserva=reserva
                        )
                    
                    action_performed = True
                    resposta = f"Check-out da acomodação **{unidade.identificador}** (hóspede **{reserva.hospede_nome}**) concluído com sucesso! Uma tarefa de limpeza pós-checkout foi aberta para a equipe. *(Dica: Recarregue a página para atualizar o painel!)*"
                else:
                    resposta = f"O **{unidade.identificador}** não possui nenhuma reserva ativa (hospedado) no momento para fazer check-out."
            else:
                resposta = f"Não encontrei a acomodação **{quarto_num}** cadastrada na pousada **{hotel.nome}**."
        else:
            resposta = "Para fazer check-out de um quarto, por favor informe o número ou identificador dele. Exemplo: *'Checkout do quarto 101'*."

    # 3. Block Room / Set Unavailable
    elif any(k in mensagem for k in ['bloquear', 'interditar', 'indisponibilizar', 'indisponivel', 'indisponível']):
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                unidade.disponivel = False
                motivo = 'outro'
                motivo_desc = "Serviço Operacional"
                
                if any(k in mensagem for k in ['manutenção', 'manutencao', 'conserto', 'reparo', 'quebrado', 'vazamento', 'manut', 'amnut', 'anuten', 'manten', 'maten']):
                    motivo = 'manutencao'
                    motivo_desc = "Manutenção"
                elif any(k in mensagem for k in ['limpeza', 'sujo', 'higieniza', 'limpa', 'limpez', 'faxina']):
                    motivo = 'limpeza'
                    motivo_desc = "Limpeza"
                
                unidade.motivo_indisponivel = motivo
                
                justificativa = ""
                quote_match = re.findall(r'"([^"]*)"', original_msg)
                if quote_match:
                    justificativa = quote_match[0].strip()
                else:
                    reason_match = re.search(r'(?:por|motivo|justificativa|devido a|de)\s+([^.\n]+)', mensagem)
                    if reason_match:
                        justificativa = reason_match.group(1).strip()
                
                unidade.justificativa_indisponivel = justificativa or "Bloqueio solicitado via chat Naviê AI."
                unidade.save()
                
                # Create corresponding Task
                if motivo == 'limpeza':
                    if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Limpeza').exists():
                        Tarefa.objects.create(
                            hotel=hotel,
                            titulo=f"Limpeza e Higienização - {unidade.identificador}",
                            descricao=unidade.justificativa_indisponivel,
                            prioridade='normal',
                            status='todo',
                            unidade=unidade
                        )
                elif motivo == 'manutencao':
                    if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Manutenção').exists():
                        Tarefa.objects.create(
                            hotel=hotel,
                            titulo=f"Manutenção e Reparos - {unidade.identificador}",
                            descricao=unidade.justificativa_indisponivel,
                            prioridade='alta',
                            status='todo',
                            unidade=unidade
                        )
                else:
                    if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Serviço Operacional').exists():
                        Tarefa.objects.create(
                            hotel=hotel,
                            titulo=f"Serviço Operacional - {unidade.identificador}",
                            descricao=unidade.justificativa_indisponivel,
                            prioridade='normal',
                            status='todo',
                            unidade=unidade
                        )
                
                action_performed = True
                resposta = f"Ok! O **{unidade.identificador}** foi bloqueado para **{motivo_desc}** no sistema.<br>Justificativa: *\"{unidade.justificativa_indisponivel}\"*.<br>*(Dica: Recarregue a página para atualizar o painel!)*"
            else:
                resposta = f"Desculpe, não encontrei a acomodação **{quarto_num}** na pousada **{hotel.nome}**."
        else:
            resposta = "Para bloquear um quarto, por favor informe o número ou identificador dele. Exemplo: *'Bloquear o quarto 101 por manutenção'*."

    # 4. Release Room / Make Available
    elif any(k in mensagem for k in ['liberar', 'desbloquear', 'disponibilizar', 'tornar disponível', 'tornar disponivel', 'ativar quarto']):
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                unidade.disponivel = True
                unidade.motivo_indisponivel = None
                unidade.justificativa_indisponivel = None
                unidade.save()
                
                # Complete operational tasks linked to this unit
                Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing']).update(status='done')
                
                action_performed = True
                resposta = f"Excelente! O **{unidade.identificador}** foi liberado e está marcado como **Livre/Disponível**. As tarefas operacionais pendentes deste quarto foram concluídas. *(Dica: Recarregue a página para atualizar o painel!)*"
            else:
                resposta = f"Não encontrei a acomodação **{quarto_num}** cadastrada na pousada **{hotel.nome}**."
        else:
            resposta = "Para liberar um quarto, por favor informe o número ou identificador dele. Exemplo: *'Liberar o quarto 102'*."

    # 5. Room Booking / Create Walk-in Reservation
    elif any(k in mensagem for k in ['reservar', 'reserva', 'marcar hospedagem', 'agendar hospedagem', 'fazer reserva', 'nova reserva']):
        hospede_nome = "Hóspede Avulso"
        quotes = re.findall(r'"([^"]*)"', original_msg)
        if len(quotes) >= 1:
            hospede_nome = quotes[0].strip()
        else:
            name_match = re.search(r'(?:para|nome de|hóspede|hospede)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', original_msg)
            if name_match:
                hospede_nome = name_match.group(1).strip()
            else:
                name_match_lc = re.search(r'(?:para|nome de|hóspede|hospede)\s+([a-zà-ú\s]+?)(?=\s+(?:de|do|desde|dia|em|no|com|q|$))', mensagem)
                if name_match_lc:
                    hospede_nome = name_match_lc.group(1).strip().title()
        
        # Parse Dates
        dates_found = []
        # YYYY-MM-DD
        for d_str in re.findall(r'(\d{4}-\d{2}-\d{2})', mensagem):
            try:
                dates_found.append(datetime.strptime(d_str, '%Y-%m-%d').date())
            except ValueError:
                pass
        # DD/MM/YYYY
        for d_str in re.findall(r'(\d{2}/\d{2}/\d{4})', mensagem):
            try:
                dates_found.append(datetime.strptime(d_str, '%d/%m/%Y').date())
            except ValueError:
                pass
        # DD/MM
        if len(dates_found) < 2:
            for d_str in re.findall(r'\b(\d{1,2})/(\d{1,2})\b', mensagem):
                day = int(d_str[0])
                month = int(d_str[1])
                current_year = date.today().year
                try:
                    parsed_date = date(current_year, month, day)
                    if parsed_date not in dates_found:
                        dates_found.append(parsed_date)
                except ValueError:
                    pass
        
        # Relative shifts
        if len(dates_found) < 2:
            if 'hoje' in mensagem:
                d = date.today()
                if d not in dates_found:
                    dates_found.append(d)
            if 'amanhã' in mensagem or 'amanha' in mensagem:
                d = date.today() + timedelta(days=1)
                if d not in dates_found:
                    dates_found.append(d)
        
        dates_found = sorted(list(set(dates_found)))
        
        if len(dates_found) >= 2:
            checkin_date = dates_found[0]
            checkout_date = dates_found[1]
        elif len(dates_found) == 1:
            checkin_date = dates_found[0]
            checkout_date = checkin_date + timedelta(days=1)
        else:
            checkin_date = date.today()
            checkout_date = checkin_date + timedelta(days=1)
            
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                preco_diaria = unidade.quarto.preco
                noites = (checkout_date - checkin_date).days
                if noites <= 0:
                    noites = 1
                
                valor_total = preco_diaria * noites
                if unidade.quarto.tem_desconto_multidias and noites >= unidade.quarto.dias_minimos_desconto:
                    desconto = (unidade.quarto.percentual_desconto / 100) * valor_total
                    valor_total -= desconto
                
                res_status = 'confirmada'
                if checkin_date <= date.today() and checkout_date > date.today():
                    res_status = 'hospedado'
                    
                reserva = Reserva.objects.create(
                    unidade=unidade,
                    data_checkin=checkin_date,
                    data_checkout=checkout_date,
                    subtotal=preco_diaria * noites,
                    taxas=0.00,
                    valor_total=valor_total,
                    status=res_status,
                    canal_venda='walk-in',
                    hospede_nome=hospede_nome,
                    quantidade_hospedes=1
                )
                
                HospedeReserva.objects.create(
                    reserva=reserva,
                    ordem=1,
                    nome=hospede_nome
                )
                
                ReservaLog.objects.create(
                    reserva=reserva,
                    usuario=request.user,
                    acao='criar',
                    detalhes=f"Reserva walk-in criada via assistente virtual Naviê AI pelo usuário {request.user.username}."
                )
                
                action_performed = True
                resposta = f"Sucesso! Criei uma reserva **{reserva.canal_venda.title()}** para **{hospede_nome}**:<br>" \
                           f"• Acomodação: **{unidade.identificador}** ({unidade.quarto.nome})<br>" \
                           f"• Período: **{checkin_date.strftime('%d/%m/%Y')}** a **{checkout_date.strftime('%d/%m/%Y')}** ({noites} noites)<br>" \
                           f"• Valor Total: **R$ {valor_total:.2f}**<br>" \
                           f"• Status: **{reserva.get_status_display()}**<br>" \
                           f"*(Dica: Recarregue a página para ver a reserva no seu mapa de quartos!)*"
            else:
                resposta = f"Não encontrei o quarto/acomodação **{quarto_num}** cadastrado na pousada **{hotel.nome}**."
        else:
            resposta = "Para criar uma reserva, por favor indique o quarto e o nome do hóspede. Exemplo: *'Reservar o quarto 101 para Mateus de hoje a amanhã'*."

    # 6. Room Status / Availability Query
    elif any(k in mensagem for k in ['livre', 'dispo', 'ocupa', 'vago', 'status', 'quarto', 'acomodação', 'chale', 'chalé', 'suite', 'suíte', 'como estão', 'situação', 'manuten', 'manut', 'amnut', 'anuten', 'manten', 'maten', 'bloque', 'bloq', 'interdit', 'interd', 'indisponi', 'limpez', 'limpa', 'sujo', 'faxina']) and not any(k in mensagem for k in ['criar', 'adicionar', 'reservar', 'reserva', 'checkout', 'check-out', 'liberar', 'desbloquear', 'cadastrar']):
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                resposta = formatar_quartos_grouped([unidade], hotel.nome, "Aqui está o status do quarto solicitado:")
            else:
                resposta = f"Não encontrei a acomodação **{quarto_num}** cadastrada na pousada **{hotel.nome}**."
        else:
            unidades_qs = UnidadeQuarto.objects.filter(quarto__hotel=hotel).order_by('identificador')
            unidades = list(unidades_qs)
            
            filter_desc = "gerais"
            # Detect status filter using stems (unicode-safe)
            if any(k in mensagem for k in ['livre', 'livres', 'dispo', 'vago', 'vagos']):
                unidades = [u for u in unidades if u.status_mapa == 'livre']
                filter_desc = "livres"
            elif any(k in mensagem for k in ['ocupa', 'aluga', 'cheio']):
                unidades = [u for u in unidades if u.status_mapa == 'ocupado']
                filter_desc = "ocupados"
            elif any(k in mensagem for k in ['limpez', 'limpa', 'sujo', 'faxina']):
                unidades = [u for u in unidades if u.status_mapa == 'limpeza']
                filter_desc = "em limpeza"
            elif any(k in mensagem for k in ['manuten', 'manut', 'amnut', 'anuten', 'manten', 'maten', 'bloque', 'bloq', 'interdit', 'interd', 'indisponi']):
                unidades = [u for u in unidades if u.status_mapa == 'indisponivel']
                filter_desc = "em manutenção ou bloqueados"

            # EXTRA FILTERS: Capacity (Pax)
            num_map = {'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'três': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10}
            pax_match = re.search(r'(\d+|um|uma|dois|duas|três|tres|quatro|cinco|seis|sete|oito|nove|dez)\s*(?:pessoa|hóspede|hospede|cama|alguem|alguém|pax|leito)', mensagem)
            pax = None
            if pax_match:
                val = pax_match.group(1)
                pax = int(val) if val.isdigit() else num_map.get(val, None)
            elif 'pessoa' in mensagem or 'hóspede' in mensagem or 'hospede' in mensagem:
                digit_match = re.search(r'\b(\d+)\b', mensagem)
                if digit_match:
                    pax = int(digit_match.group(1))

            if pax:
                exact_units = [u for u in unidades if u.quarto.capacidade_pessoas == pax]
                if exact_units:
                    unidades = exact_units
                else:
                    unidades = [u for u in unidades if u.quarto.capacidade_pessoas >= pax]
                filter_desc += f" para {pax} pessoas"

            # EXTRA FILTERS: Amenities (Comodidades)
            amenities_filters = []
            if any(k in mensagem for k in ['ar condicionado', 'ar-condicionado', 'ar cond', 'climatiz', 'ar-cond']):
                unidades = [u for u in unidades if any(x in (u.quarto.comodidades or '').lower() or x in (u.quarto.descricao or '').lower() or x in (u.quarto.seo_descricao or '').lower() for x in ['ar condicionado', 'ar-condicionado', 'ar cond', 'climatiz'])]
                amenities_filters.append("ar-condicionado")
            if any(k in mensagem for k in ['wifi', 'wi-fi', 'internet', 'fibra']):
                unidades = [u for u in unidades if any(x in (u.quarto.comodidades or '').lower() or x in (u.quarto.descricao or '').lower() or x in (u.quarto.seo_descricao or '').lower() for x in ['wifi', 'wi-fi', 'internet', 'fibra'])]
                amenities_filters.append("wi-fi")
            if any(k in mensagem for k in ['frigobar', 'geladeira']):
                unidades = [u for u in unidades if any(x in (u.quarto.comodidades or '').lower() or x in (u.quarto.descricao or '').lower() or x in (u.quarto.seo_descricao or '').lower() for x in ['frigobar', 'geladeira'])]
                amenities_filters.append("frigobar")
            if any(k in mensagem for k in ['hidro', 'jacuzzi', 'banheira']):
                unidades = [u for u in unidades if any(x in (u.quarto.comodidades or '').lower() or x in (u.quarto.descricao or '').lower() or x in (u.quarto.seo_descricao or '').lower() for x in ['hidro', 'jacuzzi', 'banheira'])]
                amenities_filters.append("hidromassagem/banheira")
            if any(k in mensagem for k in ['piscina', 'vista']):
                unidades = [u for u in unidades if any(x in (u.quarto.comodidades or '').lower() or x in (u.quarto.descricao or '').lower() or x in (u.quarto.seo_descricao or '').lower() for x in ['piscina', 'vista'])]
                amenities_filters.append("piscina/vista")

            if amenities_filters:
                filter_desc += f" com {', '.join(amenities_filters)}"

            # EXTRA FILTERS: Price limits
            price_match = re.search(r'(?:até|ate|maximo|máximo|valor|preço|preco|diaria|diária)\s*(?:r\$)?\s*(\d+)', mensagem)
            if price_match:
                max_price = float(price_match.group(1))
                if 'quarto' not in mensagem or max_price > 120:
                    unidades = [u for u in unidades if u.quarto.preco <= max_price]
                    filter_desc += f" com valor até R$ {max_price:.2f}"
            elif any(k in mensagem for k in ['mais barato', 'mais em conta', 'menor preço', 'menor valor']):
                unidades = sorted(unidades, key=lambda u: u.quarto.preco)
                if unidades:
                    cheapest_price = unidades[0].quarto.preco
                    unidades = [u for u in unidades if u.quarto.preco == cheapest_price]
                filter_desc += " de menor preço"

            if unidades:
                resposta = formatar_quartos_grouped(unidades, hotel.nome, f"Aqui está o status das acomodações **{filter_desc}** na **{hotel.nome}**:")
            else:
                resposta = f"Não encontrei nenhuma acomodação com o status **{filter_desc}** na pousada **{hotel.nome}**."

    # 8. Register / Update Guest (Cadastrar Hóspede / Dados)
    elif any(k in mensagem for k in ['cadastrar hóspede', 'cadastrar hospede', 'dados do hóspede', 'dados do hospede', 'preencher dados', 'adicionar acompanhante', 'registrar hóspede', 'registrar hospede', 'cadastrar pessoa']):
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
            if unidade:
                reserva = unidade.reserva_ativa
                if not reserva:
                    reserva = Reserva.objects.filter(unidade=unidade, status='confirmada').order_by('data_checkin').first()
                
                if reserva:
                    nome = "Acompanhante"
                    quotes = re.findall(r'"([^"]*)"', original_msg)
                    if quotes:
                        nome = quotes[0].strip()
                    else:
                        name_match = re.search(r'(?:nome|chamado|hóspede|hospede|pessoa|para)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', original_msg)
                        if name_match:
                            nome = name_match.group(1).strip()
                            
                    cpf_match = re.search(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', original_msg)
                    cpf = cpf_match.group(0) if cpf_match else ""
                    
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', original_msg)
                    email = email_match.group(0) if email_match else ""
                    
                    tel_match = re.search(r'\b(?:\(?\d{2}\)?\s*)?\d{4,5}-?\d{4}\b', original_msg)
                    tel = tel_match.group(0) if tel_match else ""
                    
                    is_acompanhante = 'acompanhante' in mensagem or 'novo hóspede' in mensagem or 'nova pessoa' in mensagem
                    if is_acompanhante:
                        from django.db.models import Max
                        max_ordem = reserva.hospedes.aggregate(Max('ordem'))['ordem__max'] or 1
                        hospede = HospedeReserva.objects.create(
                            reserva=reserva,
                            ordem=max_ordem + 1,
                            nome=nome,
                            cpf=cpf,
                            email=email,
                            telefone=tel
                        )
                        msg_sucesso = f"Adicionei o acompanhante **{nome}** à reserva da acomodação **{unidade.identificador}**."
                    else:
                        hospede, created = HospedeReserva.objects.get_or_create(
                            reserva=reserva,
                            ordem=1,
                            defaults={'nome': nome}
                        )
                        if not created and nome != "Acompanhante":
                            hospede.nome = nome
                        if cpf:
                            hospede.cpf = cpf
                        if email:
                            hospede.email = email
                        if tel:
                            hospede.telefone = tel
                        hospede.save()
                        
                        if nome != "Acompanhante":
                            reserva.hospede_nome = nome
                            reserva.save()
                        msg_sucesso = f"Dados do hóspede titular **{hospede.nome}** atualizados com sucesso para a acomodação **{unidade.identificador}**."
                        
                    action_performed = True
                    resposta = f"Perfeito! {msg_sucesso}<br>" \
                               f"• CPF: **{hospede.cpf or 'Não informado'}**<br>" \
                               f"• E-mail: **{hospede.email or 'Não informado'}**<br>" \
                               f"• Telefone: **{hospede.telefone or 'Não informado'}**"
                else:
                    resposta = f"A acomodação **{unidade.identificador}** não possui nenhuma reserva ativa ou futura confirmada para cadastrar hóspedes no momento."
            else:
                resposta = f"Não encontrei a acomodação **{quarto_num}** cadastrada na pousada **{hotel.nome}**."
        else:
            resposta = "Para cadastrar dados de um hóspede, por favor indique o quarto e os dados dele. Exemplo: *'Cadastrar hóspede do quarto 101 com nome \"Mateus Silva\" e CPF 123.456.789-00'*."

    # 7. Create Task
    elif any(k in mensagem for k in ['criar', 'adicionar', 'marcar', 'atribuir', 'agendar', 'cadastrar']):
        data_vencimento = date.today()
        data_label = "hoje"
        
        if 'amanhã' in mensagem or 'amanha' in mensagem:
            data_vencimento = date.today() + timedelta(days=1)
            data_label = "amanhã"
        elif 'semana' in mensagem:
            data_vencimento = date.today() + timedelta(days=7)
            data_label = "daqui a uma semana"
        else:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', mensagem)
            if date_match:
                try:
                    data_vencimento = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    data_label = data_vencimento.strftime('%d/%m/%Y')
                except ValueError:
                    pass
            else:
                date_match2 = re.search(r'(\d{2}/\d{2}/\d{4})', mensagem)
                if date_match2:
                    try:
                        data_vencimento = datetime.strptime(date_match2.group(1), '%d/%m/%Y').date()
                        data_label = data_vencimento.strftime('%d/%m/%Y')
                    except ValueError:
                        pass
        
        titulo = ""
        quote_match = re.findall(r'"([^"]*)"', original_msg)
        if quote_match:
            titulo = quote_match[0].strip()
        else:
            if 'reunião' in mensagem or 'reuniao' in mensagem:
                titulo = "Reunião de Equipe"
            elif 'faxina' in mensagem or 'limpeza' in mensagem:
                titulo = "Faxina e Higienização"
            elif 'manutenção' in mensagem or 'manutencao' in mensagem:
                titulo = "Manutenção do Quarto"
            else:
                titulo = "Atividade Operacional"
        
        responsavel = None
        for func in hotel.equipe.all():
            nome_func = func.user.first_name.lower() or func.user.username.lower()
            if nome_func in mensagem:
                responsavel = func
                break
                
        unidade = None
        unidade_match = re.search(r'(?:quarto|suite|suíte|chale|chalé|unidade)\s*(\d+)', mensagem)
        if unidade_match:
            quarto_num = unidade_match.group(1)
            unidade = UnidadeQuarto.objects.filter(identificador__icontains=quarto_num, quarto__hotel=hotel).first()
        
        prioridade = 'normal'
        if any(k in mensagem for k in ['urgente', 'alta', 'prioridade alta']):
            prioridade = 'alta'
        elif any(k in mensagem for k in ['baixa', 'prioridade baixa']):
            prioridade = 'baixa'
            
        t = Tarefa.objects.create(
            hotel=hotel,
            titulo=titulo,
            descricao=f"Criado automaticamente via Assistente de IA por solicitação de {request.user.get_full_name() or request.user.username}.",
            prioridade=prioridade,
            status='todo',
            data_vencimento=data_vencimento,
            responsavel=responsavel,
            unidade=unidade
        )
        action_performed = True
        
        resp_parts = [f"Perfeito! Agendei a tarefa **#{t.id} - {t.titulo}** para **{data_label}**."]
        if responsavel:
            resp_parts.append(f"Responsável: **{responsavel.user.get_full_name() or responsavel.user.username}**.")
        if unidade:
            resp_parts.append(f"Acomodação vinculada: **{unidade.identificador}**.")
        resp_parts.append("*(Dica: Recarregue a página para ver a atividade no seu quadro de tarefas!)*")
        resposta = " ".join(resp_parts)

    # 8. List Tasks
    elif any(k in mensagem for k in ['tarefa', 'afazeres', 'lista', 'listar', 'pendente', 'urgente', 'atividades']):
        real_tasks = Tarefa.objects.filter(hotel=hotel).order_by('data_vencimento')
        
        if 'hoje' in mensagem:
            real_tasks = real_tasks.filter(data_vencimento=date.today())
            filter_desc = "agendadas para hoje"
        elif 'urgente' in mensagem or 'urgentes' in mensagem:
            real_tasks = real_tasks.filter(prioridade='alta')
            filter_desc = "com prioridade alta (urgentes)"
        elif 'pendente' in mensagem or 'pendentes' in mensagem or 'todo' in mensagem or 'doing' in mensagem:
            real_tasks = real_tasks.filter(status__in=['todo', 'doing'])
            filter_desc = "pendentes de conclusão"
        else:
            filter_desc = "gerais registradas"
            
        if real_tasks.exists():
            resposta = f"Aqui estão as tarefas {filter_desc} na **{hotel.nome}**:<br><br>"
            for t in real_tasks[:8]:
                status_emoji = "⏳"
                if t.status == 'doing':
                    status_emoji = "⚡"
                elif t.status == 'done':
                    status_emoji = "✅"
                
                resp_line = f"{status_emoji} **#{t.id} - {t.titulo}**<br>"
                details = []
                if t.responsavel:
                    details.append(f"Atribuída a: {t.responsavel.user.get_full_name() or t.responsavel.user.username}")
                if t.data_vencimento:
                    details.append(f"Vence em: {t.data_vencimento.strftime('%d/%m/%Y')}")
                details.append(f"Status: {t.get_status_display()}")
                details.append(f"Prioridade: {t.get_prioridade_display()}")
                resp_line += f"&nbsp;&nbsp;&nbsp;&nbsp;*({', '.join(details)})*<br>"
                resposta += resp_line
        else:
            resposta = f"Não encontrei nenhuma tarefa {filter_desc} cadastrada para a **{hotel.nome}**."

    # 9. Greeting & Finance Fallbacks
    elif any(k in mensagem for k in ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite']):
        resposta = f"Olá, **{request.user.first_name or request.user.username}**! Sou o seu assistente Naviê AI para a **{hotel.nome}**. Posso gerenciar tarefas operacionais e acomodações em tempo real: experimente dizer *'quais quartos estão livres?'*, *'reservar quarto 101 para Mateus'*, *'checkout do quarto 102'* ou *'bloquear quarto 105 para manutenção'*!"
    elif 'faturamento' in mensagem or 'financeiro' in mensagem or 'caixa' in mensagem or 'receita' in mensagem:
        resposta = "Consultando relatórios financeiros... Atualmente os lançamentos operacionais indicam faturamento positivo com fluxo de caixa sob controle neste mês. Para ver o detalhado, navegue até a aba 'Visão Geral / Financeiro'!"
    else:
        resposta = "Entendido! Posso ajudar na organização operacional e gestão de acomodações da pousada. Experimente me pedir para: *'listar as tarefas de hoje'*, *'quais quartos estão livres?'*, *'reservar o quarto 101 para João Silva'* ou *'bloquear quarto 102 para manutenção'*!"
        
    # Converter markdown simples para HTML
    resposta_html = resposta
    resposta_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', resposta_html)
    resposta_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', resposta_html)
    
    context = {'resposta_ia': resposta_html}
    return render(request, 'hoteis/ia_chat_response.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_criar_tarefa(request):
    """
    Creates a new operational Task/Activity for the B2B dashboard.
    --------------------------------------------------------------
    This view manages the B2B Task Creation modal and handles POST requests 
    to instantiate a new task linked to the current user's hotel.
    
    Operational Schema (AI-Readiness):
    - GET: Renders a form containing members of the hotel staff, active room units, and bookings.
    - POST: Validates arguments and creates a Tarefa record.
    
    Fields required in POST:
    - titulo (str): Non-empty task title.
    - descricao (str, optional): Additional instructions.
    - prioridade (str): choices: 'baixa', 'normal', 'alta'. Default 'normal'.
    - status (str): choices: 'todo', 'doing', 'done'. Default 'todo'.
    - data_vencimento (str, format YYYY-MM-DD): Target deadline.
    - responsavel_id (int, optional): ID of the staff member (ParceiroUsuario).
    - unidade_id (int, optional): ID of the room unit (UnidadeQuarto).
    - reserva_id (int, optional): ID of the linked booking (Reserva).
    
    Returns:
    - HTML modal render on GET, or HX-Redirect to B2B dashboard on successful POST.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        prioridade = request.POST.get('prioridade', 'normal')
        status = request.POST.get('status', 'todo')
        data_vencimento_str = request.POST.get('data_vencimento', '').strip()
        responsavel_id = request.POST.get('responsavel_id')
        unidade_id = request.POST.get('unidade_id')
        reserva_id = request.POST.get('reserva_id')
        
        data_vencimento = None
        if data_vencimento_str:
            try:
                data_vencimento = datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        responsavel = None
        if responsavel_id:
            responsavel = get_object_or_404(ParceiroUsuario, id=responsavel_id, hotel=hotel)
            
        unidade = None
        if unidade_id:
            unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
            
        reserva = None
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
            
        if titulo:
            Tarefa.objects.create(
                hotel=hotel,
                titulo=titulo,
                descricao=descricao,
                prioridade=prioridade,
                status=status,
                data_vencimento=data_vencimento,
                responsavel=responsavel,
                unidade=unidade,
                reserva=reserva
            )
            messages.success(request, "Nova atividade operacional adicionada!")
            
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse()
                from django.urls import reverse
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
            
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    
    data_inicial = request.GET.get('data', '')
    
    context = {
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        'data_inicial': data_inicial,
        'tarefa': None
    }
    return render(request, 'hoteis/atividades/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_editar_tarefa(request, tarefa_id):
    """
    Edits an existing operational Task/Activity.
    -------------------------------------------
    This view retrieves the specified Tarefa record and renders the edit form modal,
    saving any changes during a POST request.
    
    Operational Schema (AI-Readiness):
    - GET: Populates the modal fields with the current task state.
    - POST: Modifies the task state and saves it.
    
    Parameters:
    - request: HttpRequest object.
    - tarefa_id (int): Primary key ID of the target Task.
    
    Fields allowed in POST:
    - Same parameters as partner_criar_tarefa. Modifies instead of creates.
    
    Returns:
    - HTML modal on GET, or HX-Redirect to B2B dashboard on successful POST.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=hotel)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        prioridade = request.POST.get('prioridade', 'normal')
        status = request.POST.get('status', 'todo')
        data_vencimento_str = request.POST.get('data_vencimento', '').strip()
        responsavel_id = request.POST.get('responsavel_id')
        unidade_id = request.POST.get('unidade_id')
        reserva_id = request.POST.get('reserva_id')
        
        data_vencimento = None
        if data_vencimento_str:
            try:
                data_vencimento = datetime.strptime(data_vencimento_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        responsavel = None
        if responsavel_id:
            responsavel = get_object_or_404(ParceiroUsuario, id=responsavel_id, hotel=hotel)
            
        unidade = None
        if unidade_id:
            unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
            
        reserva = None
        if reserva_id:
            reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
            
        if titulo:
            tarefa.titulo = titulo
            tarefa.descricao = descricao
            tarefa.prioridade = prioridade
            tarefa.status = status
            tarefa.data_vencimento = data_vencimento
            tarefa.responsavel = responsavel
            tarefa.unidade = unidade
            tarefa.reserva = reserva
            tarefa.save()
            
            messages.success(request, "Atividade atualizada com sucesso!")
            
            if request.headers.get('HX-Request') == 'true':
                response = HttpResponse()
                from django.urls import reverse
                response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
                return response
            return redirect('hoteis:partner_dashboard')
            
    equipe = hotel.equipe.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    reservas = Reserva.objects.filter(unidade__quarto__hotel=hotel).order_by('-criado_em')
    
    context = {
        'equipe': equipe,
        'unidades': unidades,
        'reservas': reservas,
        'tarefa': tarefa,
        'data_inicial': ''
    }
    return render(request, 'hoteis/atividades/partials/modal_tarefa.html', context)


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_deletar_tarefa(request, tarefa_id):
    """
    Deletes an operational Task/Activity.
    -------------------------------------
    Accepts only POST requests to securely delete the Tarefa object and redirect.
    
    Operational Schema (AI-Readiness):
    - POST: Deletes the Tarefa from the database.
    
    Parameters:
    - request: HttpRequest object.
    - tarefa_id (int): Primary key ID of the target Task to delete.
    
    Returns:
    - Redirect or HX-Redirect to the B2B dashboard.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=perfil.hotel)
    tarefa.delete()
    
    messages.success(request, "Atividade operacional excluída permanentemente.")
    
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        from django.urls import reverse
        response['HX-Redirect'] = reverse('hoteis:partner_dashboard')
        return response
    return redirect('hoteis:partner_dashboard')


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_mudar_status_tarefa(request, tarefa_id):
    """
    Asynchronously updates the status of a Task (specifically for drag-and-drop actions).
    -------------------------------------------------------------------------------------
    Invoked primarily via SortableJS on the B2B Kanban board, updating status in real-time.
    
    Operational Schema (AI-Readiness):
    - POST: Modifies the status attribute.
    
    Parameters:
    - request: HttpRequest.
    - tarefa_id (int): ID of the task.
    - request.POST.get('status'): Target status value, choices: ('todo', 'doing', 'done', 'overdue').
    
    Returns:
    - HttpResponse with status code 200 on success, or 400 on invalid parameters.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse(status=403)
        
    perfil = request.user.perfil_parceiro
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, hotel=perfil.hotel)
    
    novo_status = request.POST.get('status')
    if novo_status in ['overdue', 'todo', 'doing', 'done']:
        if novo_status == 'overdue':
            tarefa.status = 'todo'
            tarefa.data_vencimento = date.today() - timedelta(days=1)
        else:
            tarefa.status = novo_status
            
        tarefa.save()
        return HttpResponse(status=200)
    return HttpResponse(status=400)


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_salvar_configuracoes(request):
    """
    Grava as configurações de personalização visual, contatos e geolocalização do hotel.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        messages.error(request, "Acesso negado.")
        return redirect('clientes:painel')
        
    perfil = request.user.perfil_parceiro
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente para alterar as configurações.")
        return redirect('hoteis:partner_dashboard')
        
    hotel = perfil.hotel
    
    # Atualização dos campos de texto e branding
    hotel.nome = request.POST.get('nome', hotel.nome)
    hotel.descricao = request.POST.get('descricao', hotel.descricao)
    
    raw_whatsapp = request.POST.get('whatsapp', '')
    cleaned_whatsapp = ''.join(c for c in raw_whatsapp if c.isdigit())
    if len(cleaned_whatsapp) in [10, 11]:
        cleaned_whatsapp = '55' + cleaned_whatsapp
    hotel.whatsapp = cleaned_whatsapp
    
    hotel.cor_primaria = request.POST.get('cor_primaria', hotel.cor_primaria)
    hotel.cor_secundaria = request.POST.get('cor_secundaria', hotel.cor_secundaria)
    hotel.hero_tipo = request.POST.get('hero_tipo', hotel.hero_tipo)
    
    # Geolocalização
    lat = request.POST.get('latitude', '').strip().replace(',', '.')
    lon = request.POST.get('longitude', '').strip().replace(',', '.')
    if lat and lat.lower() != 'none' and lat.lower() != 'nan':
        try:
            hotel.latitude = float(lat)
        except ValueError:
            pass
    if lon and lon.lower() != 'none' and lon.lower() != 'nan':
        try:
            hotel.longitude = float(lon)
        except ValueError:
            pass
            
    # Endereço por extenso
    if hotel.local:
        hotel.local.endereco = request.POST.get('endereco', hotel.local.endereco).strip()
        hotel.local.save()
            
    # Upload de arquivos e remoções
    if request.POST.get('remover_banner') == 'true':
        hotel.banner = None
    elif 'banner' in request.FILES:
        hotel.banner = request.FILES['banner']
        
    if request.POST.get('remover_logo') == 'true':
        hotel.logo = None
    elif 'logo' in request.FILES:
        hotel.logo = request.FILES['logo']
        
    if request.POST.get('remover_foto_fundo') == 'true':
        hotel.foto_fundo = None
    elif 'foto_fundo' in request.FILES:
        hotel.foto_fundo = request.FILES['foto_fundo']
        
    if request.POST.get('remover_imagem_compartilhamento') == 'true':
        hotel.imagem_compartilhamento = None
    elif 'imagem_compartilhamento' in request.FILES:
        hotel.imagem_compartilhamento = request.FILES['imagem_compartilhamento']
        
    # Processa remoção ou novo upload do vídeo do banner
    if request.POST.get('remover_hero_video') == 'true':
        hotel.hero_video = None
    elif 'hero_video' in request.FILES:
        video_file = request.FILES['hero_video']
        # Limitar a 30MB
        if video_file.size > 30 * 1024 * 1024:
            messages.error(request, "O vídeo em loop ultrapassa o limite de 30MB permitido.")
            return redirect('hoteis:partner_dashboard')
        hotel.hero_video = video_file
        
    # Processar fotos da galeria (10 slots)
    for idx in range(10):
        img_id = request.POST.get(f'galeria_{idx}_id')
        remover = request.POST.get(f'galeria_{idx}_remover') == 'true'
        file = request.FILES.get(f'galeria_{idx}_file')
        
        if img_id:
            try:
                imagem_obj = HotelImagem.objects.get(id=img_id, hotel=hotel)
                if remover:
                    try:
                        imagem_obj.url_imagem.delete(save=False)
                    except Exception:
                        pass
                    imagem_obj.delete()
                elif file:
                    try:
                        imagem_obj.url_imagem.delete(save=False)
                    except Exception:
                        pass
                    imagem_obj.url_imagem = file
                    imagem_obj.save()
            except HotelImagem.DoesNotExist:
                pass
        elif file and not remover:
            HotelImagem.objects.create(
                hotel=hotel,
                url_imagem=file,
                ordem=idx
            )
         
    # Seção Sobre da Pousada
    hotel.sobre_titulo = request.POST.get('sobre_titulo', hotel.sobre_titulo)
    hotel.sobre_texto = request.POST.get('sobre_texto', hotel.sobre_texto)
    hotel.sobre_midia_tipo = request.POST.get('sobre_midia_tipo', hotel.sobre_midia_tipo or 'imagem')
    hotel.sobre_cor_fundo = request.POST.get('sobre_cor_fundo', hotel.sobre_cor_fundo or '#f8fafc')
    hotel.sobre_cor_texto = request.POST.get('sobre_cor_texto', hotel.sobre_cor_texto or '#0f172a')
    
    if request.POST.get('remover_sobre_banner') == 'true':
        hotel.sobre_banner = None
    elif 'sobre_banner' in request.FILES:
        hotel.sobre_banner = request.FILES['sobre_banner']
        
    if request.POST.get('remover_sobre_video') == 'true':
        hotel.sobre_video = None
    elif 'sobre_video' in request.FILES:
        video_file_sobre = request.FILES['sobre_video']
        if video_file_sobre.size > 8 * 1024 * 1024:
            messages.error(request, "O vídeo da seção Sobre ultrapassa o limite de 8MB.")
            return redirect('hoteis:partner_dashboard')
        hotel.sobre_video = video_file_sobre

    hotel.save()
    messages.success(request, "Configurações do estabelecimento gravadas com sucesso!")
    return redirect('/hospedagens/sistema/?tab=configuracoes&config_tab=site')


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_salvar_configuracoes_geral(request):
    """
    Grava as configurações gerais do portal de rede unificado (Empresa) associado ao hotel.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        messages.error(request, "Acesso negado.")
        return redirect('clientes:painel')
        
    perfil = request.user.perfil_parceiro
    if perfil.role not in ['proprietario', 'gerente']:
        messages.error(request, "Permissão insuficiente para alterar as configurações.")
        return redirect('hoteis:partner_dashboard')
        
    hotel = perfil.hotel
    empresa = hotel.empresa
    
    if not empresa or empresa.modalidade_portal != 'unificado':
        messages.error(request, "Esta empresa não está configurada como portal unificado.")
        return redirect('hoteis:partner_dashboard')
        
    # Salvar campos textuais
    empresa.nome_fantasia = request.POST.get('nome_fantasia', empresa.nome_fantasia)
    empresa.cor_primaria = request.POST.get('cor_primaria', empresa.cor_primaria)
    empresa.cor_secundaria = request.POST.get('cor_secundaria', empresa.cor_secundaria)
    empresa.descricao_portal = request.POST.get('descricao_portal', '')
    empresa.hero_tipo = request.POST.get('hero_tipo', empresa.hero_tipo or 'imagem')
    
    # Seção Sobre
    empresa.sobre_titulo = request.POST.get('sobre_titulo', '')
    empresa.sobre_texto = request.POST.get('sobre_texto', '')
    empresa.sobre_midia_tipo = request.POST.get('sobre_midia_tipo', 'imagem')
    empresa.sobre_cor_fundo = request.POST.get('sobre_cor_fundo', '#f8fafc')
    empresa.sobre_cor_texto = request.POST.get('sobre_cor_texto', '#0f172a')
    
    # Uploads e remoções
    if request.POST.get('remover_banner') == 'true':
        empresa.banner = None
    elif 'banner' in request.FILES:
        empresa.banner = request.FILES['banner']
        
    if request.POST.get('remover_logo') == 'true':
        empresa.logo = None
    elif 'logo' in request.FILES:
        empresa.logo = request.FILES['logo']
        
    if request.POST.get('remover_hero_video') == 'true':
        empresa.hero_video = None
    elif 'hero_video' in request.FILES:
        empresa.hero_video = request.FILES['hero_video']
        
    if request.POST.get('remover_imagem_compartilhamento') == 'true':
        empresa.imagem_compartilhamento = None
    elif 'imagem_compartilhamento' in request.FILES:
        empresa.imagem_compartilhamento = request.FILES['imagem_compartilhamento']
        
    if request.POST.get('remover_sobre_banner') == 'true':
        empresa.sobre_banner = None
    elif 'sobre_banner' in request.FILES:
        empresa.sobre_banner = request.FILES['sobre_banner']
        
    if request.POST.get('remover_sobre_video') == 'true':
        empresa.sobre_video = None
    elif 'sobre_video' in request.FILES:
        empresa.sobre_video = request.FILES['sobre_video']
        
    # Salvar ordem das pousadas
    ordem_hoteis = request.POST.get('ordem_hoteis', '').strip()
    if ordem_hoteis:
        try:
            from hoteis.models import Hotel
            ids = [int(x) for x in ordem_hoteis.split(',') if x.isdigit()]
            for idx, h_id in enumerate(ids):
                Hotel.objects.filter(id=h_id, empresa=empresa).update(ordem=idx)
        except Exception as e:
            print("Erro ao atualizar ordem das pousadas: ", e)
            
    empresa.save()
    messages.success(request, "Configurações gerais do grupo gravadas com sucesso!")
    return redirect('/hospedagens/sistema/?tab=configuracoes&config_tab=geral')


# ─────────────────────────────────────────────────────────────
# GESTÃO REATIVA DE ACOMODAÇÕES (B2B HTMX CONTROLLERS)
# ─────────────────────────────────────────────────────────────

from django.views.decorators.http import require_http_methods, require_POST
from django.http import HttpResponse
from .models import QuartoImagem

@login_required(login_url='hoteis:partner_login')
def partner_quarto_formulario(request, quarto_id=None):
    """
    Carrega o formulário completo de criação ou edição de quarto via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto = None
    if quarto_id:
        quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
        
    context = {
        'quarto': quarto,
        'hotel': hotel,
        'capacidades': [1, 2, 3, 4, 5, 6, 7],
        'tags_disponiveis': ["Família", "Casal", "Romântico", "Serra", "Trabalho Remoto", "Pet Friendly", "Silencioso"],
        'comodidades_disponiveis': ["Ar Condicionado", "Wi-Fi de Alta Velocidade", "Copa Completa", "Piscina Privativa", "Hidromassagem", "Frigobar Abastecido", "Café no Quarto"]
    }
    return render(request, 'hoteis/quartos/partials/quarto_formulario.html', context)


@login_required(login_url='hoteis:partner_login')
def partner_quarto_lista(request):
    """
    Retorna apenas a grade de cards dos quartos via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quartos = hotel.quartos.all()
    
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@never_cache
def partner_liberar_quarto(request, unidade_id):
    """
    Marca as tarefas de limpeza pendentes da unidade como concluídas e re-renderiza o mapa de quartos.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    from hoteis.models import UnidadeQuarto, Tarefa
    unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
    
    # Conclui todas as tarefas de limpeza pendentes da unidade
    tarefas_limpeza = Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Limpeza')
    for t in tarefas_limpeza:
        t.status = 'done'
        t.save()
        
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_mapa.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_POST
@never_cache
def partner_atualizar_disponibilidade_quarto(request, unidade_id):
    """
    Atualiza a disponibilidade operacional de um quarto físico específico da pousada e gerencia ordens de serviço.
    
    Parâmetros (via POST):
    - unidade_id (int na URL): ID da unidade de quarto (UnidadeQuarto).
    - disponivel (str): 'true' para liberar o quarto; 'false' para bloquear.
    - motivo_indisponivel (str, se disponivel for 'false'): Escolha entre ['limpeza', 'manutencao', 'outro'].
    - justificativa_indisponivel (str, opcional): Descrição textual com detalhes do motivo do bloqueio.
    
    Comportamento Operacional:
    - Se liberado (disponivel='true'), limpa os campos de indisponibilidade e conclui (status='done') todas as tarefas pendentes vinculadas ao quarto.
    - Se bloqueado (disponivel='false'), define o motivo e cria uma Tarefa pendente adequada (Limpeza, Manutenção ou Serviço Operacional) para a equipe.
    
    Retorno:
    - Renderiza e retorna o fragmento HTMX 'hoteis/quartos/partials/quarto_mapa.html' atualizado.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    from hoteis.models import UnidadeQuarto, Tarefa
    unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
    
    disponivel_str = request.POST.get('disponivel', 'true')
    disponivel = disponivel_str.lower() == 'true'
    
    unidade.disponivel = disponivel
    if not disponivel:
        motivo = request.POST.get('motivo_indisponivel')
        justificativa = request.POST.get('justificativa_indisponivel', '').strip()
        unidade.motivo_indisponivel = motivo
        unidade.justificativa_indisponivel = justificativa
        
        # Criação de Tarefas operacionais correspondentes
        if motivo == 'limpeza':
            if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Limpeza').exists():
                Tarefa.objects.create(
                    hotel=hotel,
                    titulo=f"Limpeza e Higienização - {unidade.identificador}",
                    descricao="Solicitada manualmente via controle de disponibilidade.",
                    prioridade='normal',
                    status='todo',
                    unidade=unidade
                )
        elif motivo == 'manutencao':
            if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Manutenção').exists():
                Tarefa.objects.create(
                    hotel=hotel,
                    titulo=f"Manutenção e Reparos - {unidade.identificador}",
                    descricao=justificativa or "Manutenção solicitada manualmente via controle de disponibilidade.",
                    prioridade='alta',
                    status='todo',
                    unidade=unidade
                )
        elif motivo == 'outro':
            if not Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Serviço Operacional').exists():
                Tarefa.objects.create(
                    hotel=hotel,
                    titulo=f"Serviço Operacional - {unidade.identificador}",
                    descricao=justificativa or "Bloqueio operacional avulso.",
                    prioridade='normal',
                    status='todo',
                    unidade=unidade
                )
    else:
        unidade.motivo_indisponivel = None
        unidade.justificativa_indisponivel = None
        # Conclui tarefas operacionais ativas para liberar o quarto
        Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing']).update(status='done')
        
    unidade.save()
    
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_mapa.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@never_cache
def partner_detalhe_quarto_modal(request, unidade_id):
    """
    Exibe o modal de detalhes operacionais de um quarto físico, exibindo
    abas de Ocupação, Tarefas pendentes e Ações/Liberação de forma reativa.
    
    Parâmetros:
    - unidade_id (int na URL): ID da unidade de quarto (UnidadeQuarto).
    
    Comportamento Operacional:
    - Carrega a reserva ativa (se houver hóspede no quarto).
    - Carrega todas as tarefas de limpeza pendentes vinculadas a esta unidade física.
    
    Retorno:
    - Renderiza e retorna o modal HTML 'hoteis/quartos/partials/modal_detalhe_quarto.html'.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    from hoteis.models import UnidadeQuarto, Reserva, Tarefa
    unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
    
    # Detalhes da reserva ativa se estiver ocupado
    reserva = unidade.reserva_ativa
    
    # Tarefas de limpeza pendentes da unidade
    tarefas_limpeza = Tarefa.objects.filter(unidade=unidade, status__in=['todo', 'doing'], titulo__icontains='Limpeza')
    
    context = {
        'u': unidade,
        'reserva': reserva,
        'tarefas_limpeza': tarefas_limpeza,
        'hotel': hotel,
        'perfil': request.user.perfil_parceiro
    }
    return render(request, 'hoteis/quartos/partials/modal_detalhe_quarto.html', context)


@login_required(login_url='hoteis:partner_login')
@require_POST
@never_cache
def partner_checkout_quarto_mapa(request, reserva_id):
    """
    Realiza o check-out de uma reserva ativa direto do mapa de quartos e retorna o mapa atualizado.
    
    Parâmetros:
    - reserva_id (int na URL): ID da reserva a ter o check-out efetuado.
    
    Comportamento Operacional:
    - Atualiza a reserva para o status 'concluido' e define a data/hora real de check-out (checkout_realizado_em).
    - Cria um log em ReservaLog documentando a ação.
    - Cria automaticamente uma tarefa de limpeza pós-checkout ("Limpeza e Preparação - {quarto}") pendente para a equipe operacional.
    
    Retorno:
    - Renderiza e retorna o fragmento HTMX 'hoteis/quartos/partials/quarto_mapa.html' atualizado.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    from hoteis.models import Reserva, UnidadeQuarto, Tarefa, ReservaLog
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    # Executa check-out
    reserva.status = 'concluido'
    from django.utils import timezone
    reserva.checkout_realizado_em = timezone.now()
    reserva.save()
    
    # Log action
    ReservaLog.objects.create(
        reserva=reserva,
        usuario=request.user,
        acao='checkout',
        detalhes=f"Check-out realizado via mapa de quartos pelo usuário {request.user.username}."
    )
    
    # Criar tarefa de limpeza pós-checkout se não existir
    if not Tarefa.objects.filter(reserva=reserva, titulo__icontains="Limpeza").exists():
        Tarefa.objects.create(
            hotel=hotel,
            titulo=f"Limpeza e Preparação - {reserva.unidade.identificador}",
            descricao=f"Realizar limpeza pós-checkout da reserva #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}.",
            prioridade='alta',
            status='todo',
            unidade=reserva.unidade,
            reserva=reserva
        )
        
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_mapa.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_quarto_salvar(request):
    """
    Salva ou atualiza um quarto com suporte a upload de múltiplas imagens,
    descontos multidias, categorização e SEO/IA. Retorna a grade atualizada via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto_id = request.POST.get('quarto_id')
    
    if quarto_id:
        quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
    else:
        quarto = Quarto(hotel=hotel)
        
    quarto.nome = request.POST.get('nome', '').strip()
    quarto.descricao = request.POST.get('descricao', '').strip()
    
    # Tratamento de preço decimal
    preco_raw = request.POST.get('preco', '0').replace(',', '.')
    try:
        quarto.preco = float(preco_raw)
    except ValueError:
        quarto.preco = 0.00
        
    quarto.video_url = request.POST.get('video_url', '').strip() or None
    
    # Processa upload do arquivo de vídeo local
    if request.POST.get('remover_video') == 'true':
        quarto.video_arquivo = None
    elif 'video_arquivo' in request.FILES:
        vid_file = request.FILES['video_arquivo']
        if vid_file.size <= 30 * 1024 * 1024:  # Limite de 30MB
            quarto.video_arquivo = vid_file
    
    try:
        quarto.capacidade_pessoas = int(request.POST.get('capacidade_pessoas', '2'))
    except ValueError:
        quarto.capacidade_pessoas = 2
        
    # Tags e comodidades selecionadas
    quarto.tags = request.POST.get('tags', '').strip()
    quarto.comodidades = request.POST.get('comodidades', '').strip()
    
    # Descontos
    quarto.tem_desconto_multidias = request.POST.get('tem_desconto_multidias') == 'true'
    try:
        quarto.dias_minimos_desconto = int(request.POST.get('dias_minimos_desconto', '3'))
    except ValueError:
        quarto.dias_minimos_desconto = 3
        
    desc_raw = request.POST.get('percentual_desconto', '0').replace(',', '.')
    try:
        quarto.percentual_desconto = float(desc_raw)
    except ValueError:
        quarto.percentual_desconto = 0.00
        
    # SEO e IA
    quarto.seo_titulo = request.POST.get('seo_titulo', '').strip() or None
    quarto.seo_descricao = request.POST.get('seo_descricao', '').strip() or None
    
    quarto.save()
    
    # Processa a sincronização de unidades físicas (UnidadeQuarto)
    unidades_ids = request.POST.getlist('unidades_ids')
    unidades_identificadores = request.POST.getlist('unidades_identificadores')
    
    submitted_pairs = []
    for uid, ident in zip(unidades_ids, unidades_identificadores):
        ident = ident.strip()
        if ident:
            submitted_pairs.append((uid, ident))
            
    # Se nenhuma unidade foi enviada, garante pelo menos uma padrão
    if not submitted_pairs:
        submitted_pairs.append(('new', '101'))
        
    existing_units = {str(u.id): u for u in quarto.unidades.all()}
    submitted_ids = set()
    
    for uid, ident in submitted_pairs:
        if uid in existing_units:
            unit = existing_units[uid]
            unit.identificador = ident
            unit.ativa = True
            unit.save()
            submitted_ids.add(uid)
        else:
            new_unit = UnidadeQuarto.objects.create(
                quarto=quarto,
                identificador=ident,
                ativa=True
            )
            submitted_ids.add(str(new_unit.id))
            
    # Exclui ou desativa fisicamente as que não vieram no POST
    for uid, unit in existing_units.items():
        if uid not in submitted_ids:
            try:
                unit.delete()
            except Exception:
                unit.ativa = False
                unit.save()
    
    # Processa uploads de múltiplas imagens
    imagens_carregadas = request.FILES.getlist('imagens')
    current_count = QuartoImagem.objects.filter(quarto=quarto).count()
    for idx, img in enumerate(imagens_carregadas):
        # Limite de no máximo 10 fotos no total
        if current_count + idx >= 10:
            break
        QuartoImagem.objects.create(
            quarto=quarto,
            url_imagem=img,
            ordem=current_count + idx
        )
        
    messages.success(request, f"Acomodação '{quarto.nome}' salva com sucesso!")
    
    # Retorna a grade atualizada
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar(request, quarto_id):
    """
    Exclui um quarto do estabelecimento e retorna a grade atualizada via HTMX.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    quarto = get_object_or_404(Quarto, id=quarto_id, hotel=hotel)
    quarto_nome = quarto.nome
    quarto.delete()
    
    messages.success(request, f"Quarto '{quarto_nome}' excluído com sucesso!")
    
    # Retorna a grade atualizada
    quartos = hotel.quartos.all()
    return render(request, 'hoteis/quartos/partials/quarto_grid.html', {'quartos': quartos})


@login_required(login_url='hoteis:partner_login')
@require_http_methods(["DELETE", "POST"])
def partner_quarto_deletar_imagem(request, imagem_id):
    """
    Exclui uma imagem específica do quarto via HTMX. Retorna string vazia para remover o card.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    img = get_object_or_404(QuartoImagem, id=imagem_id, quarto__hotel=hotel)
    img.delete()
    
    return HttpResponse("")

def quarto_detalhe(request, hotel_id, quarto_slug):
    """
    Página pública B2C de detalhes de uma acomodação específica.
    URL amigável com slug gerado do nome do quarto, único por hotel.
    Ex: /hotel/1/acomodacao/suite-premium-2/
    """
    hotel = get_object_or_404(Hotel, id=hotel_id)
    quarto = get_object_or_404(Quarto, hotel=hotel, slug=quarto_slug)
    
    # Incrementa contador de visualizações
    quarto.visualizacoes += 1
    quarto.save(update_fields=['visualizacoes'])

    imagens = list(quarto.imagens.all())
    primeira_imagem = imagens[0] if imagens else None
    outras_imagens = imagens[1:] if len(imagens) > 1 else []

    comodidades = [c.strip() for c in quarto.comodidades.split(',') if c.strip()] if quarto.comodidades else []
    tags = [t.strip() for t in quarto.tags.split(',') if t.strip()] if quarto.tags else []

    context = {
        'hotel': hotel,
        'quarto': quarto,
        'primeira_imagem': primeira_imagem,
        'outras_imagens': outras_imagens,
        'comodidades': comodidades,
        'tags': tags,
        'imagens_todas': imagens,
    }
    return render(request, 'hoteis/quartos/quarto_detalhe.html', context)

@require_POST
def carrinho_adicionar(request, quarto_id):
    quarto = get_object_or_404(Quarto, id=quarto_id)
    checkin_str = request.POST.get('checkin')
    checkout_str = request.POST.get('checkout')
    
    if not checkin_str or not checkout_str:
        return JsonResponse({'success': False, 'error': 'Selecione as datas de check-in e check-out.'}, status=400)
    
    try:
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Formato de data inválido.'}, status=400)
        
    if checkout <= checkin:
        return JsonResponse({'success': False, 'error': 'A data de checkout deve ser após a data de check-in.'}, status=400)
        
    # Validar disponibilidade
    if not checar_disponibilidade_quarto(quarto, checkin, checkout):
        return JsonResponse({'success': False, 'error': 'Desculpe, esta acomodação não está disponível para o período selecionado.'}, status=400)
        
    # Adicionar ao carrinho na sessão pré-configurado com a capacidade máxima do quarto
    request.session['carrinho'] = {
        'quarto_id': quarto.id,
        'checkin': checkin_str,
        'checkout': checkout_str,
        'quantidade_hospedes': quarto.capacidade_pessoas,
        'hospedes': [{} for _ in range(quarto.capacidade_pessoas)],
        'veiculo': {'placa': '', 'modelo': '', 'cor': ''}
    }
    request.session.modified = True
    
    # Rastrear carrinho no analytics de forma segura
    try:
        from analytics.models import CarrinhoStatus
        tracker_id = getattr(request, 'tracker_id', None)
        if tracker_id:
            CarrinhoStatus.objects.update_or_create(
                tracker_id=tracker_id,
                category='hospedagem',
                item_id=str(quarto.id),
                defaults={
                    'usuario': request.user if request.user.is_authenticated else None,
                    'quantidade': 1,
                    'recuperado': False,
                    'metadata': {
                        'checkin': checkin_str,
                        'checkout': checkout_str,
                        'quantidade_hospedes': quarto.capacidade_pessoas
                    }
                }
            )
    except Exception as e:
        print("Erro ao registrar carrinho no analytics:", e)
        
    return JsonResponse({'success': True})

def carrinho_remover(request):
    if 'carrinho' in request.session:
        del request.session['carrinho']
        request.session.modified = True
    
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')
    return redirect('hoteis:home')

@require_POST
def carrinho_salvar_fnrh(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    try:
        idx = int(request.GET.get('idx', 0))
    except ValueError:
        idx = 0
        
    quantidade = carrinho_data.get('quantidade_hospedes', 1)
    if idx < 0 or idx >= quantidade:
        return JsonResponse({'success': False, 'error': 'Índice de hóspede inválido.'}, status=400)
        
    hospedes = carrinho_data.get('hospedes', [{}])
    while len(hospedes) < quantidade:
        hospedes.append({})
    while len(hospedes) > quantidade:
        hospedes.pop()
        
    nome = request.POST.get('hospede_nome', '').strip()
    cpf = request.POST.get('hospede_cpf', '').strip()
    email = request.POST.get('hospede_email', '').strip()
    telefone = request.POST.get('hospede_telefone', '').strip()
    rg = request.POST.get('hospede_rg', '').strip()
    nacionalidade = request.POST.get('hospede_nacionalidade', 'Brasileira').strip()
    profissao = request.POST.get('hospede_profissao', '').strip()
    cep = request.POST.get('hospede_cep', '').strip()
    endereco = request.POST.get('hospede_endereco', '').strip()
    
    # Validação condicional com base no tipo de hóspede (titular vs acompanhante)
    if idx == 0:
        if not all([nome, cpf, email, telefone, cep, endereco]):
            return JsonResponse({'success': False, 'error': 'Preencha todos os campos obrigatórios do hóspede principal.'}, status=400)
        
        fnrh = {
            'nome': nome,
            'cpf': cpf,
            'email': email,
            'telefone': telefone,
            'rg': rg,
            'nacionalidade': nacionalidade,
            'profissao': profissao,
            'cep': cep,
            'endereco': endereco
        }
    else:
        # Se vier 100% em branco, permite salvar vazio
        if not nome and not cpf and not email and not telefone and not rg and not cep and not endereco:
            fnrh = {}
        elif not all([nome, cpf]):
            return JsonResponse({'success': False, 'error': 'Preencha todos os campos obrigatórios (Nome e CPF) do acompanhante.'}, status=400)
        else:
            fnrh = {
                'nome': nome,
                'cpf': cpf,
                'email': email,
                'telefone': telefone,
                'rg': rg,
                'nacionalidade': nacionalidade,
                'profissao': profissao,
                'cep': cep,
                'endereco': endereco
            }
    
    hospedes[idx] = fnrh
    carrinho_data['hospedes'] = hospedes
    
    # Salvar veículo de forma integrada se idx == 0 (hóspede titular)
    if idx == 0:
        veiculo_placa = request.POST.get('veiculo_placa', '').strip().upper()
        veiculo_modelo = request.POST.get('veiculo_modelo', '').strip()
        veiculo_cor = request.POST.get('veiculo_cor', '').strip()
        
        if veiculo_placa:
            carrinho_data['veiculo'] = {
                'placa': veiculo_placa,
                'modelo': veiculo_modelo,
                'cor': veiculo_cor
            }
        else:
            carrinho_data['veiculo'] = {
                'placa': '',
                'modelo': '',
                'cor': ''
            }
            
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    # Ligar FNRH salva do usuário no perfil principal da conta (apenas para o titular se o campo estiver vazio)
    if idx == 0 and request.user.is_authenticated:
        from clientes.models import ClientePerfil
        try:
            perfil, _ = ClientePerfil.objects.get_or_create(user=request.user)
            if cpf and not perfil.cpf:
                perfil.cpf = cpf
            if telefone and not perfil.telefone:
                perfil.telefone = telefone
            if cep and not perfil.cep:
                perfil.cep = cep
            if endereco and not perfil.endereco:
                perfil.endereco = endereco
            perfil.save()
        except Exception as e:
            pass
            
    return JsonResponse({'success': True})


@require_POST
def carrinho_definir_hospedes(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Quantidade inválida.'}, status=400)
        
    quarto_id = carrinho_data.get('quarto_id')
    quarto = get_object_or_404(Quarto, id=quarto_id)
    
    if quantidade < 1 or quantidade > quarto.capacidade_pessoas:
        return JsonResponse({
            'success': False, 
            'error': f'A quantidade de hóspedes deve ser entre 1 e {quarto.capacidade_pessoas}.'
        }, status=400)
        
    carrinho_data['quantidade_hospedes'] = quantidade
    hospedes = carrinho_data.get('hospedes', [{}])
    
    # Ajusta o tamanho da lista de hóspedes na sessão
    while len(hospedes) < quantidade:
        hospedes.append({})
    while len(hospedes) > quantidade:
        hospedes.pop()
        
    carrinho_data['hospedes'] = hospedes
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')
        
    return JsonResponse({'success': True})


@require_POST
def carrinho_salvar_veiculo(request):
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        return JsonResponse({'success': False, 'error': 'Seu carrinho está vazio.'}, status=400)
        
    placa = request.POST.get('placa', '').strip().upper()
    modelo = request.POST.get('modelo', '').strip()
    cor = request.POST.get('cor', '').strip()
    
    if not placa:
        veiculo = {'placa': '', 'modelo': '', 'cor': ''}
    else:
        veiculo = {
            'placa': placa,
            'modelo': modelo,
            'cor': cor
        }
        
    carrinho_data['veiculo'] = veiculo
    request.session['carrinho'] = carrinho_data
    request.session.modified = True
    
    return JsonResponse({'success': True})


@login_required
def checkout_processar(request):
    import json
    import uuid
    import requests
    from django.conf import settings
    
    carrinho_data = request.session.get('carrinho')
    if not carrinho_data:
        if request.method == 'POST' or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': 'Seu carrinho de compras está vazio.'}, status=400)
        messages.error(request, 'Seu carrinho de compras está vazio.')
        return redirect('hoteis:home')
        
    quantidade_hospedes = carrinho_data.get('quantidade_hospedes', 1)
    hospedes = carrinho_data.get('hospedes', [{}])
    
    # Garantir que a lista de hóspedes esteja correta
    while len(hospedes) < quantidade_hospedes:
        hospedes.append({})
    while len(hospedes) > quantidade_hospedes:
        hospedes.pop()
        
    required_titular = ['nome', 'cpf', 'email', 'telefone', 'cep', 'endereco']
    required_acompanhante = ['nome', 'cpf']
    
    for idx, h in enumerate(hospedes):
        if idx == 0:
            if not all(h.get(f) for f in required_titular):
                if request.method == 'POST':
                    return JsonResponse({'success': False, 'error': 'Preencha todos os dados obrigatórios do hóspede titular antes de finalizar.'}, status=400)
                messages.error(request, 'Preencha todos os dados obrigatórios do hóspede titular antes de finalizar.')
                return redirect('hoteis:home')
        else:
            # Acompanhante é opcional se estiver completamente vazio.
            # Mas se tiver qualquer dado preenchido, deve obrigatoriamente preencher Nome e CPF.
            h_tem_dados = any(h.get(f) for f in ['nome', 'cpf', 'email', 'telefone', 'rg', 'nacionalidade', 'profissao', 'cep', 'endereco'])
            if h_tem_dados:
                if not all(h.get(f) for f in required_acompanhante):
                    if request.method == 'POST':
                        return JsonResponse({'success': False, 'error': f'Preencha todos os dados obrigatórios (Nome e CPF) do acompanhante {idx + 1} antes de finalizar.'}, status=400)
                    messages.error(request, f'Preencha todos os dados obrigatórios (Nome e CPF) do acompanhante {idx + 1} antes de finalizar.')
                    return redirect('hoteis:home')
            
    quarto_id = carrinho_data['quarto_id']
    quarto = get_object_or_404(Quarto, id=quarto_id)
    
    try:
        checkin = datetime.strptime(carrinho_data['checkin'], '%Y-%m-%d').date()
        checkout = datetime.strptime(carrinho_data['checkout'], '%Y-%m-%d').date()
    except ValueError:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'Datas inválidas no carrinho.'}, status=400)
        messages.error(request, 'Datas inválidas no carrinho.')
        return redirect('hoteis:home')
        
    # Calcular valores financeiros
    noites = (checkout - checkin).days
    if noites <= 0:
        noites = 1
        
    from sas.financeiro import calcular_taxas_reserva
    fin = calcular_taxas_reserva(quarto.hotel.empresa, 'hospedagem', quarto.preco, noites)
    
    if request.method == 'GET':
        # Renderizar a página de checkout pagamento
        context = {
            'carrinho': carrinho_data,
            'quarto': quarto,
            'noites': noites,
            'financeiro': fin,
            'checkin_date': checkin,
            'checkout_date': checkout,
            'mp_public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', ''),
        }
        return render(request, 'hoteis/checkout_pagamento.html', context)
        
    elif request.method == 'POST':
        print("POST REQUEST RECEIVED IN CHECKOUT_PROCESSAR!", flush=True)
        try:
            data = json.loads(request.body)
            print("DATA RECEIVED:", data, flush=True)
        except Exception as e:
            print("ERROR PARSING JSON:", e, flush=True)
            return JsonResponse({'success': False, 'error': 'Formato de payload inválido.'}, status=400)
            
        forma_pagamento = data.get('forma_pagamento')
        if forma_pagamento not in ['cartao', 'pix']:
            return JsonResponse({'success': False, 'error': 'Selecione uma forma de pagamento válida.'}, status=400)
            
        # 1. Verificar e alocar UnidadeQuarto física livre para prevenir overbooking
        unidades = quarto.unidades.filter(ativa=True)
        unidade_alocada = None
        
        from hoteis.utils import verifica_disponibilidade_unidade
        for uni in unidades:
            if verifica_disponibilidade_unidade(uni, checkin, checkout):
                unidade_alocada = uni
                break
                
        if not unidade_alocada:
            return JsonResponse({'success': False, 'error': 'Desculpe, a acomodação escolhida não possui mais vagas físicas disponíveis para este período.'}, status=400)
            
        # 2. Conectar ao Mercado Pago (API de Pagamentos Transparente /v1/payments)
        url_mp = "https://api.mercadopago.com/v1/payments"
        headers = {
            "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        }
        
        titular_fnrh = hospedes[0]
        cpf_limpo = titular_fnrh['cpf'].replace(".", "").replace("-", "").replace(" ", "").strip()
        
        # Estrutura base do payer
        payer_email = titular_fnrh['email']
        if settings.DEBUG and not payer_email.endswith('@testuser.com'):
            payer_email = "TESTUSER6095556049045318276@testuser.com"
 
        payer = {
            "email": payer_email,
            "first_name": titular_fnrh['nome'].split()[0],
            "last_name": " ".join(titular_fnrh['nome'].split()[1:]) or "Silva",
            "identification": {
                "type": "CPF",
                "number": cpf_limpo
            }
        }
        
        # Estrutura de pagamento segundo a API /v1/payments do Mercado Pago
        amount_total = float(fin['total_cliente'])
        
        payload_mp = {
            "transaction_amount": amount_total,
            "description": f"Reserva de Acomodação - {quarto.nome}",
            "external_reference": f"reserva_{quarto.id}",
            "payer": payer
        }
        
        if forma_pagamento == 'cartao':
            token = data.get('token')
            installments = int(data.get('installments', 1))
            payment_method_id = data.get('payment_method_id')
            
            if not token:
                return JsonResponse({'success': False, 'error': 'Token do cartão de crédito não foi gerado.'}, status=400)
                
            payload_mp.update({
                "token": token,
                "installments": installments,
                "payment_method_id": payment_method_id
            })
        elif forma_pagamento == 'pix':
            payload_mp.update({
                "payment_method_id": "pix"
            })
            
        # Inserir Split de Pagamento caso o parceiro tenha conta conectada
        conexao_mp = None
        if quarto.hotel and quarto.hotel.empresa and hasattr(quarto.hotel.empresa, 'mp_conexao'):
            conexao_mp = quarto.hotel.empresa.mp_conexao
            
        if conexao_mp:
            payload_mp.update({
                "application_fee": float(fin['taxa_servico']),
                "splits": [
                    {
                        "collector_id": int(conexao_mp.mp_user_id),
                        "amount": float(fin['repasse_parceiro'])
                    }
                ]
            })
            
        try:
            print("MERCADO PAGO REQUEST URL:", url_mp, flush=True)
            print("MERCADO PAGO PAYLOAD:", json.dumps(payload_mp, indent=2), flush=True)
            response = requests.post(url_mp, headers=headers, json=payload_mp, timeout=15)
            resp_data = response.json()
            print("MERCADO PAGO RESPONSE STATUS:", response.status_code, flush=True)
            print("MERCADO PAGO RESPONSE BODY:", json.dumps(resp_data, indent=2), flush=True)
        except Exception as e:
            print("MERCADO PAGO EXCEPTION:", e, flush=True)
            return JsonResponse({'success': False, 'error': f'Falha na comunicação com o gateway de pagamento: {str(e)}'}, status=500)
            
        if response.status_code not in [200, 201]:
            error_message = resp_data.get('message', 'Erro desconhecido no gateway de pagamento.')
            if 'cause' in resp_data and resp_data['cause']:
                error_message = resp_data['cause'][0].get('description', error_message)
            return JsonResponse({'success': False, 'error': f'Pagamento Recusado: {error_message}'}, status=400)
            
        status_pagamento_raw = resp_data.get('status')
        status_detail = resp_data.get('status_detail')
        
        if status_pagamento_raw == 'processed':
            status_pagamento = 'approved'
        elif status_pagamento_raw == 'action_required':
            status_pagamento = 'pending'
        else:
            status_pagamento = status_pagamento_raw
        
        # Pix fica 'pending', cartão deve estar 'approved'
        if forma_pagamento == 'cartao' and status_pagamento != 'approved':
            return JsonResponse({'success': False, 'error': f'O pagamento foi recusado pelo banco. Detalhe: {status_detail}'}, status=400)
            
        # 3. Criar a Reserva no Banco
        status_reserva = 'confirmada' if status_pagamento == 'approved' else 'pendente'
        reserva = Reserva.objects.create(
            usuario=request.user,
            unidade=unidade_alocada,
            data_checkin=checkin,
            data_checkout=checkout,
            subtotal=fin['subtotal'],
            taxas=fin['taxa_servico'],
            valor_total=fin['total_cliente'],
            taxa_servico_plataforma=fin['taxa_servico'],
            taxa_gateway=fin['taxa_gateway'],
            repasse_parceiro=fin['repasse_parceiro'],
            ganho_liquido_plataforma=fin['ganho_liquido'],
            status=status_reserva,
            canal_venda='marketplace',
            hospede_nome=titular_fnrh['nome'],
            hospede_cpf=titular_fnrh['cpf'],
            hospede_email=titular_fnrh['email'],
            hospede_telefone=titular_fnrh['telefone'],
            hospede_rg=titular_fnrh.get('rg', ''),
            hospede_nacionalidade=titular_fnrh.get('nacionalidade', 'Brasileira'),
            hospede_profissao=titular_fnrh.get('profissao', ''),
            hospede_endereco=f"{titular_fnrh['endereco']} (CEP: {titular_fnrh['cep']})",
            quantidade_hospedes=quantidade_hospedes
        )
        
        # Criar registros de HospedeReserva para todos
        for idx, h in enumerate(hospedes):
            if idx > 0 and not h.get('nome'):
                continue
                
            endereco_completo = h.get('endereco', '')
            if h.get('cep'):
                endereco_completo = f"{endereco_completo} (CEP: {h['cep']})".strip()
                
            HospedeReserva.objects.create(
                reserva=reserva,
                ordem=idx + 1,
                nome=h['nome'],
                cpf=h['cpf'],
                email=h.get('email', ''),
                telefone=h.get('telefone', ''),
                rg=h.get('rg', ''),
                nacionalidade=h.get('nacionalidade', 'Brasileira'),
                profissao=h.get('profissao', ''),
                endereco=endereco_completo
            )
            
        # Criar VeiculoReserva se placa informada
        veiculo_data = carrinho_data.get('veiculo', {})
        if veiculo_data and veiculo_data.get('placa'):
            VeiculoReserva.objects.create(
                reserva=reserva,
                placa=veiculo_data['placa'].upper(),
                modelo=veiculo_data.get('modelo', ''),
                cor=veiculo_data.get('cor', '')
            )
            
        # Criar o Voucher Universal Naviê
        from vouchers.models import Voucher
        # Obfuscate CPF para cache de portaria
        cpf_limpo = titular_fnrh['cpf'].replace(".", "").replace("-", "").replace(" ", "").strip()
        cpf_ocultado = f"***.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-**" if len(cpf_limpo) == 11 else "USER-UNKNOWN"

        Voucher.objects.create(
            empresa=quarto.hotel.empresa,
            tipo='hospedagem',
            object_id=str(reserva.id),
            codigo_seguro=f"VALIDA-RESERVA-{reserva.id}-{unidade_alocada.identificador}-{cpf_ocultado}",
            titulo_exibicao=f"{unidade_alocada.identificador} ({quarto.nome})",
            subtitulo_exibicao=quarto.hotel.nome,
            nome_beneficiario=titular_fnrh['nome'],
            documento_beneficiario=cpf_ocultado,
            detalhes_json={
                'checkin': checkin.strftime('%d/%m/%Y'),
                'checkout': checkout.strftime('%d/%m/%Y'),
                'noites': noites,
                'reserva_id': str(reserva.id)
            }
        )
            
        # Rastrear recuperação de carrinho e registrar consumo no analytics
        try:
            from analytics.models import CarrinhoStatus
            from analytics.analytics import registrar_consumo_unificado
            tracker_id = getattr(request, 'tracker_id', None)
            if tracker_id:
                # 1. Marcar carrinho como recuperado
                CarrinhoStatus.objects.filter(
                    tracker_id=tracker_id,
                    category='hospedagem',
                    item_id=str(quarto.id),
                    recuperado=False
                ).update(recuperado=True, usuario=request.user)
                
                # 2. Registrar consumo da reserva
                registrar_consumo_unificado(
                    usuario=request.user,
                    tracker_id=tracker_id,
                    category='hospedagem',
                    item_id=str(quarto.id),
                    nome=f"Reserva {quarto.nome} - {quarto.hotel.nome} ({noites} noites)",
                    preco=reserva.valor_total,
                    quantidade=1
                )
        except Exception as e:
            print("Erro ao atualizar analytics no checkout:", e)

        # 4. Limpar o carrinho
        if 'carrinho' in request.session:
            del request.session['carrinho']
            request.session.modified = True
            
        # Retornar dados de sucesso
        ret_data = {
            'success': True,
            'reserva_id': str(reserva.id),
            'redirect_url': request.build_absolute_uri(f'/carrinho/sucesso/{reserva.id}/')
        }
        
        # Inserir payload Pix para o front-end se aplicável
        if forma_pagamento == 'pix':
            try:
                # Com a API de Pagamentos (/v1/payments), a estrutura do Pix vem sob point_of_interaction
                point_of_interaction = resp_data.get('point_of_interaction', {})
                transaction_data = point_of_interaction.get('transaction_data', {})
                qr_code = transaction_data.get('qr_code')
                qr_code_base64 = transaction_data.get('qr_code_base64')
                
                # Suporte para a resposta mockada do teste (que usa a estrutura de Orders)
                if not qr_code:
                    try:
                        payment_method_info = resp_data['transactions']['payments'][0]['payment_method']
                        qr_code = payment_method_info['qr_code']
                        qr_code_base64 = payment_method_info['qr_code_base64']
                    except Exception:
                        pass
                
                if qr_code:
                    ret_data.update({
                        'forma_pagamento': 'pix',
                        'pix_qr_code': qr_code,
                        'pix_qr_code_base64': qr_code_base64
                    })
                    # Salvar detalhes do Pix na sessão para a página de sucesso
                    request.session['pix_pendente'] = {
                        'reserva_id': str(reserva.id),
                        'qr_code': qr_code,
                        'qr_code_base64': qr_code_base64
                    }
                    request.session.modified = True
            except Exception as e:
                print("Erro ao extrair dados do Pix da API de Pagamentos:", e)
                
        return JsonResponse(ret_data)

@login_required
def checkout_sucesso(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Verificar se existem metadados do Pix salvos na sessão para esta reserva
    pix_data = None
    session_pix = request.session.get('pix_pendente')
    if session_pix and session_pix.get('reserva_id') == str(reserva.id):
        pix_data = session_pix
        
    return render(request, 'hoteis/checkout_sucesso.html', {
        'reserva': reserva,
        'hotel': reserva.unidade.quarto.hotel,
        'pix_data': pix_data
    })

@login_required(login_url='hoteis:partner_login')
def partner_reserva_criar(request):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    
    hotel = request.user.perfil_parceiro.hotel
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    
    if request.method == 'POST':
        unidade_id = request.POST.get('unidade_id')
        data_checkin_str = request.POST.get('data_checkin')
        data_checkout_str = request.POST.get('data_checkout')
        valor_total_str = request.POST.get('valor_total', '0.00').strip()
        if ',' in valor_total_str:
            valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
        status = request.POST.get('status', 'pendente')
        quantidade_hospedes = int(request.POST.get('quantidade_hospedes', '1'))
        
        unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
        
        # Parse datas
        from datetime import datetime
        try:
            d_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
            d_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">Formato de datas inválido. Use AAAA-MM-DD.</div>', status=400)
            
        if d_checkout <= d_checkin:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">A data de checkout deve ser posterior ao checkin.</div>', status=400)
            
        # Validar conflitos de reservas
        conflitos = Reserva.objects.filter(
            unidade=unidade,
            data_checkin__lt=d_checkout,
            data_checkout__gt=d_checkin
        ).exclude(status='cancelada')
        
        if conflitos.exists():
            return HttpResponse(f'<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O quarto {unidade.identificador} já possui uma reserva ativa neste período.</div>', status=400)
            
        try:
            valor_total = float(valor_total_str)
        except ValueError:
            valor_total = 0.00
            
        # Pegar dados do hóspede titular (ordem=1)
        nome_1 = request.POST.get('nome_1', '').strip()
        cpf_1 = request.POST.get('cpf_1', '').strip()
        email_1 = request.POST.get('email_1', '').strip()
        telefone_1 = request.POST.get('telefone_1', '').strip()
        rg_1 = request.POST.get('rg_1', '').strip()
        nacionalidade_1 = request.POST.get('nacionalidade_1', 'Brasileira').strip()
        profissao_1 = request.POST.get('profissao_1', '').strip()
        endereco_1 = request.POST.get('endereco_1', '').strip()
        
        if not nome_1:
            return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O nome do Hóspede 1 (Titular) é obrigatório.</div>', status=400)
            
        # Criar reserva walk-in
        reserva = Reserva.objects.create(
            unidade=unidade,
            data_checkin=d_checkin,
            data_checkout=d_checkout,
            subtotal=valor_total,
            valor_total=valor_total,
            status=status,
            canal_venda='walk-in',
            quantidade_hospedes=quantidade_hospedes,
            hospede_nome=nome_1,
            hospede_cpf=cpf_1,
            hospede_email=email_1,
            hospede_telefone=telefone_1,
            hospede_rg=rg_1,
            hospede_nacionalidade=nacionalidade_1,
            hospede_profissao=profissao_1,
            hospede_endereco=endereco_1
        )
        
        # Registrar todos os hóspedes
        import re
        for i in range(1, quantidade_hospedes + 1):
            nome = request.POST.get(f'nome_{i}', '').strip()
            cpf = request.POST.get(f'cpf_{i}', '').strip()
            email = request.POST.get(f'email_{i}', '').strip()
            telefone = request.POST.get(f'telefone_{i}', '').strip()
            rg = request.POST.get(f'rg_{i}', '').strip()
            nacionalidade = request.POST.get(f'nacionalidade_{i}', 'Brasileira').strip()
            profissao = request.POST.get(f'profissao_{i}', '').strip()
            endereco = request.POST.get(f'endereco_{i}', '').strip()
            
            # Pular acompanhantes sem nome se quantidade informada exceder
            if i > 1 and not nome:
                continue
                
            docs_list = request.FILES.getlist(f'documentos_{i}')
            hospede = HospedeReserva.objects.create(
                reserva=reserva,
                ordem=i,
                nome=nome or f"Acompanhante {i}",
                cpf=cpf,
                email=email,
                telefone=telefone,
                rg=rg,
                nacionalidade=nacionalidade,
                profissao=profissao,
                endereco=endereco,
                documento_frente=docs_list[0] if len(docs_list) > 0 else None,
                documento_verso=docs_list[1] if len(docs_list) > 1 else None
            )
            
        # Registrar veículo se placa informada
        placa_1 = request.POST.get('placa_1', '').strip()
        if placa_1:
            VeiculoReserva.objects.create(
                reserva=reserva,
                placa=placa_1.upper(),
                modelo=request.POST.get('modelo_1', '').strip(),
                cor=request.POST.get('cor_1', '').strip()
            )
            
        response = HttpResponse("""
            <script>
                document.getElementById('modal-container').innerHTML = '';
                if (typeof window.triggerReservasRefresh === 'function') {
                    window.triggerReservasRefresh();
                }
            </script>
        """)
        return response
        
    # GET: renderizar formulário em branco
    from datetime import date, timedelta
    data_inicio = date.today()
    data_fim = data_inicio + timedelta(days=1)
    
    selected_unidade_id = request.GET.get('unidade_id')
    selected_unidade_label = "Selecione..."
    if selected_unidade_id:
        try:
            uni = UnidadeQuarto.objects.get(id=selected_unidade_id, quarto__hotel=hotel)
            selected_unidade_label = f"{uni.quarto.nome} - {uni.identificador}"
        except UnidadeQuarto.DoesNotExist:
            selected_unidade_id = None
            
    return render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': True,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': None,
        'hospedes': [],
        'veiculo': None,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'selected_unidade_id': selected_unidade_id,
        'selected_unidade_label': selected_unidade_label,
    })

@login_required(login_url='hoteis:partner_login')
def partner_reserva_detalhe(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    return render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo
    })

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_salvar(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    unidade_id = request.POST.get('unidade_id')
    data_checkin_str = request.POST.get('data_checkin')
    data_checkout_str = request.POST.get('data_checkout')
    valor_total_str = request.POST.get('valor_total', '0.00').strip()
    if ',' in valor_total_str:
        valor_total_str = valor_total_str.replace('.', '').replace(',', '.')
    status = request.POST.get('status', reserva.status)
    quantidade_hospedes = int(request.POST.get('quantidade_hospedes', '1'))
    
    unidade = get_object_or_404(UnidadeQuarto, id=unidade_id, quarto__hotel=hotel)
    
    # Parse datas
    from datetime import datetime
    try:
        d_checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d').date()
        d_checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">Formato de datas inválido. Use AAAA-MM-DD.</div>', status=400)
        
    if d_checkout <= d_checkin:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">A data de checkout deve ser posterior ao checkin.</div>', status=400)
        
    # Validar conflitos de reservas
    conflitos = Reserva.objects.filter(
        unidade=unidade,
        data_checkin__lt=d_checkout,
        data_checkout__gt=d_checkin
    ).exclude(id=reserva.id).exclude(status='cancelada')
    
    if conflitos.exists():
        return HttpResponse(f'<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O quarto {unidade.identificador} já possui uma reserva ativa neste período.</div>', status=400)
        
    try:
        valor_total = float(valor_total_str)
    except ValueError:
        valor_total = reserva.valor_total
        
    # Pegar dados do hóspede titular (ordem=1)
    nome_1 = request.POST.get('nome_1', '').strip()
    cpf_1 = request.POST.get('cpf_1', '').strip()
    email_1 = request.POST.get('email_1', '').strip()
    telefone_1 = request.POST.get('telefone_1', '').strip()
    rg_1 = request.POST.get('rg_1', '').strip()
    nacionalidade_1 = request.POST.get('nacionalidade_1', 'Brasileira').strip()
    profissao_1 = request.POST.get('profissao_1', '').strip()
    endereco_1 = request.POST.get('endereco_1', '').strip()
    
    if not nome_1:
        return HttpResponse('<div class="p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-xl">O nome do Hóspede 1 (Titular) é obrigatório.</div>', status=400)
        
    # Atualizar reserva
    reserva.unidade = unidade
    reserva.data_checkin = d_checkin
    reserva.data_checkout = d_checkout
    reserva.subtotal = valor_total
    reserva.valor_total = valor_total
    reserva.status = status
    reserva.quantidade_hospedes = quantidade_hospedes
    reserva.hospede_nome = nome_1
    reserva.hospede_cpf = cpf_1
    reserva.hospede_email = email_1
    reserva.hospede_telefone = telefone_1
    reserva.hospede_rg = rg_1
    reserva.hospede_nacionalidade = nacionalidade_1
    reserva.hospede_profissao = profissao_1
    reserva.hospede_endereco = endereco_1
    reserva.save()
    
    # Atualizar hóspedes
    import re
    for i in range(1, quantidade_hospedes + 1):
        nome = request.POST.get(f'nome_{i}', '').strip()
        cpf = request.POST.get(f'cpf_{i}', '').strip()
        email = request.POST.get(f'email_{i}', '').strip()
        telefone = request.POST.get(f'telefone_{i}', '').strip()
        rg = request.POST.get(f'rg_{i}', '').strip()
        nacionalidade = request.POST.get(f'nacionalidade_{i}', 'Brasileira').strip()
        profissao = request.POST.get(f'profissao_{i}', '').strip()
        endereco = request.POST.get(f'endereco_{i}', '').strip()
        
        if i > 1 and not nome:
            continue
            
        hospede, created = HospedeReserva.objects.get_or_create(reserva=reserva, ordem=i)
        hospede.nome = nome or f"Hóspede {i}"
        hospede.cpf = cpf
        hospede.email = email
        hospede.telefone = telefone
        hospede.rg = rg
        hospede.nacionalidade = nacionalidade
        hospede.profissao = profissao
        hospede.endereco = endereco
        
        if request.POST.get(f'delete_doc_frente_{i}') == 'true':
            hospede.documento_frente = None
        if request.POST.get(f'delete_doc_verso_{i}') == 'true':
            hospede.documento_verso = None

        docs_list = request.FILES.getlist(f'documentos_{i}')
        if len(docs_list) > 0:
            hospede.documento_frente = docs_list[0]
        if len(docs_list) > 1:
            hospede.documento_verso = docs_list[1]
            
        hospede.save()
        
    # Deletar acompanhantes sobressalentes
    reserva.hospedes.filter(ordem__gt=quantidade_hospedes).delete()
    
    # Atualizar veículo
    placa_1 = request.POST.get('placa_1', '').strip()
    if placa_1:
        veiculo, created = VeiculoReserva.objects.get_or_create(reserva=reserva)
        veiculo.placa = placa_1.upper()
        veiculo.modelo = request.POST.get('modelo_1', '').strip()
        veiculo.cor = request.POST.get('cor_1', '').strip()
        veiculo.save()
    else:
        VeiculoReserva.objects.filter(reserva=reserva).delete()
        
    response = HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            if (typeof window.triggerReservasRefresh === 'function') {
                window.triggerReservasRefresh();
            }
        </script>
    """)
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_checkin(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    # Toggle Check-in
    if reserva.status == 'hospedado' or reserva.status == 'concluido':
        # Unmark check-in: revert to 'confirmada' and clear timestamps
        reserva.status = 'confirmada'
        reserva.checkin_realizado_em = None
        reserva.checkout_realizado_em = None
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkin',
            detalhes=f"Check-in desmarcado pelo usuário {request.user.username}."
        )
    else:
        # Mark check-in
        reserva.status = 'hospedado'
        from django.utils import timezone
        reserva.checkin_realizado_em = timezone.now()
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkin',
            detalhes=f"Check-in realizado pelo usuário {request.user.username}."
        )
        
    # Render the modal form to keep it open with the updated state
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    response = render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'trigger_grid_update': True
    })
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_checkout(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    # Toggle Check-out
    if reserva.status == 'concluido':
        # Unmark check-out: revert to 'hospedado'
        reserva.status = 'hospedado'
        reserva.checkout_realizado_em = None
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='desmarcar_checkout',
            detalhes=f"Check-out desmarcado pelo usuário {request.user.username}."
        )
    else:
        # Mark check-out
        reserva.status = 'concluido'
        from django.utils import timezone
        reserva.checkout_realizado_em = timezone.now()
        reserva.save()
        # Log action
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user,
            acao='checkout',
            detalhes=f"Check-out realizado pelo usuário {request.user.username}."
        )
        
        # Criar tarefa de limpeza pós-checkout se não existir
        if not Tarefa.objects.filter(reserva=reserva, titulo__icontains="Limpeza").exists():
            Tarefa.objects.create(
                hotel=hotel,
                titulo=f"Limpeza e Preparação - {reserva.unidade.identificador}",
                descricao=f"Realizar limpeza pós-checkout da reserva #{str(reserva.id)[:8].upper()} do hóspede {reserva.hospede_nome}.",
                prioridade='alta',
                status='todo',
                unidade=reserva.unidade,
                reserva=reserva
            )
        
    # Render the modal form to keep it open with the updated state
    quartos = hotel.quartos.all()
    unidades = UnidadeQuarto.objects.filter(quarto__hotel=hotel, ativa=True)
    hospedes = list(reserva.hospedes.all().order_by('ordem'))
    try:
        veiculo = reserva.veiculo
    except Exception:
        veiculo = None
        
    response = render(request, 'hoteis/partials/modal_reserva_form.html', {
        'is_create': False,
        'hotel': hotel,
        'quartos': quartos,
        'unidades': unidades,
        'reserva': reserva,
        'hospedes': hospedes,
        'veiculo': veiculo,
        'trigger_grid_update': True
    })
    return response

@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_reserva_cancelar(request, reserva_id):
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
        
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    reserva.status = 'cancelada'
    reserva.save()
    
    # Log de cancelamento
    from .models import ReservaLog
    ReservaLog.objects.create(
        reserva=reserva,
        usuario=request.user,
        acao='cancelar',
        detalhes=f"Reserva cancelada pelo usuário {request.user.username}."
    )
    
    response = HttpResponse("""
        <script>
            document.getElementById('modal-container').innerHTML = '';
            // disparar atualização do grid
            const filtro = document.getElementById('filtro-periodo');
            if (filtro) {
                htmx.trigger(filtro, 'change');
            } else {
                window.location.reload();
            }
        </script>
    """)
    return response


@login_required(login_url='hoteis:partner_login')
def partner_hospedes_pedidos(request):
    """
    Retorna a lista de pedidos de quarto do hotel logado (útil para atualização assíncrona).
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    pedidos = PedidoServico.objects.filter(hotel=hotel).order_by('-criado_em')
    return render(request, 'hoteis/partials/pedidos_lista.html', {'pedidos_ativos': pedidos})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_hospedes_atualizar_status(request, pedido_id):
    """
    Atualiza o status de uma solicitação de hóspede e retorna o card unitário atualizado.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    pedido = get_object_or_404(PedidoServico, id=pedido_id, hotel=hotel)
    
    novo_status = request.POST.get('status')
    if novo_status in dict(PedidoServico.STATUS_CHOICES):
        pedido.status = novo_status
        pedido.save()
        
    return render(request, 'hoteis/partials/pedido_card.html', {'p': pedido})


@login_required(login_url='hoteis:partner_login')
@require_POST
def partner_hospedes_lancar_consumo(request, reserva_id):
    """
    Lança um item de consumo (frigobar/bomboniere) na conta da reserva e atualiza a grade de reservas.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Não autorizado", status=403)
    hotel = request.user.perfil_parceiro.hotel
    reserva = get_object_or_404(Reserva, id=reserva_id, unidade__quarto__hotel=hotel)
    
    produto_id = request.POST.get('produto_id')
    quantidade_str = request.POST.get('quantidade', '1')
    observacoes = request.POST.get('observacoes', '').strip()
    
    try:
        quantidade = int(quantidade_str)
    except ValueError:
        quantidade = 1
        
    produto = get_object_or_404(ProdutoConsumo, id=produto_id, hotel=hotel)
    valor_total = produto.preco * quantidade
    
    # Criar um pedido do tipo 'entregue' para faturamento do frigobar
    pedido = PedidoServico.objects.create(
        reserva=reserva,
        unidade=reserva.unidade,
        hotel=hotel,
        status='entregue',
        observacoes=observacoes or f"Consumo lançado pela recepção: {produto.nome}.",
        valor_total=valor_total
    )
    
    ItemPedidoServico.objects.create(
        pedido=pedido,
        produto=produto,
        quantidade=quantidade,
        preco_unitario=produto.preco
    )
    
    # Adicionar o consumo ao valor total da reserva
    reserva.valor_total += valor_total
    reserva.save()
    
    # Deduzir do estoque físico se estiver vinculado a um produto do almoxarifado e lançar no financeiro
    if produto.estoque_produto:
        from decimal import Decimal
        from estoque.models import MovimentoEstoque
        from financeiro.models import TransacaoFinanceira
        
        estoque_prod = produto.estoque_produto
        estoque_prod.estoque_atual -= Decimal(str(quantidade))
        estoque_prod.save()
        
        # Registrar movimento de estoque (Saída)
        MovimentoEstoque.objects.create(
            hotel=hotel,
            produto=estoque_prod,
            tipo='saida',
            quantidade=Decimal(str(quantidade)),
            referencia=f"Consumo Reserva #{str(reserva.id)[:8]} (Quarto {reserva.unidade.identificador})",
            criado_por=request.user if request.user.is_authenticated else None
        )
        
        # Lançar automaticamente no financeiro
        TransacaoFinanceira.objects.create(
            hotel=hotel,
            tipo='receita',
            categoria='frigobar',
            valor=valor_total,
            descricao=f"Consumo: {quantidade}x {produto.nome} (Reserva: {str(reserva.id)[:8]} - Quarto {reserva.unidade.identificador})",
            data_vencimento=date.today(),
            data_pagamento=date.today(),
            criado_por=request.user if request.user.is_authenticated else None
        )
    
    # Registrar consumo unificado no analytics
    try:
        from analytics.analytics import registrar_consumo_unificado
        if reserva.usuario:
            registrar_consumo_unificado(
                usuario=reserva.usuario,
                tracker_id=None,
                category='hospedagem',
                item_id=str(produto.id),
                nome=produto.nome,
                preco=produto.preco,
                quantidade=quantidade
            )
    except Exception as e:
        print("Erro ao lançar consumo no analytics:", e)
    
    # Log de auditoria
    try:
        ReservaLog.objects.create(
            reserva=reserva,
            usuario=request.user if request.user.is_authenticated else None,
            acao='consumo_lancado',
            detalhes=f"Lançado consumo de {quantidade}x {produto.nome} (Total: R$ {valor_total})."
        )
    except Exception:
        pass
    
    # Resposta com feedback e atualização do grid B2B em background
    return HttpResponse(f"""
        <div id="lancar-consumo-feedback" class="p-3 mb-3 text-xs text-green-800 bg-green-50 rounded-xl border border-green-500/20">
            Lançado com sucesso! R$ {valor_total} adicionados ao quarto {reserva.unidade.identificador}.
        </div>
        <script>
            if (typeof window.triggerReservasRefresh === 'function') {{
                window.triggerReservasRefresh();
            }}
            setTimeout(() => {{
                document.getElementById('lancar-consumo-feedback')?.remove();
            }}, 3500);
        </script>
    """)


def api_verificar_subdominio(request):
    slug = request.GET.get('slug', '').strip().lower().replace(' ', '-')
    exclude_id = request.GET.get('exclude_id')
    
    if not slug:
        return JsonResponse({'disponivel': False, 'mensagem': 'Subdomínio não pode ser vazio.'})
    
    reservados = ['admin', 'accounts', 'api', 'clientes', 'hospedagens', 'hotelaria', 'static', 'media', 'www', 'dashboard', 'navievibe']
    if slug in reservados:
        return JsonResponse({'disponivel': False, 'mensagem': 'Este termo é reservado pelo sistema.'})
        
    qs = Hotel.objects.filter(slug=slug)
    if exclude_id and exclude_id != 'None' and exclude_id != '':
        try:
            qs = qs.exclude(id=int(exclude_id))
        except ValueError:
            pass
            
    if qs.exists():
        return JsonResponse({'disponivel': False, 'mensagem': 'Este subdomínio já está em uso.'})
        
    return JsonResponse({'disponivel': True, 'mensagem': 'Subdomínio disponível!'})


def quarto_detalhe_subdomain(request, quarto_slug):
    hotel = getattr(request, 'hotel_atual', None)
    if not hotel:
        from hoteis.models import Quarto
        quarto = Quarto.objects.filter(slug=quarto_slug).first()
        if quarto:
            hotel = quarto.hotel
        else:
            return redirect('hoteis:home')
    return quarto_detalhe(request, hotel.id, quarto_slug)


def api_buscar_quartos(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    # 1. Recuperar parâmetros
    datas_str = request.GET.get('datas', '').strip() # formato: "DD/MM/YYYY - DD/MM/YYYY" ou "DD/MM/YYYY a DD/MM/YYYY"
    guests_str = request.GET.get('guests', '2').strip()
    
    # Defaults
    guests = 2
    try:
        if 'ou mais' in guests_str:
            guests = 8
        else:
            # Pegar apenas o número do texto se necessário
            import re
            nums = re.findall(r'\d+', guests_str)
            if nums:
                guests = int(nums[0])
            else:
                guests = int(guests_str)
    except ValueError:
        pass
        
    checkin = None
    checkout = None
    
    # Parser de datas flexível
    if datas_str:
        parts = []
        if " - " in datas_str:
            parts = datas_str.split(" - ")
        elif " a " in datas_str:
            parts = datas_str.split(" a ")
        elif " to " in datas_str:
            parts = datas_str.split(" to ")
            
        if len(parts) == 2:
            try:
                checkin = datetime.strptime(parts[0].strip(), '%d/%m/%Y').date()
                checkout = datetime.strptime(parts[1].strip(), '%d/%m/%Y').date()
            except ValueError:
                pass
                
    if not checkin or not checkout:
        return HttpResponse("""
            <div class="mb-12 pt-4 border-b border-slate-100 pb-10" id="resultados-busca-secao">
                <div class="max-w-2xl mx-auto bg-slate-50 border border-slate-200 rounded-3xl p-8 text-center shadow-sm">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path></svg>
                    </div>
                    <h4 class="text-lg font-black text-slate-800">Selecione o período corretamente</h4>
                    <p class="text-xs text-slate-500 mt-2 leading-relaxed">
                        Por favor, selecione as datas de entrada (check-in) e saída (checkout) para pesquisar acomodações.
                    </p>
                </div>
            </div>
        """)
        
    # Verificar disponibilidade
    noites = (checkout - checkin).days
    if noites <= 0:
        return HttpResponse("""
            <div class="mb-12 pt-4 border-b border-slate-100 pb-10" id="resultados-busca-secao">
                <div class="max-w-2xl mx-auto bg-slate-50 border border-slate-200 rounded-3xl p-8 text-center shadow-sm">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path></svg>
                    </div>
                    <h4 class="text-lg font-black text-slate-800">Datas inválidas</h4>
                    <p class="text-xs text-slate-500 mt-2 leading-relaxed">
                        A data de saída (checkout) deve ser posterior à data de entrada (check-in).
                    </p>
                </div>
            </div>
        """)
        
    quartos_disponiveis = []
    
    # 2. Filtrar quartos e checar disponibilidade
    for q in hotel.quartos.all():
        # Verifica se comporta a quantidade de hóspedes
        if q.capacidade_pessoas >= guests:
            disponivel = checar_disponibilidade_quarto(q, checkin, checkout)
            if disponivel:
                quartos_disponiveis.append(q)
                
    # Lógica de recomendações se não houver quartos disponíveis
    quartos_capacidade_alternativa = []
    quartos_sugeridos = []
    if not quartos_disponiveis:
        # Recomendar quartos com capacidade menor na mesma data
        for q in hotel.quartos.all():
            if q.capacidade_pessoas < guests:
                if checar_disponibilidade_quarto(q, checkin, checkout):
                    quartos_capacidade_alternativa.append(q)
                    
        # Recomendar quartos com capacidade solicitada em datas alternativas
        from .utils import buscar_datas_proximas
        from datetime import timedelta
        for q in hotel.quartos.all():
            if q.capacidade_pessoas >= guests:
                sugestao_antes, sugestao_depois = buscar_datas_proximas(q, checkin, noites)
                if sugestao_antes or sugestao_depois:
                    quartos_sugeridos.append({
                        'quarto': q,
                        'sugestao_antes': sugestao_antes,
                        'sugestao_depois': sugestao_depois,
                        'sugestao_antes_checkout': (sugestao_antes + timedelta(days=noites)) if sugestao_antes else None,
                        'sugestao_depois_checkout': (sugestao_depois + timedelta(days=noites)) if sugestao_depois else None,
                    })

    context = {
        'hotel': hotel,
        'quartos_disponiveis': quartos_disponiveis,
        'quartos_capacidade_alternativa': quartos_capacidade_alternativa,
        'quartos_sugeridos': quartos_sugeridos,
        'checkin': checkin,
        'checkout': checkout,
        'guests': guests,
        'noites': noites,
    }
    
    return render(request, 'hoteis/partials/resultados_busca_quartos.html', context)


def api_buscar_quartos_grupo(request, empresa_id):
    from core.models import Empresa
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    # 1. Recuperar parâmetros
    datas_str = request.GET.get('datas', '').strip()
    guests_str = request.GET.get('guests', '2').strip()
    
    # Defaults
    guests = 2
    try:
        if 'ou mais' in guests_str:
            guests = 8
        else:
            import re
            nums = re.findall(r'\d+', guests_str)
            if nums:
                guests = int(nums[0])
            else:
                guests = int(guests_str)
    except ValueError:
        pass
        
    checkin = None
    checkout = None
    
    # Parser de datas flexível
    if datas_str:
        parts = []
        if " - " in datas_str:
            parts = datas_str.split(" - ")
        elif " a " in datas_str:
            parts = datas_str.split(" a ")
        elif " to " in datas_str:
            parts = datas_str.split(" to ")
            
        if len(parts) == 2:
            try:
                checkin = datetime.strptime(parts[0].strip(), '%d/%m/%Y').date()
                checkout = datetime.strptime(parts[1].strip(), '%d/%m/%Y').date()
            except ValueError:
                pass
                
    if not checkin or not checkout:
        return HttpResponse("""
            <div class="mb-12 pt-4 border-b border-slate-100 pb-10" id="resultados-busca-secao">
                <div class="max-w-2xl mx-auto bg-slate-50 border border-slate-200 rounded-3xl p-8 text-center shadow-sm">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path></svg>
                    </div>
                    <h4 class="text-lg font-black text-slate-800">Selecione o período corretamente</h4>
                    <p class="text-xs text-slate-500 mt-2 leading-relaxed">
                        Por favor, selecione as datas de entrada (check-in) e saída (checkout) para pesquisar acomodações.
                    </p>
                </div>
            </div>
        """)
        
    # Verificar disponibilidade
    noites = (checkout - checkin).days
    if noites <= 0:
        return HttpResponse("""
            <div class="mb-12 pt-4 border-b border-slate-100 pb-10" id="resultados-busca-secao">
                <div class="max-w-2xl mx-auto bg-slate-50 border border-slate-200 rounded-3xl p-8 text-center shadow-sm">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"></path></svg>
                    </div>
                    <h4 class="text-lg font-black text-slate-800">Datas inválidas</h4>
                    <p class="text-xs text-slate-500 mt-2 leading-relaxed">
                        A data de saída (checkout) deve ser posterior à data de entrada (check-in).
                    </p>
                </div>
            </div>
        """)
        
    quartos_disponiveis = []
    
    # 2. Filtrar quartos e checar disponibilidade de todas as pousadas da empresa
    pousadas = empresa.hoteis_ativos_ordenados
    for hotel in pousadas:
        for q in hotel.quartos.all():
            if q.capacidade_pessoas >= guests:
                disponivel = checar_disponibilidade_quarto(q, checkin, checkout)
                if disponivel:
                    quartos_disponiveis.append(q)
                    
    # Lógica de recomendações se não houver quartos disponíveis
    quartos_capacidade_alternativa = []
    quartos_sugeridos = []
    if not quartos_disponiveis:
        for hotel in pousadas:
            # Recomendar quartos com capacidade menor na mesma data
            for q in hotel.quartos.all():
                if q.capacidade_pessoas < guests:
                    if checar_disponibilidade_quarto(q, checkin, checkout):
                        quartos_capacidade_alternativa.append(q)
                        
            # Recomendar quartos com capacidade solicitada em datas alternativas
            from .utils import buscar_datas_proximas
            from datetime import timedelta
            for q in hotel.quartos.all():
                if q.capacidade_pessoas >= guests:
                    sugestao_antes, sugestao_depois = buscar_datas_proximas(q, checkin, noites)
                    if sugestao_antes or sugestao_depois:
                        quartos_sugeridos.append({
                            'quarto': q,
                            'sugestao_antes': sugestao_antes,
                            'sugestao_depois': sugestao_depois,
                            'sugestao_antes_checkout': (sugestao_antes + timedelta(days=noites)) if sugestao_antes else None,
                            'sugestao_depois_checkout': (sugestao_depois + timedelta(days=noites)) if sugestao_depois else None,
                        })

    # Usamos o primeiro hotel da empresa (se houver) como hotel de contexto principal ou None
    primeiro_hotel = pousadas[0] if len(pousadas) > 0 else None

    context = {
        'hotel': primeiro_hotel,
        'quartos_disponiveis': quartos_disponiveis,
        'quartos_capacidade_alternativa': quartos_capacidade_alternativa,
        'quartos_sugeridos': quartos_sugeridos,
        'checkin': checkin,
        'checkout': checkout,
        'guests': guests,
        'noites': noites,
    }
    
    return render(request, 'hoteis/partials/resultados_busca_quartos.html', context)


def teste_404(request):
    return render(request, '404.html')


@login_required
def partner_secao_salvar(request, secao_id=None):
    """
    Cria ou edita uma Seção do Hotel. Retorna para a aba de seções.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado.", status=403)
    
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        subtitulo = request.POST.get('subtitulo', '').strip()
        tipo = request.POST.get('tipo', 'texto_imagem')
        texto = request.POST.get('texto', '').strip()
        video_url = request.POST.get('video_url', '').strip()
        ordem = int(request.POST.get('ordem', 0) or 0)
        ativa = request.POST.get('ativa') == 'on' or 'ativa' in request.POST
        imagem = request.FILES.get('imagem')
        video = request.FILES.get('video')
        link_cta = request.POST.get('link_cta', '').strip()
        preco_raw = request.POST.get('preco', '').strip()
        
        if secao_id:
            secao = get_object_or_404(HotelSecao, id=secao_id, hotel=hotel)
        else:
            secao = HotelSecao(hotel=hotel)
            
        secao.titulo = titulo
        secao.subtitulo = subtitulo or None
        secao.tipo = tipo
        secao.texto = texto or None
        secao.video_url = video_url or None
        secao.ordem = ordem
        secao.ativa = ativa
        secao.link_cta = link_cta or None
        
        if preco_raw:
            try:
                secao.preco = Decimal(preco_raw.replace('R$', '').replace('.', '').replace(',', '.').strip())
            except Exception:
                secao.preco = None
        else:
            secao.preco = None
            
        # Limpeza de mídias e campos obsoletos por tipo de layout
        if secao.tipo not in ['texto_imagem', 'video']:
            if secao.imagem:
                try: secao.imagem.delete(save=False)
                except Exception: pass
                secao.imagem = None
            if secao.video:
                try: secao.video.delete(save=False)
                except Exception: pass
                secao.video = None
            secao.video_url = None
            secao.texto = None
            secao.preco = None
            secao.link_cta = None
        else:
            if imagem:
                if secao.video:
                    try: secao.video.delete(save=False)
                    except Exception: pass
                    secao.video = None
                secao.video_url = None
            elif video or video_url:
                if secao.imagem:
                    try: secao.imagem.delete(save=False)
                    except Exception: pass
                    secao.imagem = None
                if secao.tipo == 'video':
                    secao.texto = None

        if imagem and secao.tipo == 'texto_imagem':
            if secao.imagem:
                try: secao.imagem.delete(save=False)
                except Exception: pass
            secao.imagem = imagem
            
        if video and (secao.tipo == 'texto_imagem' or secao.tipo == 'video'):
            if secao.video:
                try: secao.video.delete(save=False)
                except Exception: pass
            secao.video = video
            
        secao.save()
        
        # Processar os 10 cards da galeria / itens secundários
        for idx in range(10):
            item_id = request.POST.get(f'item_{idx}_id')
            item_titulo = request.POST.get(f'item_{idx}_titulo', '').strip()
            item_media_type = request.POST.get(f'item_{idx}_media_type', 'imagem')
            item_remover = request.POST.get(f'item_{idx}_remover') == 'true'
            item_file = request.FILES.get(f'item_{idx}_file')
            
            if item_id or item_file or item_titulo:
                item = None
                if item_id:
                    item = HotelSecaoItem.objects.filter(id=item_id, secao=secao).first()
                if not item:
                    if item_remover:
                        continue
                    item = HotelSecaoItem(secao=secao, ordem=idx)
                
                if item_remover:
                    if item.imagem:
                        try: item.imagem.delete(save=False)
                        except Exception: pass
                    if item.video:
                        try: item.video.delete(save=False)
                        except Exception: pass
                    item.delete()
                    continue
                
                item.titulo = item_titulo or f"Mídia {idx+1}"
                item.ordem = idx
                
                if item_media_type == 'imagem':
                    if item_file:
                        if item.imagem:
                            try: item.imagem.delete(save=False)
                            except Exception: pass
                        item.imagem = item_file
                    if item.video:
                        try: item.video.delete(save=False)
                        except Exception: pass
                        item.video = None
                elif item_media_type == 'video':
                    if item_file:
                        if item.video:
                            try: item.video.delete(save=False)
                            except Exception: pass
                        item.video = item_file
                    if item.imagem:
                        try: item.imagem.delete(save=False)
                        except Exception: pass
                        item.imagem = None
                
                if item.imagem or item.video:
                    item.save()
        
        response = HttpResponse()
        response['HX-Redirect'] = '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes'
        return response
        
    return HttpResponse("Método inválido.", status=405)


@login_required
def partner_secao_destaques_salvar(request):
    """
    Salva a seção de destaques completa (título, subtítulo e seus 3 cards do Canvas editor)
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado.", status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', 'Três experiências inesquecíveis').strip()
        subtitulo = request.POST.get('subtitulo', '').strip()
        
        secao = HotelSecao.objects.filter(hotel=hotel, tipo='destaques').first()
        if not secao:
            secao = HotelSecao(hotel=hotel, tipo='destaques', ordem=0, ativa=True)
        
        secao.titulo = titulo
        secao.subtitulo = subtitulo or None
        secao.save()
        
        for idx in range(1, 4):
            item_id = request.POST.get(f'card_{idx}_id')
            c_titulo = request.POST.get(f'card_{idx}_titulo', '').strip()
            c_desc = request.POST.get(f'card_{idx}_descricao', '').strip()
            c_preco_raw = request.POST.get(f'card_{idx}_preco', '').strip()
            c_link = request.POST.get(f'card_{idx}_link_cta', '').strip()
            media_type = request.POST.get(f'card_{idx}_media_type', 'imagem')
            remover_media = request.POST.get(f'card_{idx}_remover_media') == 'true'
            
            c_imagem = request.FILES.get(f'card_{idx}_imagem')
            c_video = request.FILES.get(f'card_{idx}_video')
            
            item = None
            if item_id:
                item = HotelSecaoItem.objects.filter(id=item_id, secao=secao).first()
            if not item:
                item = HotelSecaoItem(secao=secao, ordem=idx)
            
            item.titulo = c_titulo or f"Card {idx}"
            item.descricao = c_desc or None
            item.link_cta = c_link or None
            
            if c_preco_raw:
                try:
                    item.preco = Decimal(c_preco_raw.replace('R$', '').replace('.', '').replace(',', '.').strip())
                except Exception:
                    item.preco = None
            else:
                item.preco = None
                
            if remover_media:
                if item.imagem:
                    item.imagem.delete(save=False)
                    item.imagem = None
                if item.video:
                    item.video.delete(save=False)
                    item.video = None
            
            if media_type == 'video':
                if c_video:
                    if item.video:
                        item.video.delete(save=False)
                    item.video = c_video
                if item.imagem:
                    item.imagem.delete(save=False)
                    item.imagem = None
            else:
                if c_imagem:
                    if item.imagem:
                        item.imagem.delete(save=False)
                    item.imagem = c_imagem
                if item.video:
                    item.video.delete(save=False)
                    item.video = None
                    
            item.save()
            
        response = HttpResponse()
        response['HX-Redirect'] = '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes'
        return response
        
    return HttpResponse("Método inválido.", status=405)


@login_required
@require_POST
def partner_secao_deletar(request, secao_id):
    """
    Deleta uma Seção do Hotel.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado.", status=403)
        
    perfil = request.user.perfil_parceiro
    secao = get_object_or_404(HotelSecao, id=secao_id, hotel=perfil.hotel)
    secao.delete()
    
    response = HttpResponse()
    response['HX-Redirect'] = '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes'
    return response


@login_required
def partner_secao_item_salvar(request, item_id=None):
    """
    Cria ou edita um item (atração/imagem) dentro de uma seção.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado.", status=403)
        
    perfil = request.user.perfil_parceiro
    hotel = perfil.hotel
    
    if request.method == 'POST':
        secao_id = request.POST.get('secao_id')
        secao = get_object_or_404(HotelSecao, id=secao_id, hotel=hotel)
        
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        preco_str = request.POST.get('preco', '').strip()
        link_cta = request.POST.get('link_cta', '').strip()
        media_type = request.POST.get('media_type', 'imagem')
        imagem = request.FILES.get('imagem')
        video = request.FILES.get('video')
        ordem = int(request.POST.get('ordem', 0) or 0)
        
        preco = None
        if preco_str:
            try:
                preco = Decimal(preco_str.replace(',', '.'))
            except Exception:
                pass
                
        if item_id:
            item = get_object_or_404(HotelSecaoItem, id=item_id, secao__hotel=hotel)
        else:
            item = HotelSecaoItem(secao=secao)
            
        item.titulo = titulo
        item.descricao = descricao or None
        item.preco = preco
        item.link_cta = link_cta or None
        item.ordem = ordem
        
        if media_type == 'imagem':
            if imagem:
                if item.imagem:
                    try:
                        item.imagem.delete(save=False)
                    except Exception:
                        pass
                item.imagem = imagem
            if item.video:
                try:
                    item.video.delete(save=False)
                except Exception:
                    pass
                item.video = None
        elif media_type == 'video':
            if video:
                if item.video:
                    try:
                        item.video.delete(save=False)
                    except Exception:
                        pass
                item.video = video
            if item.imagem:
                try:
                    item.imagem.delete(save=False)
                except Exception:
                    pass
                item.imagem = None
            
        item.save()
        
        response = HttpResponse()
        response['HX-Redirect'] = '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes'
        return response
        
    return HttpResponse("Método inválido.", status=405)


@login_required
@require_POST
def partner_secao_item_deletar(request, item_id):
    """
    Deleta um item da seção.
    """
    if not hasattr(request.user, 'perfil_parceiro'):
        return HttpResponse("Acesso negado.", status=403)
        
    perfil = request.user.perfil_parceiro
    item = get_object_or_404(HotelSecaoItem, id=item_id, secao__hotel=perfil.hotel)
    item.delete()
    
    response = HttpResponse()
    response['HX-Redirect'] = '/hospedagens/sistema/?tab=configuracoes&config_tab=secoes'
    return response


def portal_grupo(request, slug=None):
    from core.models import Empresa
    from hoteis.models import Hotel
    import re
    
    # 1. Resolve a Empresa pelo slug (da URL ou do middleware)
    empresa_atual = getattr(request, 'empresa_atual', None)
    if not empresa_atual and slug:
        empresa_atual = get_object_or_404(Empresa, slug=slug, modalidade_portal='unificado')
        
    if not empresa_atual:
        # Se não houver empresa, redireciona para a home do marketplace
        return redirect('hoteis:home')
        
    empresa_atual.visualizacoes += 1
    empresa_atual.save(update_fields=['visualizacoes'])
    
    # 2. Busca todas as pousadas ativas da empresa ordenadas
    pousadas = empresa_atual.hoteis_ativos_ordenados
    
    # 3. Busca disponibilidade se datas forem fornecidas na busca
    datas_str = request.GET.get('datas', '').strip()
    guests_str = request.GET.get('guests', '2 Hóspedes').strip()
    
    # Resolver hóspedes
    guests = 2
    try:
        nums = re.findall(r'\d+', guests_str)
        if nums:
            guests = int(nums[0])
    except Exception:
        pass
        
    filtros_ativos = False
    checkin = None
    checkout = None
    
    if datas_str:
        try:
            # Formatos suportados: "DD/MM/YYYY - DD/MM/YYYY" ou "DD/MM/YYYY a DD/MM/YYYY"
            parts = re.split(r'\s+-\s+|\s+a\s+', datas_str)
            if len(parts) == 2:
                from datetime import datetime
                checkin = datetime.strptime(parts[0].strip(), '%d/%m/%Y').date()
                checkout = datetime.strptime(parts[1].strip(), '%d/%m/%Y').date()
                filtros_ativos = True
        except Exception:
            pass
            
    # Montar dados estruturados para cada pousada
    pousadas_data = []
    for pousada in pousadas:
        pousada.visualizacoes += 1
        pousada.save(update_fields=['visualizacoes'])
        
        # Filtra quartos da pousada
        quartos_qs = pousada.quartos.all()
        
        # Filtrar quartos disponíveis caso datas tenham sido especificadas
        quartos_disponiveis = []
        for quarto in quartos_qs:
            # Validar capacidade de hóspedes
            if quarto.capacidade_pessoas < guests:
                continue
                
            if filtros_ativos and checkin and checkout:
                # Verificar se o quarto possui unidades físicas disponíveis para o período
                disponivel = False
                unidades = quarto.unidades.all()
                for unidade in unidades:
                    # Verifica se a unidade tem conflito de reservas
                    conflito = unidade.reservas.filter(
                        status__in=['confirmado', 'checkin', 'checkout'],
                        data_checkin__lt=checkout,
                        data_checkout__gt=checkin
                    ).exists()
                    # Verifica bloqueios manuais
                    bloqueado = unidade.bloqueios.filter(
                        data_inicio__lt=checkout,
                        data_fim__gt=checkin
                    ).exists()
                    
                    if not conflito and not bloqueado:
                        disponivel = True
                        break
                        
                if disponivel:
                    quartos_disponiveis.append(quarto)
            else:
                # Sem filtro de data
                quartos_disponiveis.append(quarto)
                
        preco_minimo = min((q.preco for q in quartos_disponiveis), default=None)
        pousadas_data.append({
            'hotel': pousada,
            'quartos': quartos_disponiveis,
            'tem_quartos': len(quartos_disponiveis) > 0,
            'preco_minimo': preco_minimo,
        })
        
    todos_quartos = []
    for item in pousadas_data:
        for q in item['quartos']:
            todos_quartos.append(q)
            
    context = {
        'empresa': empresa_atual,
        'pousadas_data': pousadas_data,
        'todos_quartos': todos_quartos,
        'datas_str': datas_str,
        'guests_str': guests_str,
        'filtros_ativos': filtros_ativos
    }
    return render(request, 'hoteis/portal_grupo.html', context)







