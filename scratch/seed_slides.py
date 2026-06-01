import os
import sys
import django

# Define o caminho do projeto no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import HomeSlide

def seed_slides():
    print("Iniciando seed de HomeSlide no banco hospedagem...")
    
    # Limpa slides antigos se existirem
    HomeSlide.objects.using('hospedagem').all().delete()
    
    slides_data = [
        {
            'titulo': "Viva a Essência da Serra da Ibiapaba",
            'subtitulo': "Descubra chalés rústicos, pousadas charmosas e resorts cercados pela natureza exuberante.",
            'tipo_midia': 'imagem',
            'imagem': None,
            'video': None,
            'data_texto': "Temporada de Inverno",
            'local_texto': "Serra da Ibiapaba, CE",
            'texto_cta': "Explorar Hotéis",
            'link_cta': "/hotelaria/",
            'ordem': 1,
            'ativo': True
        },
        {
            'titulo': "Chalés Exclusivos com Vista Panorâmica",
            'subtitulo': "Aproveite o clima frio e aconchegante da serra em acomodações de alto padrão com todo o conforto.",
            'tipo_midia': 'imagem',
            'imagem': None,
            'video': None,
            'data_texto': "Finais de Semana Especiais",
            'local_texto': "Tianguá, Ceará",
            'texto_cta': "Reservar Chalé",
            'link_cta': "/hotelaria/?tipo=chale",
            'ordem': 2,
            'ativo': True
        },
        {
            'titulo': "Refúgios & Pousadas Boutique de Luxo",
            'subtitulo': "Viva momentos inesquecíveis com experiências completas de bem-estar, lazer e alta gastronomia.",
            'tipo_midia': 'imagem',
            'imagem': None,
            'video': None,
            'data_texto': "Pacotes Exclusivos",
            'local_texto': "Ubajara, Ceará",
            'texto_cta': "Ver Pousadas",
            'link_cta': "/hotelaria/?tipo=pousada",
            'ordem': 3,
            'ativo': True
        }
    ]
    
    for data in slides_data:
        slide = HomeSlide.objects.using('hospedagem').create(**data)
        print(f"Slide criado: {slide.titulo}")
        
    print("Seed de HomeSlide concluído com sucesso!")

if __name__ == '__main__':
    seed_slides()
