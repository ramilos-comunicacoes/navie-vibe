from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from hoteis.models import Reserva
from datetime import date, timedelta
from clientes.models import PostMomento, ComentarioMomento

@login_required(login_url='clientes:login_cadastro')
def painel_view(request):
    """
    Renders the central unified Client Dashboard (Painel do Cliente).
    
    PURPOSE FOR AI AGENTS:
    - This view acts as the private user cockpit.
    - It reads the user context and fetches all active hotel/stay bookings from hoteis.Reserva.
    - It combines active database bookings with simulated tickets (Shows, Cinema) to fully demo the QR validation mechanics.
    - AI agents can call this view's backend endpoint or parse its rendered templates to inspect a customer's active schedules.

    DATABASE QUERIES:
    - Stays (Hospedagens): Fetched directly from the sqlite database where user equals request.user.
    
    MOCK/DEMO INJECTION:
    - To prevent empty lists and showcase the front-end card layouts, dynamic simulated tickets are generated in Python
      for the 'Shows' and 'Cinema' verticals and merged into the context dictionary.
    """
    # 1. Fetch real stays from the database
    real_reservas = Reserva.objects.filter(usuario=request.user).order_by('-data_checkin')
    
    hospedagens_list = []
    
    # Process real stays into a uniform layout format
    for res in real_reservas:
        hospedagens_list.append({
            'id': f"RES-{res.id.hex[:8].upper()}",
            'real': True,
            'estabelecimento': res.unidade.quarto.hotel.nome,
            'localizacao': f"{res.unidade.quarto.hotel.local.cidade} - {res.unidade.quarto.hotel.local.estado}",
            'detalhe': f"Quarto/Chalé: {res.unidade.identificador} ({res.unidade.quarto.nome})",
            'data_inicio': res.data_checkin.strftime('%d/%m/%Y'),
            'data_fim': res.data_checkout.strftime('%d/%m/%Y'),
            'periodo': f"{res.data_checkin.strftime('%d/%m/%Y')} até {res.data_checkout.strftime('%d/%m/%Y')}",
            'preco_formatado': f"R$ {res.valor_total:.2f}",
            'status': res.get_status_display(),
            'status_slug': res.status, # 'pendente', 'confirmada', 'cancelada'
            'qr_payload': f"VALIDA-RESERVA-{res.id}-{res.unidade.identificador}-{cpf_obfuscated(request.user)}",
            'logo_url': res.unidade.quarto.hotel.logo.url if res.unidade.quarto.hotel.logo else '/media/hoteis/logos/logosemfundo.png'
        })
        
    # If the user has no real bookings, inject a beautiful mock stay to showcase the UI
    if not hospedagens_list:
        hospedagens_list.append({
            'id': "RES-MOCK99",
            'real': False,
            'estabelecimento': "Pousada da Serra",
            'localizacao': "Tianguá - CE",
            'detalhe': "Chalé Master 04 (Suíte Casal Premium)",
            'data_inicio': (date.today() + timedelta(days=15)).strftime('%d/%m/%Y'),
            'data_fim': (date.today() + timedelta(days=18)).strftime('%d/%m/%Y'),
            'periodo': f"{(date.today() + timedelta(days=15)).strftime('%d/%m/%Y')} até {(date.today() + timedelta(days=18)).strftime('%d/%m/%Y')}",
            'preco_formatado': "R$ 1.650,00",
            'status': "Confirmada (Demonstração)",
            'status_slug': "confirmada",
            'qr_payload': f"VALIDA-RESERVA-MOCK99-CHALE04-{cpf_obfuscated(request.user)}",
            'logo_url': '/media/hoteis/logos/logosemfundo.png'
        })

    # 2. Inject beautifully structured mock tickets for Shows
    shows_list = [
        {
            'id': "TKT-SHOW01",
            'titulo': "Ibiapaba Rock Festival 2026",
            'produtora': "Vibe Produções CE",
            'local': "Arena Ibiapaba - Tianguá",
            'data': "14/11/2026 às 21:00",
            'setor': "Ingresso VIP Frontstage",
            'preco_formatado': "R$ 180,00",
            'status': "Ativo",
            'status_slug': "confirmada",
            'qr_payload': f"VALIDA-INGRESSO-SHOW01-VIP-{cpf_obfuscated(request.user)}"
        },
        {
            'id': "TKT-SHOW02",
            'titulo': "Stand Up Comedy: Rindo na Serra",
            'produtora': "Ceará Riso & Arte",
            'local': "Auditório Centro Cultural Ubajara",
            'data': "05/12/2026 às 20:00",
            'setor': "Pista Meia-Entrada",
            'preco_formatado': "R$ 45,00",
            'status': "Ativo",
            'status_slug': "confirmada",
            'qr_payload': f"VALIDA-INGRESSO-SHOW02-PISTAMEIA-{cpf_obfuscated(request.user)}"
        }
    ]

    # 3. Inject beautifully structured mock tickets for Cinema
    cinema_list = [
        {
            'id': "TKT-CINE01",
            'filme': "Batman: O Retorno do Cavaleiro",
            'cinema': "Ciné Naviê - Tianguá Shopping",
            'sala': "Sala 02 VIP - 4K Laser",
            'sessao': "Hoje às 19:30",
            'formato': "3D - Dublado",
            'assento': "Fileira F - Poltrona 12",
            'preco_formatado': "R$ 38,00",
            'status': "Emitido",
            'status_slug': "confirmada",
            'qr_payload': f"VALIDA-INGRESSO-CINE01-SALA02-F12-{cpf_obfuscated(request.user)}"
        }
    ]

    # 4. Fetch real moments from database
    from clientes.models import PostMomento, ComentarioMomento
    posts_qs = PostMomento.objects.all().order_by('-criado_em').prefetch_related('comentarios', 'likes')
    
    feed_posts = []
    for p in posts_qs:
        liked_by_me = request.user in p.likes.all()
        comments_list = []
        for c in p.comentarios.all():
            comments_list.append({
                'usuario': c.usuario.get_full_name() or c.usuario.username,
                'usuario_username': c.usuario.username,
                'texto': c.texto,
                'criado_em': c.criado_em.strftime('%d/%m/%Y %H:%M')
            })
            
        feed_posts.append({
            'id': p.id.hex,
            'usuario': p.usuario.get_full_name() or p.usuario.username,
            'usuario_username': p.usuario.username,
            'texto': p.texto,
            'imagem': p.imagem.url if p.imagem else None,
            'avaliacao': p.avaliacao,
            'estabelecimento': p.estabelecimento_nome,
            'reserva_confirmada': p.reserva is not None,
            'likes_count': p.likes.count(),
            'liked_by_me': liked_by_me,
            'criado_em': p.criado_em.strftime('%d/%m/%Y %H:%M'),
            'comentarios': comments_list
        })

    # Inject premium mock moments if database has no posts (for demo purpose)
    mock_comments_1 = request.session.get('comments_mock-post-1', [])
    liked_mock_1 = request.session.get('liked_mock-post-1', False)
    
    mock_comments_2 = request.session.get('comments_mock-post-2', [])
    liked_mock_2 = request.session.get('liked_mock-post-2', True)
    
    mock_comments_3 = request.session.get('comments_mock-post-3', [])
    liked_mock_3 = request.session.get('liked_mock-post-3', False)

    mock_posts = [
        {
            'id': 'mock-post-1',
            'usuario': 'Marcos Oliveira',
            'usuario_username': 'marcos_ol',
            'texto': 'Experiência sensacional na Pousada Ramilos Tianguá! O clima da serra de Ibiapaba é espetacular à noite, ótimo atendimento e chalés super confortáveis. Recomendo muito o fondue de chocolate da casa!',
            'imagem': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80',
            'avaliacao': 5,
            'estabelecimento': 'Pousada Ramilos Tianguá',
            'reserva_confirmada': True,
            'likes_count': 24 + (1 if liked_mock_1 else 0),
            'liked_by_me': liked_mock_1,
            'criado_em': '14/06/2026 18:30',
            'comentarios': [
                {
                    'usuario': 'Alice Souza',
                    'usuario_username': 'alice_sz',
                    'texto': 'Que lugar lindo! Já quero reservar para minhas férias!',
                    'criado_em': '14/06/2026 19:10'
                },
                {
                    'usuario': 'Mateus da Silva',
                    'usuario_username': 'mateus_silva',
                    'texto': 'O atendimento de lá é realmente nota dez.',
                    'criado_em': '14/06/2026 19:45'
                }
            ] + mock_comments_1
        },
        {
            'id': 'mock-post-2',
            'usuario': 'Carla Mendes',
            'usuario_username': 'carla_m',
            'texto': 'Ibiapaba Rock Festival 2026 foi incrível! A vibe e a organização foram nota mil. Que venham mais festivais como esse em Tianguá!',
            'imagem': 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80',
            'avaliacao': 5,
            'estabelecimento': 'Ibiapaba Rock Festival 2026',
            'reserva_confirmada': True,
            'likes_count': 42 + (1 if liked_mock_2 else 0),
            'liked_by_me': liked_mock_2,
            'criado_em': '15/06/2026 01:15',
            'comentarios': [
                {
                    'usuario': 'Roberto Costa',
                    'usuario_username': 'roberto_c',
                    'texto': 'O show do Frontstage foi insano! Melhor festival do ano.',
                    'criado_em': '15/06/2026 09:30'
                }
            ] + mock_comments_2
        },
        {
            'id': 'mock-post-3',
            'usuario': 'Fernanda Lima',
            'usuario_username': 'fer_lima',
            'texto': 'Só passei pra dizer que a Sala VIP do Ciné Naviê no Tianguá Shopping tem a melhor poltrona que já experimentei. E a pipoca de manteiga trufada é outro nível!',
            'imagem': None,
            'avaliacao': 4,
            'estabelecimento': 'Ciné Naviê - Tianguá Shopping',
            'reserva_confirmada': True,
            'likes_count': 12 + (1 if liked_mock_3 else 0),
            'liked_by_me': liked_mock_3,
            'criado_em': '15/06/2026 14:05',
            'comentarios': [] + mock_comments_3
        }
    ]

    feed_posts = feed_posts + mock_posts

    context = {
        'hospedagens': hospedagens_list,
        'shows': shows_list,
        'cinema': cinema_list,
        'feed_posts': feed_posts,
        'perfil': getattr(request.user, 'perfil', None)
    }

    return render(request, 'clientes/painel.html', context)

