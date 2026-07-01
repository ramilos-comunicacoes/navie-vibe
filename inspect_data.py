import os
import sys
import django

# Inicializa o ambiente do Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navievibe.settings")
django.setup()

from core.models import Empresa
from hoteis.models import Hotel
from restaurantes.models import Restaurante

def inspect_all():
    print("=" * 70)
    print("        INSPEÇÃO DE TENANTS E EMPRESAS - NAVIÊ VIBE")
    print("=" * 70)
    
    # --- 1. EMPRESAS (Banco default) ---
    print("\n>>> 1. EMPRESAS CADASTRADAS (Grupo/Portal Unificado) <<<")
    try:
        empresas = Empresa.objects.all()
        if not empresas.exists():
            print("Nenhuma Empresa cadastrada no banco principal.")
        for emp in empresas:
            print(f"\n[Empresa ID {emp.id}] {emp.nome_fantasia}")
            print(f"  Razão Social : {emp.razao_social}")
            print(f"  CNPJ         : {emp.cnpj}")
            print(f"  Categoria    : {emp.get_categoria_display()}")
            print(f"  Subdomínio   : {emp.slug}.navievibe.com" if emp.slug else "  Subdomínio   : (Sem slug)")
            print(f"  Portal Rede  : {emp.get_modalidade_portal_display()}")
            print(f"  Localização  : {emp.cidade} - {emp.estado}")
            print(f"  Contato      : {emp.email_contato} | {emp.telefone_contato}")
    except Exception as e:
        print(f"Erro ao consultar Empresas: {str(e)}")

    # --- 2. HOTÉIS E POUSADAS (Banco hospedagem) ---
    print("\n" + "=" * 70)
    print(">>> 2. HOTÉIS / POUSADAS CADASTRADAS <<<")
    try:
        hoteis = Hotel.objects.all()
        if not hoteis.exists():
            print("Nenhum Hotel/Pousada cadastrado no banco de hospedagem.")
        for hotel in hoteis:
            emp_vinc = "Nenhum"
            if hotel.empresa_id:
                try:
                    emp = Empresa.objects.filter(id=hotel.empresa_id).first()
                    emp_vinc = f"{emp.nome_fantasia} (ID {emp.id})" if emp else f"ID {hotel.empresa_id} (Não encontrada)"
                except Exception:
                    emp_vinc = f"ID {hotel.empresa_id} (Erro ao buscar empresa)"
                
            print(f"\n[Hotel ID {hotel.id}] {hotel.nome}")
            print(f"  Subdomínio   : {hotel.slug}.navievibe.com" if hotel.slug else "  Subdomínio   : (Sem slug)")
            print(f"  Status       : {hotel.get_status_display()}")
            print(f"  Destaque     : {'Sim' if hotel.destaque else 'Não'}")
            print(f"  Venda Online : {'Sim' if hotel.venda_online else 'Não'}")
            print(f"  Grupo/Empresa: {emp_vinc}")
            print(f"  Endereço     : {hotel.endereco_completo or 'Não informado'}")
            print(f"  WhatsApp     : {hotel.whatsapp or 'Não informado'}")
    except Exception as e:
        print(f"Erro ao consultar Hotéis/Pousadas: {str(e)}")

    # --- 3. RESTAURANTES (Banco restaurantes) ---
    print("\n" + "=" * 70)
    print(">>> 3. RESTAURANTES CADASTRADOS <<<")
    try:
        restaurantes = Restaurante.objects.using('restaurantes').all()
        if not restaurantes.exists():
            print("Nenhum restaurante cadastrado no banco de restaurantes.")
        for rest in restaurantes:
            print(f"\n[Restaurante ID {rest.id}] {rest.nome}")
            print(f"  Subdomínio   : {rest.slug}.navievibe.com" if rest.slug else "  Subdomínio   : (Sem slug)")
            print(f"  Especialidade: {rest.especialidade or 'Não informada'}")
            print(f"  Cidade       : {rest.cidade_nome or 'Não informada'}")
            print(f"  Ativo        : {'Sim' if rest.ativo else 'Não'}")
            print(f"  Venda Online : {'Sim' if rest.venda_online else 'Não'}")
            print(f"  WhatsApp     : {rest.whatsapp or 'Não informado'}")
            print(f"  Cores Extraídas: Primária: {rest.cor_primaria} | Secundária: {rest.cor_secundaria}")
    except Exception as e:
        print(f"Erro ao consultar Restaurantes: {str(e)}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    inspect_all()
