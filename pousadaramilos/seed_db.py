import os
import django
from datetime import date, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from sistema.models import Pousada, CategoriaQuarto, Quarto, Usuario, Cliente, Reserva, TransacaoFinanceira

def seed():
    print("=== Iniciando a Semeadura do Banco de Dados (Seed Atualizado) ===")
    
    # 1. Limpa dados antigos
    print("Limpando dados antigos...")
    Reserva.objects.all().delete()
    Cliente.objects.all().delete()
    Quarto.objects.all().delete()
    CategoriaQuarto.objects.all().delete()
    Usuario.objects.all().delete()
    Pousada.objects.all().delete()
    
    # 2. Criação das Pousadas (3 Unidades da Rede Ramilos)
    print("Criando as 3 Pousadas Ramilos...")
    pousada_centro = Pousada.objects.create(
        nome="Pousada Ramilos Sertão",
        endereco="Sitio Bela Vista, N° S/N, Complemento: Sala 1, Bairro: Zona Rural, Tianguá - CE, 62336-000",
        telefone_whatsapp="5554999999991",
        cnpj="12.345.678/0001-90",
        cor_primaria_hex="#2563eb",  # Azul sofisticado
        mapa_latitude=-3.6658475,
        mapa_longitude=-40.9367097,
        ativo=True
    )
    pousada_praia = Pousada.objects.create(
        nome="Pousada Luís Correia",
        endereco="Av. Beira Mar, S/N - Praia de Atalaia, Luís Correia - PI, 64220-000",
        telefone_whatsapp="5554999999992",
        cnpj="12.345.678/0002-71",
        cor_primaria_hex="#10b981",  # Verde esmeralda refrescante
        mapa_latitude=-2.888536,
        mapa_longitude=-41.6514733,
        ativo=True
    )
    pousada_serra = Pousada.objects.create(
        nome="Pousada Serra - Tianguá",
        endereco="Sítio Santo Antônio, N° S/N - Zona Rural, Tianguá - CE, 62336-000",
        telefone_whatsapp="5554999999993",
        cnpj="12.345.678/0003-52",
        cor_primaria_hex="#8b5cf6",  # Violeta luxo
        mapa_latitude=-3.7439608,
        mapa_longitude=-41.0070228,
        ativo=True
    )
    
    # 3. Criação dos Usuários por Cargo (RBAC)
    print("Criando usuários de demonstração...")
    # Administrador Global Principal
    admin = Usuario.objects.create_superuser(
        username='admin',
        email='admin@ramiros.com.br',
        password='admin123',
        nome_completo='Administrador Geral Ramiros',
        role='DIRECAO',
        pousada_vinculada=None
    )
    
    # Administrador Tiago Ismar (Usuário mestre solicitado)
    tiago = Usuario.objects.create_superuser(
        username='tiagoismar',
        email='tiago@ramiros.com.br',
        password='limaodoce',
        nome_completo='Tiago Ismar',
        role='DIRECAO',
        pousada_vinculada=None
    )
    
    # Portaria (Alocado na pousada Centro)
    recepcao = Usuario.objects.create_user(
        username='recepcionista',
        email='recepcao@ramiros.com.br',
        password='recepcionista123',
        nome_completo='Carla Souza (Portaria)',
        role='PORTARIA',
        pousada_vinculada=pousada_centro
    )
    
    # Serviço / Operacional (Alocado na pousada Centro)
    camareira = Usuario.objects.create_user(
        username='camareira',
        email='camareira@ramiros.com.br',
        password='camareira123',
        nome_completo='Dona Maria (Serviço)',
        role='SERVICO',
        pousada_vinculada=pousada_centro
    )

    # 4. Categorias de Quarto (Preços, Capacidades e Vínculo à Pousada)
    print("Criando categorias de acomodações vinculadas às pousadas...")
    # Categorias da Pousada Centro
    cat_suite_centro = CategoriaQuarto.objects.create(
        pousada=pousada_centro,
        nome="Suíte Master Casal",
        descricao="Cama king-size, banheira de hidromassagem, ar-condicionado quente/frio, frigobar retrô e vista panorâmica.",
        preco_base=450.00,
        capacidade_adultos=2,
        capacidade_criancas=1,
        comodidades="Ar Condicionado,Wi-Fi de Alta Velocidade,Hidromassagem,Frigobar Abastecido",
        tags="Casal,Romântico,Serra"
    )
    cat_standard_centro = CategoriaQuarto.objects.create(
        pousada=pousada_centro,
        nome="Quarto Standard Casal",
        descricao="Cama queen-size, ar-condicionado split, TV a cabo, frigobar e mesa de trabalho confortável.",
        preco_base=280.00,
        capacidade_adultos=2,
        capacidade_criancas=0,
        comodidades="Ar Condicionado,Wi-Fi de Alta Velocidade,Café no Quarto",
        tags="Casal,Trabalho Remoto"
    )
    cat_familia_centro = CategoriaQuarto.objects.create(
        pousada=pousada_centro,
        nome="Cabana Luxo Família",
        descricao="Dois quartos integrados, cozinha completa equipada, lareira a lenha e deck externo privativo com churrasqueira.",
        preco_base=680.00,
        capacidade_adultos=4,
        capacidade_criancas=2,
        comodidades="Wi-Fi de Alta Velocidade,Copa Completa,Lareira,Churrasqueira",
        tags="Família,Pet Friendly,Silencioso"
    )

    # Categoria da Pousada Praia
    cat_suite_praia = CategoriaQuarto.objects.create(
        pousada=pousada_praia,
        nome="Suíte Frente Mar Premium",
        descricao="Cama de casal king, varanda de vidro privativa sobre a areia da praia, jacuzzi externa aquecida e ar-condicionado potênte.",
        preco_base=590.00,
        capacidade_adultos=2,
        capacidade_criancas=0,
        comodidades="Ar Condicionado,Wi-Fi de Alta Velocidade,Piscina Privativa,Hidromassagem",
        tags="Casal,Romântico,Praia"
    )

    # 5. Quartos Físicos Reais (Unidades de Acomodação)
    print("Criando quartos físicos reativos...")
    # Pousada Centro
    q101 = Quarto.objects.create(pousada=pousada_centro, categoria=cat_suite_centro, numero="101", status="OCUPADO", capacidade_maxima=3)
    q102 = Quarto.objects.create(pousada=pousada_centro, categoria=cat_suite_centro, numero="102", status="LIVRE", capacidade_maxima=3)
    q201 = Quarto.objects.create(pousada=pousada_centro, categoria=cat_standard_centro, numero="201", status="LIVRE", capacidade_maxima=2)
    q202 = Quarto.objects.create(pousada=pousada_centro, categoria=cat_standard_centro, numero="202", status="SUJO", capacidade_maxima=2)
    q301 = Quarto.objects.create(pousada=pousada_centro, categoria=cat_familia_centro, numero="301", status="MANUTENCAO", capacidade_maxima=6)

    # Pousada Praia
    q_praia_101 = Quarto.objects.create(pousada=pousada_praia, categoria=cat_suite_praia, numero="101", status="LIVRE", capacidade_maxima=2)
    q_praia_102 = Quarto.objects.create(pousada=pousada_praia, categoria=cat_suite_praia, numero="102", status="OCUPADO", capacidade_maxima=2)

    # 6. Clientes
    print("Criando base de hóspedes...")
    c1 = Cliente.objects.create(nome="João Silva Santos", cpf_passaporte="111.222.333-44", telefone_whatsapp="5511988887777", email="joao.silva@gmail.com")
    c2 = Cliente.objects.create(nome="Mariana Oliveira Costa", cpf_passaporte="555.666.777-88", telefone_whatsapp="5521977776666", email="mari.costa@hotmail.com")
    c3 = Cliente.objects.create(nome="Carlos Eduardo Rocha", cpf_passaporte="999.888.777-66", telefone_whatsapp="5581966665555", email="carlos.rocha@outlook.com")

    # 7. Reservas
    print("Criando histórico de reservas...")
    # Reserva ativa ocupando o quarto 101 da pousada Centro
    res1 = Reserva.objects.create(
        quarto=q101,
        cliente=c1,
        data_checkin=date.today() - timedelta(days=2),
        data_checkout=date.today() + timedelta(days=2),
        status='HOSPEDADO',
        valor_total=1800.00,
        valor_pago=900.00,
        canal_origem='WEBSITE_WHATSAPP'
    )
    
    # Reserva futura pendente para o quarto 102
    res2 = Reserva.objects.create(
        quarto=q102,
        cliente=c2,
        data_checkin=date.today() + timedelta(days=5),
        data_checkout=date.today() + timedelta(days=9),
        status='PENDENTE',
        valor_total=1800.00,
        valor_pago=0.00,
        canal_origem='WEBSITE_DIRETO'
    )

    # Reserva finalizada histórica
    res3 = Reserva.objects.create(
        quarto=q201,
        cliente=c3,
        data_checkin=date.today() - timedelta(days=10),
        data_checkout=date.today() - timedelta(days=7),
        status='FINALIZADA',
        valor_total=840.00,
        valor_pago=840.00,
        canal_origem='BALCAO'
    )

    # 8. Movimentações Financeiras
    print("Registrando lançamentos financeiros...")
    # Receita parcial de res1
    TransacaoFinanceira.objects.create(
        reserva=res1,
        pousada=pousada_centro,
        tipo='RECEITA',
        valor=900.00,
        categoria='DIARIA',
        data_pagamento=date.today() - timedelta(days=2),
        metodo_pagamento='PIX'
    )
    # Receita quitada de res3
    TransacaoFinanceira.objects.create(
        reserva=res3,
        pousada=pousada_centro,
        tipo='RECEITA',
        valor=840.00,
        categoria='DIARIA',
        data_pagamento=date.today() - timedelta(days=7),
        metodo_pagamento='CARTAO_CREDITO'
    )
    # Despesa operacional (Manutenção)
    TransacaoFinanceira.objects.create(
        pousada=pousada_centro,
        tipo='DESPESA',
        valor=150.00,
        categoria='MANUTENCAO',
        data_pagamento=date.today() - timedelta(days=3),
        metodo_pagamento='PIX'
    )

    print("\n=== Banco de Dados Re-Popularizado com Sucesso! ===")
    print("--- CREDENCIAIS MASTER OPERACIONAIS ---")
    print(f"ADMIN PRINCIPAL -> Usuário: admin      | Senha: admin123")
    print(f"TIAGO ISMAR     -> Usuário: tiagoismar | Senha: limaodoce")
    print(f"GERENTE CENTRO  -> Usuário: gerente    | Senha: gerente123")
    print("=======================================")

if __name__ == "__main__":
    seed()
