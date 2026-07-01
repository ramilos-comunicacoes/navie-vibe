import os
import sys
import django

# Set up django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from restaurantes.models import Restaurante, RestauranteAtracao

def register_restaurants():
    print("Iniciando o seeding de restaurantes...")
    
    # 1. Limpar atrações e restaurantes existentes para evitar duplicidade
    RestauranteAtracao.objects.using('restaurantes').all().delete()
    Restaurante.objects.using('restaurantes').all().delete()
    print("Dados antigos limpos do banco 'restaurantes'.")
    # 2. Definição dos Restaurantes
    restaurantes_data = [
        {
            "nome": "Casa de Engenho",
            "slug": "casa-de-engenho",
            "especialidade": "Restaurante Temático Nordestino",
            "cidade_nome": "Tianguá",
            "endereco": "Rodovia BR-222, Km 310 - Sítio Engenho, Tianguá - CE",
            "whatsapp": "558892763226",
            "whatsapp_privado": "88988881111",
            "email_contato": "contato@casadeengenho.com.br",
            "instagram": "https://www.instagram.com/rcasadeengenho/",
            "cor_primaria": "#b45309",  # Terracota / Âmbar
            "cor_secundaria": "#f59e0b",  # Dourado
            "descricao": "A verdadeira alma do nordeste em Tianguá! Um restaurante temático nordestino perfeito para quem busca uma autêntica imersão cultural acompanhada da melhor gastronomia regional.",
            "banner": "restaurantes/casa-de-engenho/banner/banner.png",
            "imagem": "restaurantes/casa-de-engenho/logo/logo.jpg",
            "logo": "restaurantes/casa-de-engenho/logo/logo.png",
            "sobre_titulo": "Nossa Tradição & Sabor",
            "sobre_texto": "Na Casa de Engenho, cada prato conta uma história. Nascido do desejo de preservar as ricas traditions da culinária cearense e nordestina, nosso restaurante oferece uma verdadeira viagem no tempo. Com uma decoração rústica inspirada nos antigos engenhos de cana-de-açúcar, combinamos ingredientes locais frescos com técnicas artesanais de cozimento lento. Venha saborear nossa tradicional carne de sol com nata, baião de dois quentinho e doces caseiros deliciosos.",
            "sobre_cor_fundo": "#fef3c7",
            "sobre_cor_texto": "#78350f",
            "venda_online": True,
            "latitude": -3.7440084,
            "longitude": -40.9955986
        },
        {
            "nome": "Manacá da Serra",
            "slug": "manaca-da-serra",
            "especialidade": "Restaurante Contemporâneo",
            "cidade_nome": "Tianguá",
            "endereco": "Rua Coronel Estanislau, 450 - Centro, Tianguá - CE",
            "whatsapp": "5588994719344",
            "whatsapp_privado": "88988882222",
            "email_contato": "contato@manacadaserra.com.br",
            "instagram": "https://www.instagram.com/manaca.restaurante/",
            "cor_primaria": "#c16096",  # Rosa/Magenta Manacá
            "cor_secundaria": "#140a1b",  # Ameixa Escura / Plum Black
            "descricao": "O seu refúgio gastronômico em Tianguá. Um ambiente aconchegante que combina sabores únicos com uma experiência acolhedora, ideal para qualquer momento do dia.",
            "banner": "restaurantes/manaca-da-serra/banner/banner.png",
            "imagem": "restaurantes/manaca-da-serra/logo/logo.jpg",
            "logo": "restaurantes/manaca-da-serra/logo/logo.png",
            "sobre_titulo": "Um Refúgio Acolhedor",
            "sobre_texto": "O Manacá da Serra nasceu sob a brisa fresca e acolhedora da serra da Ibiapaba. Nosso espaço foi projetado para ser um verdadeiro refúgio do dia a dia, onde a pressa dá lugar à contemplação e ao prazer de uma boa refeição. Nosso cardápio celebra a culinária contemporânea com toques serranos, utilizando vegetais orgânicos cultivados na própria região e carnes nobres grelhadas com precisão. Perfeito para um almoço em família ou um jantar romântico sob a luz de velas.",
            "sobre_cor_fundo": "#fdf2f8",
            "sobre_cor_texto": "#701a75",
            "venda_online": True,
            "latitude": -3.7213182,
            "longitude": -40.9886249
        },
        {
            "nome": "Premibeer Gastro Pub",
            "slug": "premibeer",
            "especialidade": "Gastro Pub e Cervejaria",
            "cidade_nome": "Tianguá",
            "endereco": "Av. Prefeito Jaques Nunes, 1200 - Planalto da Ibiapaba, Tianguá - CE",
            "whatsapp": "558596699306",
            "whatsapp_privado": "88988883333",
            "email_contato": "contato@premibeer.com.br",
            "instagram": "https://www.instagram.com/premibeer/",
            "cor_primaria": "#d97706",  # Dourado Cerveja
            "cor_secundaria": "#1e293b",  # Slate
            "descricao": "A primeira cervejaria da Serra da Ibiapaba! Uma fusão perfeita entre cervejas artesanais de excelência e pratos elaborados, criando a vibe ideal para curtir com os amigos.",
            "banner": "restaurantes/premibeer/banner/banner.png",
            "imagem": "restaurantes/premibeer/logo/logo.jpg",
            "logo": "restaurantes/premibeer/logo/logo.png",
            "sobre_titulo": "Cerveja Artesanal de Verdade",
            "sobre_texto": "A Premibeer orgulhosamente trouxe a cultura das microcervejarias para o topo da Serra da Ibiapaba. Unindo paixão por malte e lúpulo com a pureza da água da nossa serra, criamos receitas únicas de cerveja artesanal servidas diretamente da fonte. Para acompanhar nossas torneiras de chopp sempre frescas, nosso cardápio de Gastro Pub oferece hambúrgueres artesanais robustos, petiscos clássicos de boteco e carnes defumadas de sabor incomparável. A vibe perfeita para celebrar a vida!",
            "sobre_cor_fundo": "#fafaf9",
            "sobre_cor_texto": "#1c1917",
            "venda_online": True,
            "latitude": -3.718032,
            "longitude": -40.9920004
        },
        {
            "nome": "Biene Cacau",
            "slug": "biene-cacau",
            "especialidade": "Chocolateria Artesanal",
            "cidade_nome": "Tianguá",
            "endereco": "Shopping Ibiapaba, Loja 15 - Centro, Tianguá - CE",
            "whatsapp": "5588992237412",
            "whatsapp_privado": "88988884444",
            "email_contato": "contato@bienecacau.com.br",
            "instagram": "https://www.instagram.com/bienecacau/",
            "cor_primaria": "#7c2d12",  # Marrom Chocolate
            "cor_secundaria": "#fbbf24",  # Ouro
            "descricao": "Elevando o padrão do chocolate na região. Uma marca exclusiva de chocolates artesanais com o conceito bean-to-bar (da amêndoa à barra), garantindo pureza, sabor e uma experiência premium.",
            "banner": "restaurantes/biene-cacau/banner/banner.png",
            "imagem": "restaurantes/biene-cacau/logo/logo.jpg",
            "logo": "restaurantes/biene-cacau/logo/logo.png",
            "sobre_titulo": "Da Amêndoa à Barra",
            "sobre_texto": "Na Biene Cacau, acreditamos que o chocolate de verdade deve ser puro, ético e extraordinário. Somos pioneiros na Serra da Ibiapaba na fabricação de chocolates sob o conceito bean-to-bar (da amêndoa de cacau selecionada diretamente do produtor até a barra finalizada). Controlamos cada etapa do processo: torra suave, moagem em moinhos de pedra e maturação lenta. O resultado é um chocolate com notas aromáticas complexas, sem conservantes ou gorduras hidrogenadas, oferecendo uma experiência sensorial única para paladares exigentes.",
            "sobre_cor_fundo": "#fff7ed",
            "sobre_cor_texto": "#7c2d12",
            "venda_online": True,
            "latitude": -3.718032,
            "longitude": -40.9920004
        }
    ]

    # Criar Restaurantes e salvar no banco 'restaurantes'
    restaurantes_obj = {}
    for data in restaurantes_data:
        rest = Restaurante.objects.using('restaurantes').create(
            nome=data["nome"],
            slug=data["slug"],
            especialidade=data["especialidade"],
            cidade_nome=data["cidade_nome"],
            endereco=data["endereco"],
            whatsapp=data["whatsapp"],
            whatsapp_privado=data["whatsapp_privado"],
            email_contato=data["email_contato"],
            instagram=data["instagram"],
            cor_primaria=data["cor_primaria"],
            cor_secundaria=data["cor_secundaria"],
            descricao=data["descricao"],
            banner=data["banner"],
            imagem=data["imagem"],
            logo=data["logo"],
            sobre_titulo=data["sobre_titulo"],
            sobre_texto=data["sobre_texto"],
            sobre_cor_fundo=data["sobre_cor_fundo"],
            sobre_cor_texto=data["sobre_cor_texto"],
            venda_online=data["venda_online"],
            latitude=data["latitude"],
            longitude=data["longitude"]
        )
        print(f"Restaurante criado com sucesso: {rest.nome} (slug: {rest.slug})")
        restaurantes_obj[rest.slug] = rest

    # 3. Definição das Atrações Especiais de cada estabelecimento
    atracoes_data = [
        {
            "restaurante_slug": "casa-de-engenho",
            "dia": "Toda Sexta-Feira",
            "titulo": "Sexta do Pé de Serra",
            "texto": "Toda sexta-feira a partir das 20h, traga os amigos para curtir o melhor do forró pé-de-serra ao vivo com trios locais e saborear nosso tradicional baião de dois duplo com desconto especial.",
            "cor_fundo": "#b45309",
            "cor_texto": "#ffffff"
        },
        {
            "restaurante_slug": "manaca-da-serra",
            "dia": "Aos Sábados",
            "titulo": "Música Acústica no Jardim",
            "texto": "Aproveite a noite de sábado com clássicos da MPB e Pop Nacional em formato acústico (voz e violão), sob a luz de velas em nosso aconchegante jardim de inverno.",
            "cor_fundo": "#8b5cf6",
            "cor_texto": "#ffffff"
        },
        {
            "restaurante_slug": "premibeer",
            "dia": "Toda Quinta-Feira",
            "titulo": "Quinta do Rock & Blues",
            "texto": "Toda quinta-feira, bandas regionais e nacionais trazem o melhor do rock clássico e blues. E mais: Chopp Pilsen artesanal de 500ml com 30% de desconto até as 21h!",
            "cor_fundo": "#d97706",
            "cor_texto": "#ffffff"
        },
        {
            "restaurante_slug": "biene-cacau",
            "dia": "Aos Sábados",
            "titulo": "Harmonização de Cafés & Chocolates",
            "texto": "Todos os sábados à tarde, participe de um workshop guiado de harmonização de nossos chocolates bean-to-bar com cafés especiais de microlotes premiados cultivados na serra.",
            "cor_fundo": "#7c2d12",
            "cor_texto": "#ffffff"
        }
    ]

    # Criar Atrações e salvar no banco 'restaurantes'
    for atracao in atracoes_data:
        rest = restaurantes_obj[atracao["restaurante_slug"]]
        RestauranteAtracao.objects.using('restaurantes').create(
            restaurante=rest,
            dia=atracao["dia"],
            titulo=atracao["titulo"],
            texto=atracao["texto"],
            cor_fundo=atracao["cor_fundo"],
            cor_texto=atracao["cor_texto"],
            ativo=True
        )
        print(f"Atração '{atracao['titulo']}' vinculada ao restaurante {rest.nome}.")

    print("Seeding de restaurantes concluído com sucesso!")

if __name__ == "__main__":
    register_restaurants()
