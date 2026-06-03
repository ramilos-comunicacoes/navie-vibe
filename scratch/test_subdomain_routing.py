import os
import sys
import django
from django.test import Client

# Inicializa as configurações do Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel

def run_tests():
    client = Client()
    print("Iniciando testes de subdomínio e validação de URLs...")

    # 1. Testar se o slug 'pousadaramilostiangua' existe no banco
    hotel = Hotel.objects.filter(slug='pousadaramilostiangua').first()
    if not hotel:
        print("AVISO: Pousada 'pousadaramilostiangua' não encontrada no banco. Criando pousada de teste...")
        from hoteis.models import Local
        local, _ = Local.objects.get_or_create(nome="Tianguá Centro", defaults={"endereco": "Centro", "cidade": "Tianguá", "estado": "CE"})
        hotel = Hotel.objects.create(
            nome="Pousada Ramilos Tianguá",
            slug="pousadaramilostiangua",
            local=local,
            descricao="Descrição de teste"
        )
    else:
        print(f"Sucesso: Pousada '{hotel.nome}' encontrada com o slug '{hotel.slug}'.")

    # 2. Testar acesso via subdomínio (pousadaramilostiangua.localhost)
    print("\nTestando acesso a pousadaramilostiangua.localhost:8060...")
    response = client.get('/', HTTP_HOST='pousadaramilostiangua.localhost:8060')
    if response.status_code == 200:
        print("Sucesso: Acesso ao subdomínio pousadaramilostiangua retornou 200 OK.")
        # Verifica se o conteúdo renderizado possui o nome do hotel
        content_str = response.content.decode('utf-8', errors='ignore')
        if "Pousada Ramilos" in content_str:
            print("Sucesso: O HTML renderizado possui o nome do hotel correto.")
        else:
            print("Erro: O HTML renderizado NÃO possui o nome do hotel.")
            
        # VERIFICAÇÃO DO LINK DO CABEÇALHO (Logo da Naviê de volta ao portal principal)
        if 'href="http://localhost:8060/"' in content_str:
            print("Sucesso: O link do cabeçalho aponta para o portal principal (http://localhost:8060/).")
        else:
            print("Erro: O link do cabeçalho NÃO aponta para o portal principal.")
            
        # VERIFICAÇÃO DO FAVICON DINÂMICO
        if hotel.logo and hotel.logo.url in content_str:
            print("Sucesso: O Favicon dinâmico está usando a logo da Pousada.")
        elif not hotel.logo and "logo.png" in content_str:
            print("Sucesso: O Favicon dinâmico está usando o fallback da logo da Naviê.")
        else:
            print("Erro: O Favicon dinâmico está incorreto.")
    else:
        print(f"Erro: Acesso ao subdomínio pousadaramilostiangua retornou status {response.status_code}.")

    # 2.5 Testar se a home page geral gera o link correto para o subdomínio
    print("\nTestando se a home page geral gera o link correto para o subdomínio...")
    response = client.get('/', HTTP_HOST='localhost:8060')
    if response.status_code == 200:
        content_str = response.content.decode('utf-8', errors='ignore')
        expected_link = "http://pousadaramilostiangua.localhost:8060/"
        if expected_link in content_str:
            print("Sucesso: A home page geral contém o link correto para o subdomínio do hotel.")
        else:
            print("Erro: A home page geral NÃO contém o link do subdomínio.")
    else:
        print(f"Erro na home page, status: {response.status_code}")

    # 3. Testar acesso via subdomínio inexistente
    print("\nTestando acesso a inexistente.localhost:8060...")
    response = client.get('/', HTTP_HOST='inexistente.localhost:8060')
    if response.status_code == 200:
        content_str = response.content.decode('utf-8', errors='ignore')
        # Sem hotel associado, deve renderizar a home geral
        if "Viva a Essência" in content_str or "Explorar Hotéis" in content_str:
            print("Sucesso: Acesso com subdomínio inexistente renderizou a home geral.")
        else:
            print("Erro: Acesso com subdomínio inexistente NÃO renderizou a home geral.")
    else:
        print(f"Erro: Acesso com subdomínio inexistente retornou status {response.status_code}.")

    # 4. Testar API de verificação de subdomínio: Disponível
    print("\nTestando API para subdomínio disponível ('nova-pousada')...")
    response = client.get('/api/hotel/verificar-subdominio/', {'slug': 'nova-pousada'})
    if response.status_code == 200:
        data = response.json()
        print(f"API respondeu: {data}")
        if data.get('disponivel') is True:
            print("Sucesso: Subdomínio 'nova-pousada' detectado como disponível.")
        else:
            print("Erro: Subdomínio 'nova-pousada' incorretamente detectado como indisponível.")
    else:
        print(f"Erro na API de verificação, status: {response.status_code}")

    # 5. Testar API de verificação de subdomínio: Indisponível (Já em uso)
    print("\nTestando API para subdomínio já em uso ('pousadaramilostiangua')...")
    response = client.get('/api/hotel/verificar-subdominio/', {'slug': 'pousadaramilostiangua'})
    if response.status_code == 200:
        data = response.json()
        print(f"API respondeu: {data}")
        if data.get('disponivel') is False:
            print("Sucesso: Subdomínio 'pousadaramilostiangua' detectado como indisponível.")
        else:
            print("Erro: Subdomínio já em uso foi incorretamente detectado como disponível.")
    else:
        print(f"Erro na API de verificação, status: {response.status_code}")

    # 6. Testar API de verificação de subdomínio: Reservado
    print("\nTestando API para termo reservado ('admin')...")
    response = client.get('/api/hotel/verificar-subdominio/', {'slug': 'admin'})
    if response.status_code == 200:
        data = response.json()
        print(f"API respondeu: {data}")
        if data.get('disponivel') is False:
            print("Sucesso: Termo reservado 'admin' detectado como indisponível.")
        else:
            print("Erro: Termo reservado 'admin' foi incorretamente detectado como disponível.")
    else:
        print(f"Erro na API de verificação, status: {response.status_code}")

if __name__ == '__main__':
    run_tests()
