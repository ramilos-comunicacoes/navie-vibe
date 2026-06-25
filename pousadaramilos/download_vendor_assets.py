import os
import urllib.request
import re

# Configuração das bibliotecas estáticas (CDNs do projeto original)
LIBRARIES = {
    "vendor/htmx.min.js": "https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js",
    "vendor/alpine.min.js": "https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js",
    "vendor/tailwind.js": "https://cdn.tailwindcss.com",
    "vendor/lucide.min.js": "https://unpkg.com/lucide@latest/dist/umd/lucide.min.js",
    
    # Flatpickr
    "vendor/flatpickr/flatpickr.min.js": "https://cdn.jsdelivr.net/npm/flatpickr",
    "vendor/flatpickr/flatpickr.min.css": "https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css",
    "vendor/flatpickr/pt.js": "https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/pt.js",
    
    # Chart.js
    "vendor/chart.min.js": "https://cdn.jsdelivr.net/npm/chart.js",
    
    # CropperJS
    "vendor/cropperjs/cropper.min.js": "https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js",
    "vendor/cropperjs/cropper.min.css": "https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css",
    
    # Quill Editor
    "vendor/quill/quill.min.js": "https://cdnjs.cloudflare.com/ajax/libs/quill/1.3.7/quill.min.js",
    "vendor/quill/quill.snow.min.css": "https://cdnjs.cloudflare.com/ajax/libs/quill/1.3.7/quill.snow.min.css",
}

def download_file(url, path):
    """Realiza o download de uma URL para um caminho específico no disco."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Baixando: {url} -> {path}...")
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            with open(path, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao baixar {url}: {e}")
        return False

def download_google_fonts(base_static_dir):
    """Obtém as fontes Poppins e Inter dinamicamente da API do Google Fonts."""
    print("\n=== Buscando fontes no Google Fonts ===")
    
    # URL do CSS das fontes desejadas
    css_url = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@700;900&display=swap"
    
    try:
        req = urllib.request.Request(
            css_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            css_content = response.read().decode('utf-8')
            
        # Regex para capturar os blocos @font-face e extrair o font-family, font-weight e src url
        # Exemplo no CSS:
        # /* latin */
        # @font-face {
        #   font-family: 'Inter';
        #   font-style: normal;
        #   font-weight: 400;
        #   font-display: swap;
        #   src: url(https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp5SRy2GedEr.woff2) format('woff2');
        #   unicode-range: U+0000-00FF, ...;
        # }
        
        # Encontra blocos de font-face latinos (geralmente vêm após /* latin */ ou sem comentário)
        blocks = re.findall(r'@font-face\s*\{([^}]+)\}', css_content)
        
        font_count = 0
        for block in blocks:
            # Filtra apenas a fatia de caracteres latinos para evitar baixar 20 arquivos por fonte
            # (No CSS do Google Fonts, cada peso de fonte tem versões para grego, cirílico, vietnamita, latim, etc.)
            # Para simplificar, baixamos as fontes do subconjunto latino
            # Se for o bloco latino, ele costuma vir associado ao comentário anterior. Vamos procurar apenas os blocos principais.
            family_match = re.search(r"font-family:\s*['\"]?([^'\"]+)['\"]?", block)
            weight_match = re.search(r"font-weight:\s*(\d+)", block)
            url_match = re.search(r"url\(([^)]+)\)", block)
            
            if family_match and weight_match and url_match:
                family = family_match.group(1)
                weight = weight_match.group(1)
                url = url_match.group(1)
                
                # Para evitar duplicados de múltiplos subconjuntos (cyrillic, greek, latin-ext, etc.),
                # nós verificamos se este bloco pertence ao subconjunto 'latin' (que é o que precisamos).
                # Infelizmente, a regex simples de bloco não traz o comentário anterior facilmente.
                # Mas no CSS do Google Fonts, o subconjunto 'latin' é o que contém a faixa unicode padrão U+0000-00FF.
                if "U+0000-00FF" in block or "u+0000-00ff" in block:
                    font_filename = f"{family}-{weight}.woff2"
                    dest_path = os.path.join(base_static_dir, "fonts", font_filename)
                    
                    if not os.path.exists(dest_path):
                        download_file(url, dest_path)
                        font_count += 1
                        
        print(f"Downloads de fontes concluídos. {font_count} novos arquivos baixados.")
        
    except Exception as e:
        print(f"Erro ao processar as fontes: {e}")

def main():
    base_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    
    print("=== Iniciando o download de bibliotecas locais ===")
    for rel_path, url in LIBRARIES.items():
        dest = os.path.join(base_static_dir, rel_path)
        # Só baixa se não existir
        if not os.path.exists(dest):
            download_file(url, dest)
        else:
            print(f"Já existe: {rel_path}")
        
    download_google_fonts(base_static_dir)
        
    print("\n=== Todos os downloads concluídos! ===")

if __name__ == "__main__":
    main()