def cpf_obfuscated(user):
    """
    Helper function to safely extract and obfuscate the user's CPF for the QR payload.
    """
    profile = getattr(user, 'perfil', None)
    if profile:
        cpf = profile.cpf
        # Remove dots and dashes and return obfuscated
        cpf_clean = ''.join(c for c in cpf if c.isdigit())
        if len(cpf_clean) == 11:
            return f"***.{cpf_clean[3:6]}.{cpf_clean[6:9]}-**"
    return "USER-UNKNOWN"

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from hoteis.models import Reserva

@login_required(login_url='clientes:login_cadastro')
def criar_post_view(request):
    if request.method == 'POST':
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        reserva_id = request.POST.get('reserva_id')
        avaliacao = request.POST.get('avaliacao', 5)
        
        reserva = None
        estabelecimento_nome = request.POST.get('estabelecimento_nome')
        
        if reserva_id and reserva_id != 'none':
            try:
                from uuid import UUID
                res_uuid = UUID(reserva_id.replace('RES-', '')) if isinstance(reserva_id, str) and len(reserva_id.replace('RES-', '')) == 32 else None
                if res_uuid:
                    reserva = Reserva.objects.get(id=res_uuid, usuario=request.user)
                    estabelecimento_nome = reserva.unidade.quarto.hotel.nome
            except Exception:
                pass
                
        PostMomento.objects.create(
            usuario=request.user,
            reserva=reserva,
            estabelecimento_nome=estabelecimento_nome,
            imagem=imagem,
            texto=texto,
            avaliacao=int(avaliacao)
        )
        return redirect('clientes:painel')
    return redirect('clientes:painel')

