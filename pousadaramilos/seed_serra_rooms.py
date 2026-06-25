import os
import django

# Configure Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from sistema.models import Pousada, CategoriaQuarto, Quarto, QuartoImagem

def seed_serra():
    print("=== Iniciando População dos Quartos da Pousada Serra ===")
    
    # 1. Encontra a Pousada Serra (ID 3 ou por nome)
    pousada_serra = Pousada.objects.filter(nome__icontains="Serra").first()
    if not pousada_serra:
        print("Erro: Pousada Ramiros Serra não encontrada.")
        return
        
    print(f"Pousada encontrada: {pousada_serra.nome} (ID: {pousada_serra.id})")
    
    # 2. Apaga categorias e quartos existentes na Pousada Serra
    print("Limpando categorias e quartos antigos da Pousada Serra...")
    Quarto.objects.filter(pousada=pousada_serra).delete()
    CategoriaQuarto.objects.filter(pousada=pousada_serra).delete()
    print("Limpeza concluída com sucesso.")
    
    # 3. Definição das 12 novas categorias com seus dados
    categorias_data = [
        # === INDIVIDUAL ===
        {
            "nome": "Individual 1° Andar - Ventilador",
            "preco": 80.00,
            "capacidade": 1,
            "descricao": "Acomodação individual econômica e muito aconchegante localizada no primeiro andar. Ideal para viajantes independentes na serra. Oferece ventilador silencioso, Wi-Fi de alta velocidade, mesa de trabalho confortável e farto café da manhã montanhês servido diariamente.",
            "comodidades": "Wi-Fi de Alta Velocidade,Café no Quarto",
            "tags": "Silencioso,Café da Manhã,Serra",
            "seo_titulo": "Individual 1° Andar Econômico (Ventilador) - Pousada Ramiros Serra",
            "seo_descricao": "Hospedagem individual econômica na Serra com ventilador, mesa de trabalho, Wi-Fi rápido e café da manhã montanhês incluso. Reserve direto pelo melhor preço!"
        },
        {
            "nome": "Individual 1° Andar - Ar-condicionado",
            "preco": 105.00,
            "capacidade": 1,
            "descricao": "Quarto individual confortável e totalmente climatizado no primeiro andar da pousada. Perfeito para quem busca relaxar após explorar Gramado e Canela. Conta com ar-condicionado Split quente/frio, Wi-Fi de banda larga, frigobar abastecido e delicioso café da manhã montanhês incluso.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Silencioso,Café da Manhã,Serra",
            "seo_titulo": "Individual 1° Andar Climatizado (Ar split) - Pousada Ramiros Serra",
            "seo_descricao": "Acomodação individual climatizada com Split quente/frio, Wi-Fi de alta velocidade, frigobar e farto café da manhã na serra. Reserve com desconto progressivo!"
        },
        {
            "nome": "Individual Térreo - Ar-condicionado",
            "preco": 125.00,
            "capacidade": 1,
            "descricao": "Prático quarto individual localizado no andar térreo da pousada, com total acessibilidade e facilidade de locomoção. Climatizado com ar-condicionado split potente, oferece TV LED, Wi-Fi ultra veloz, frigobar abastecido e café da manhã farto incluso diariamente no restaurante.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Silencioso,Café da Manhã,Serra",
            "seo_titulo": "Individual Térreo com Acessibilidade e Ar Split - Pousada Ramiros Serra",
            "seo_descricao": "Hospedagem individual no andar térreo com total acessibilidade na serra. Ar-condicionado split, Wi-Fi de alta fidelidade e farto café da manhã montanhês."
        },
        # === DUPLO ===
        {
            "nome": "Duplo 1° Andar - Ventilador",
            "preco": 145.00,
            "capacidade": 2,
            "descricao": "Charme e aconchego perfeito para duas pessoas no primeiro andar. Uma acomodação arejada com ventilador, cama de casal queen-size ultra macia, frigobar com bebidas artesanais da serra, mesa de trabalho, Wi-Fi rápido e café da manhã tradicional incluso.",
            "comodidades": "Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Casal,Silencioso,Café da Manhã,Serra",
            "seo_titulo": "Duplo Aconchego 1° Andar (Ventilador) - Pousada Ramiros Serra",
            "seo_descricao": "Quarto duplo romântico no primeiro andar, muito arejado. Cama queen-size, ventilador silencioso, Wi-Fi de banda larga e farto café da manhã da serra incluso."
        },
        {
            "nome": "Duplo 1° Andar - Ar-condicionado",
            "preco": 180.00,
            "capacidade": 2,
            "descricao": "Suíte romântica de casal no primeiro andar, projetada para momentos inesquecíveis na serra gaúcha. Oferece ar-condicionado split quente/frio, isolamento termoacústico primoroso, cama queen-size de alta densidade, frigobar completo, Wi-Fi e um farto e delicioso café da manhã montanhês.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Casal,Romântico,Café da Manhã,Serra",
            "seo_titulo": "Duplo Premium 1° Andar Climatizado - Pousada Ramiros Serra",
            "seo_descricao": "Reserve nossa charmosa suíte de casal climatizada no primeiro andar em Gramado. Ar split, Wi-Fi rápido, frigobar abastecido e delicioso café da manhã incluso."
        },
        {
            "nome": "Duplo Térreo - Ar-condicionado",
            "preco": 200.00,
            "capacidade": 2,
            "descricao": "Luxuoso quarto duplo situado no térreo, oferecendo facilidade de acesso sem escadas e total privacidade. Conta com cama king-size premium, climatização quente e frio de última geração, TV, frigobar, Wi-Fi de alta fidelidade e café da manhã montanhês servido diariamente.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Casal,Romântico,Café da Manhã,Serra",
            "seo_titulo": "Duplo Térreo Conforto Master (Ar-condicionado) - Pousada Ramiros Serra",
            "seo_descricao": "Hospede-se com máximo conforto no nosso quarto duplo térreo. Climatização split, cama king-size, Wi-Fi de alta fidelidade e maravilhoso café da manhã na serra."
        },
        # === TRIPLO ===
        {
            "nome": "Triplo 1° Andar - Ar-condicionado",
            "preco": 220.00,
            "capacidade": 3,
            "descricao": "Ampla e sofisticada acomodação familiar no primeiro andar para até três hóspedes. Dispõe de cama de casal e uma cama de solteiro adicionais, ar-condicionado split quente/frio potente, frigobar abastecido, mesa de chá, Wi-Fi veloz e o farto e irresistível café da manhã de Gramado incluso.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Triplo Família 1° Andar Climatizado Split - Pousada Ramiros Serra",
            "seo_descricao": "Acomodação tripla sob medida para famílias no primeiro andar. Ar split potente, camas confortáveis, Wi-Fi e farto café da manhã montanhês incluído."
        },
        {
            "nome": "Triplo Térreo - Ar-condicionado",
            "preco": 240.00,
            "capacidade": 3,
            "descricao": "Conforto e fácil locomoção no térreo para grupos ou famílias de três pessoas. Equipado com ar-condicionado split de controle digital, camas de altíssima qualidade, amplo banheiro privativo com aquecimento a gás, frigobar, Wi-Fi rápido e café da manhã colonial completo cortesia.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Triplo Térreo Conforto & Acessibilidade - Pousada Ramiros Serra",
            "seo_descricao": "Hospedagem tripla no andar térreo com excelente mobilidade física. Ar-condicionado split, Wi-Fi veloz e farto café da manhã montanhês colonial incluso."
        },
        # === QUÁDUPLO ===
        {
            "nome": "Quádruplo 1° Andar - Ar-condicionado",
            "preco": 290.00,
            "capacidade": 4,
            "descricao": "Maravilhoso apartamento familiar para quatro hóspedes no primeiro andar. Dividido de forma inteligente para manter o conforto acústico, conta com ar-condicionado split para climatização completa, armários, frigobar de alta capacidade, Wi-Fi e delicioso café da manhã montanhês incluso.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Quádruplo Família 1° Andar Amplo - Pousada Ramiros Serra",
            "seo_descricao": "Apartamento amplo para até 4 pessoas no primeiro andar da serra. Ar split potente, frigobar abastecido, Wi-Fi rápido e café da manhã montanhês de luxo."
        },
        {
            "nome": "Quádruplo Térreo - Ar-condicionado",
            "preco": 310.00,
            "capacidade": 4,
            "descricao": "Quarto quádruplo gigante localizado no térreo, ideal para viagens em família ou grupos de amigos que priorizam a facilidade de acesso. Equipado com ar-condicionado split quente/frio, frigobar, camas super confortáveis, Wi-Fi premium de banda larga e farto café da manhã colonial da serra.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Quádruplo Térreo Conforto e Acesso Fácil - Pousada Ramiros Serra",
            "seo_descricao": "Acomodação gigante para 4 pessoas no térreo com acessibilidade excelente. Equipado com ar-condicionado split, Wi-Fi rápido e tradicional café da manhã."
        },
        # === QUÍNTUPLO ===
        {
            "nome": "Quíntuplo 1° Andar - Ar-condicionado",
            "preco": 360.00,
            "capacidade": 5,
            "descricao": "Acomodação máster gigante no primeiro andar, especialmente decorada com detalhes em madeira rústica, hospedando até 5 pessoas de forma espaçosa e elegante. Climatização split quente/frio premium, Wi-Fi rápido de banda larga, frigobar completo e farto café da manhã colonial serrano incluso.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Quíntuplo Gigante Grupo 1° Andar - Pousada Ramiros Serra",
            "seo_descricao": "Suíte quíntuplo de grande porte no primeiro andar da serra. Perfeito para grupos e famílias de 5 pessoas. Ar split, Wi-Fi de alta fidelidade e café da manhã."
        },
        {
            "nome": "Quíntuplo Térreo - Ar-condicionado",
            "preco": 380.00,
            "capacidade": 5,
            "descricao": "Nossa maior acomodação familiar no andar térreo, desenhada para proporcionar a melhor estadia em grupo com acessibilidade premium e total espaço físico. Banheiro gigante com aquecimento central a gás, climatização split de última geração, Wi-Fi rápido e farto café da manhã montanhês todos os dias.",
            "comodidades": "Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto,Frigobar Abastecido",
            "tags": "Família,Café da Manhã,Serra",
            "seo_titulo": "Quíntuplo Térreo Espaçoso Master Suite - Pousada Ramiros Serra",
            "seo_descricao": "Nossa maior suíte de 5 pessoas no térreo com acessibilidade premium em Gramado. Climatização split, Wi-Fi veloz e maravilhoso café da manhã colonial incluso."
        }
    ]

    images_filenames = [
        "serra_room_rustic.png",
        "serra_room_attic.png",
        "serra_room_fireplace.png",
        "serra_room_garden.png"
    ]

    room_number_counter = 101

    for idx, data in enumerate(categorias_data):
        print(f"\nCriando Categoria ({idx + 1}/12): {data['nome']}...")
        
        # Cria CategoriaQuarto
        cat = CategoriaQuarto.objects.create(
            pousada=pousada_serra,
            nome=data["nome"],
            preco_base=data["preco"],
            capacidade_adultos=data["capacidade"],
            capacidade_criancas=1,  # Padrão infantil da serra (até 05 anos não paga)
            descricao=data["descricao"],
            comodidades=data["comodidades"],
            tags=data["tags"],
            seo_titulo=data["seo_titulo"],
            seo_descricao=data["seo_descricao"],
            ativo=True
        )
        
        print(f"-> Categoria criada com sucesso! ID: {cat.id}, Slug: {cat.slug}")
        
        # Cria 4 imagens associadas a esta categoria (Ordem 0 a 3)
        for order, img_file in enumerate(images_filenames):
            QuartoImagem.objects.create(
                categoria=cat,
                url_imagem=f"quartos/galeria/{img_file}",
                ordem=order
            )
        print(f"-> 4 Imagens vinculadas com sucesso (Slots 0 a 3).")
        
        # Cria 1 quarto físico real (Unidade) para a categoria de forma a ficar operacional
        room_num = str(room_number_counter)
        Quarto.objects.create(
            pousada=pousada_serra,
            categoria=cat,
            numero=room_num,
            status="LIVRE",
            capacidade_maxima=cat.capacidade_adultos
        )
        print(f"-> Quarto Físico real sincronizado: Quarto {room_num}")
        room_number_counter += 1

    print("\n=== Seeding da Pousada Serra Finalizado com 100% de Sucesso! ===")

if __name__ == "__main__":
    seed_serra()
