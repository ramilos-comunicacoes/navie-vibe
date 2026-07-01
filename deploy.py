import sys
import os
import subprocess
import time
try:
    import paramiko
except ImportError:
    print("Biblioteca 'paramiko' não encontrada. Instalando...")
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"])
    import paramiko

# Configurações de Produção
SERVERS = ["187.77.60.248"]
SSH_USER = "root"
SSH_PASSWORD = "papaleguas20@P"
REMOTE_DIR = "/var/www/apps/navievibe"

def run_local_cmd(cmd, desc):
    print(f"\n[LOCAL] {desc}...")
    print(f"Executando: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Erro ao executar: {desc}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
        return False
    print(f"[+] Sucesso: {desc}")
    if res.stdout:
        print(res.stdout.strip())
    return True

def deploy_to_server(host):
    print(f"\n" + "="*50)
    print(f"[SSH] Conectando ao servidor: {host}...")
    print("="*50)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname=host, username=SSH_USER, password=SSH_PASSWORD, port=22, timeout=20)
        print(f"[+] Conectado com sucesso a {host}!")
        
        # Lista de comandos para rodar no servidor
        commands = [
            f"cd {REMOTE_DIR} && git pull origin main",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=default",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=hospedagem",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=cinema",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=eventos",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=parques",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=parceiros",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=restaurantes",
            "systemctl restart navievibe"
        ]
        
        for cmd in commands:
            print(f"\n[REMOTE @ {host}] Executando: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # Aguarda o término da execução
            exit_status = stdout.channel.recv_exit_status()
            
            out_lines = stdout.read().decode('utf-8').strip()
            err_lines = stderr.read().decode('utf-8').strip()
            
            if exit_status == 0:
                print(f"[+] Sucesso!")
                if out_lines:
                    print(out_lines)
            else:
                print(f"[-] Erro (Código {exit_status})")
                if out_lines:
                    print(f"Stdout:\n{out_lines}")
                if err_lines:
                    print(f"Stderr:\n{err_lines}")
                
                # Se falhar no pull ou migrações críticas, paramos o deploy
                if "git pull" in cmd or "migrate" in cmd:
                    print(f"[-] Interrompendo deploy no servidor {host} devido a falha crítica.")
                    return False
        
        print(f"\n[+] Servidor {host} atualizado e reiniciado com sucesso!")
        return True
        
    except Exception as e:
        print(f"[-] Falha na conexão ou execução em {host}: {str(e)}")
        return False
    finally:
        ssh.close()

def main():
    print("="*60)
    print("   SCRIPT DE DEPLOY AUTOMÁTICO - NAVIÊ VIBE")
    print("="*60)
    
    # 1. Obter mensagem de commit
    commit_msg = "deploy: atualizacao automatica"
    if len(sys.argv) > 1:
        commit_msg = sys.argv[1]
    
    # 2. Verificar modificações locais
    print("\n[1/3] Verificando modificações git locais...")
    status_res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    
    if status_res.stdout.strip():
        print("[!] Modificações locais detectadas. Adicionando e fazendo commit...")
        if not run_local_cmd("git add .", "Adicionar arquivos ao git"):
            sys.exit(1)
        if not run_local_cmd(f'git commit -m "{commit_msg}"', "Fazer commit local"):
            sys.exit(1)
    else:
        print("[+] Nenhum arquivo modificado pendente de commit.")

    # 3. Enviar para o GitHub
    print("\n[2/3] Enviando commits para o GitHub...")
    # Tenta descobrir o branch atual
    branch_res = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    current_branch = branch_res.stdout.strip() or "main"
    
    if not run_local_cmd(f"git push origin {current_branch}", f"Push para GitHub (branch: {current_branch})"):
        print("[-] Falha ao subir para o GitHub. Abortando deploy de produção.")
        sys.exit(1)

    # 4. Deploy nos servidores de produção
    print("\n[3/3] Iniciando deploy nos servidores de produção...")
    success_count = 0
    for server in SERVERS:
        if deploy_to_server(server):
            success_count += 1
            
    print("\n" + "="*60)
    if success_count == len(SERVERS):
        print(f"   DEPLOY CONCLUÍDO COM SUCESSO NOS {success_count} SERVIDORES!")
    else:
        print(f"   DEPLOY PARCIALMENTE CONCLUÍDO ({success_count}/{len(SERVERS)} servidores de pé).")
    print("="*60)

if __name__ == "__main__":
    main()