@login_required(login_url='clientes:login_cadastro')
def like_post_view(request, post_id):
    liked = False
    count = 0
    
    if post_id.startswith('mock-'):
        liked_key = f'liked_{post_id}'
        liked = not request.session.get(liked_key, False)
        request.session[liked_key] = liked
        default_counts = {'mock-post-1': 24, 'mock-post-2': 42, 'mock-post-3': 12}
        count = default_counts.get(post_id, 10) + (1 if liked else 0)
    else:
        try:
            post = PostMomento.objects.get(id=post_id)
            if request.user in post.likes.all():
                post.likes.remove(request.user)
                liked = False
            else:
                post.likes.add(request.user)
                liked = True
            count = post.likes.count()
        except Exception:
            pass
            
    coracao_class = "fill-red-500 text-red-500 scale-110" if liked else "text-slate-400 dark:text-navie-textsec hover:text-red-500 hover:scale-110"
    html = f"""
    <button hx-post="{reverse('clientes:like_post', args=[post_id])}" 
            hx-swap="outerHTML" 
            class="flex items-center gap-1.5 focus:outline-none transition-all duration-300 transform active:scale-90 {coracao_class}">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-heart"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
        <span class="text-[11px] font-bold text-slate-500 dark:text-navie-textsec">{count}</span>
    </button>
    """
    return HttpResponse(html)

@login_required(login_url='clientes:login_cadastro')
def comentar_post_view(request, post_id):
    if request.method == 'POST':
        texto = request.POST.get('texto')
        if texto:
            if post_id.startswith('mock-'):
                comments_key = f'comments_{post_id}'
                mock_comments = request.session.get(comments_key, [])
                mock_comments.append({
                    'usuario': request.user.get_full_name() or request.user.username,
                    'usuario_username': request.user.username,
                    'texto': texto,
                    'criado_em': 'Agora mesmo'
                })
                request.session[comments_key] = mock_comments
            else:
                try:
                    post = PostMomento.objects.get(id=post_id)
                    ComentarioMomento.objects.create(
                        post=post,
                        usuario=request.user,
                        texto=texto
                    )
                except Exception:
                    pass
        return redirect('clientes:painel')
    return redirect('clientes:painel')

@login_required(login_url='clientes:login_cadastro')
def editar_perfil_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        profile = getattr(user, 'perfil', None)
        if profile:
            profile.telefone = request.POST.get('telefone', '')
            profile.cep = request.POST.get('cep', '')
            profile.endereco = request.POST.get('endereco', '')
            profile.numero = request.POST.get('numero', '')
            profile.bairro = request.POST.get('bairro', '')
            profile.cidade = request.POST.get('cidade', '')
            profile.estado = request.POST.get('estado', '')
            profile.save()
            
        return redirect('clientes:painel')
    return redirect('clientes:painel')
