import os
import sys
import subprocess
import paramiko

# Server Settings
SERVERS = ["187.77.60.248"]
SSH_USER = "root"
SSH_PASSWORD = "papaleguas20@P"
REMOTE_DIR = "/var/www/apps/navievibe"

def get_git_modified_files():
    print("[LOCAL] Detectando arquivos modificados em relação ao origin/main...")
    # Executa git diff para listar os arquivos modificados localmente
    res = subprocess.run("git diff origin/main --name-only", shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print("[-] Erro ao executar git diff. Usando lista manual de emergência.")
        return []
        
    files = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Pula arquivos de outra aplicação/pasta
        if line.startswith("pousadaramilos/"):
            continue
        if line == "deploy_direct.py" or line == "deploy.py":
            continue
        files.append(line)
        
    # Adicionar logos do Manacá explicitamente (pois podem ser arquivos não rastreados/novos)
    logos = [
        "media/restaurantes/logos/manaca_logo.png",
        "media/restaurantes/logos/manaca_flower.png",
        "media/restaurantes/logos/premibeer_logo.png",
        "media/restaurantes/logos/premibeer_favicon.png",
        "media/restaurantes/logos/manaca-da-serra_logo.jpg",
        "media/restaurantes/logos/premibeer_logo.jpg",
        "media/restaurantes/logos/biene-cacau_logo.jpg",
        "media/restaurantes/logos/casa-de-engenho_logo.jpg",
        "media/restaurantes/logos/casa-de-engenho_logo.png",
        "register_restaurants_navie.py",
        "create_restaurant_credentials.py"
    ]
    for logo in logos:
        if os.path.exists(logo) and logo not in files:
            files.append(logo)
            
    print(f"[+] {len(files)} arquivos selecionados para upload.")
    return files

def deploy_to_server(host, files_to_upload):
    print(f"\n" + "="*60)
    print(f"[SSH/SFTP] Iniciando upload direto para: {host}...")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(hostname=host, username=SSH_USER, password=SSH_PASSWORD, port=22, timeout=20)
        print(f"[+] Conectado com sucesso a {host}!")
        
        # 0. Garantir que o banco de dados postgres existe (com o dono navievibe_user)
        create_db_cmd = 'sudo -u postgres psql -t -c "SELECT 1 FROM pg_database WHERE datname=\'navievibe_restaurantes\'" | grep -q 1 || sudo -u postgres psql -c "CREATE DATABASE navievibe_restaurantes OWNER navievibe_user;"'
        print(f"[SSH @ {host}] Verificando banco de dados: {create_db_cmd}")
        stdin, stdout, stderr = ssh.exec_command(create_db_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"[-] Erro ao garantir banco de dados (Código {exit_status})")
            print(stderr.read().decode())
        
        sftp = ssh.open_sftp()
        
        # 1. Enviar os arquivos dinamicamente
        for rel_path in files_to_upload:
            local_path = os.path.abspath(rel_path)
            remote_path = f"{REMOTE_DIR}/{rel_path}".replace("\\", "/")
            
            # Garantir pasta pai remota
            remote_parent = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_parent)
            except IOError:
                # Criar recursivamente diretórios remotos
                parts = remote_parent.split('/')
                current = ""
                for part in parts:
                    if part:
                        current += f"/{part}"
                        try:
                            sftp.stat(current)
                        except IOError:
                            print(f"[SFTP] Criando diretório remoto: {current}")
                            sftp.mkdir(current)
            
            print(f"[SFTP] Enviando: {rel_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
            
        sftp.close()
        print("[+] Todos os arquivos enviados via SFTP!")
        
        # 2. Executar migrações e seeder
        commands = [
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=default",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=hospedagem",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=cinema",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=eventos",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=parques",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=parceiros",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py migrate --database=restaurantes",
            f"cd {REMOTE_DIR} && venv/bin/python manage.py collectstatic --no-input",
            f"cd {REMOTE_DIR} && venv/bin/python register_restaurants_navie.py",
            f"cd {REMOTE_DIR} && venv/bin/python create_restaurant_credentials.py",
            "systemctl restart navievibe"
        ]
        
        for cmd in commands:
            print(f"[SSH @ {host}] Executando: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
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
                # Interrompe se falhar
                if "migrate" in cmd or "register_restaurants" in cmd:
                    return False
                    
        print(f"[+] Servidor {host} atualizado e reiniciado com sucesso!")
        return True
        
    except Exception as e:
        print(f"[-] Erro durante deploy em {host}: {str(e)}")
        return False
    finally:
        ssh.close()

def main():
    files = get_git_modified_files()
    if not files:
        print("[-] Nenhum arquivo modificado detectado para deploy.")
        sys.exit(1)
        
    success_count = 0
    for server in SERVERS:
        if deploy_to_server(server, files):
            success_count += 1
            
    print("\n" + "="*60)
    if success_count == len(SERVERS):
        print(f"[DEPLOY CONCLUÍDO] Sucesso em todos os {success_count} servidores!")
    else:
        print(f"[DEPLOY PARCIAL] Sucesso em {success_count}/{len(SERVERS)} servidores.")
    print("="*60)

if __name__ == "__main__":
    main()
