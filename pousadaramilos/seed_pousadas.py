import os
import django

# Configura o ambiente Django para execução direta do script
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from sistema.models import Pousada

def seed_pousadas():
    print("=== Iniciando População das Pousadas (Produção) ===")
    
    # Limpa pousadas se já existirem para evitar duplicados
    Pousada.objects.all().delete()
    
    # 1. Pousada Ramilos Sertão
    pousada_sertao = Pousada.objects.create(
        nome="Pousada Ramilos Sertão",
        endereco="Sitio Bela Vista, N° S/N, Complemento: Sala 1, Bairro: Zona Rural, Tianguá - CE, 62336-000",
        telefone_whatsapp="5588999999999",  # WhatsApp de exemplo, pode ser alterado no painel Admin
        cnpj="12.345.678/0001-90",
        cor_primaria_hex="#2563eb",  # Azul
        mapa_latitude=-3.6658475,
        mapa_longitude=-40.9367097,
        ativo=True
    )
    print(f"Criada: {pousada_sertao.nome}")
    
    # 2. Pousada Luís Correia (Ramilos Praia)
    pousada_praia = Pousada.objects.create(
        nome="Pousada Luís Correia",
        endereco="Av. Beira Mar, S/N - Praia de Atalaia, Luís Correia - PI, 64220-000",
        telefone_whatsapp="5586999999999",  # WhatsApp de exemplo, pode ser alterado no painel Admin
        cnpj="12.345.678/0002-71",
        cor_primaria_hex="#10b981",  # Verde
        mapa_latitude=-2.888536,
        mapa_longitude=-41.6514733,
        ativo=True
    )
    print(f"Criada: {pousada_praia.nome}")
    
    # 3. Pousada Serra - Tianguá
    pousada_serra = Pousada.objects.create(
        nome="Pousada Serra - Tianguá",
        endereco="Sítio Santo Antônio, N° S/N - Zona Rural, Tianguá - CE, 62336-000",
        telefone_whatsapp="5588999999998",  # WhatsApp de exemplo, pode ser alterado no painel Admin
        cnpj="12.345.678/0003-52",
        cor_primaria_hex="#8b5cf6",  # Violeta
        mapa_latitude=-3.7439608,
        mapa_longitude=-41.0070228,
        ativo=True
    )
    print(f"Criada: {pousada_serra.nome}")
    
    print("=== População finalizada com sucesso! ===")

if __name__ == '__main__':
    seed_pousadas()
