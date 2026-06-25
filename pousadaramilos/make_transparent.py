import os
from PIL import Image

def remove_black_background(input_path, output_path):
    """Remove o fundo preto da logo branca, tornando-a transparente."""
    if not os.path.exists(input_path):
        print(f"Arquivo não encontrado: {input_path}")
        return
        
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # Se for muito escuro (preto ou quase preto), torna transparente
        # item[0] = R, item[1] = G, item[2] = B, item[3] = A
        r, g, b, a = item
        if r < 40 and g < 40 and b < 40:
            new_data.append((0, 0, 0, 0)) # Totalmente transparente
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Sucesso: Fundo preto removido em {output_path}")

def remove_yellow_background(input_path, output_path):
    """Remove o fundo amarelo da logo, tornando-a transparente."""
    if not os.path.exists(input_path):
        print(f"Arquivo não encontrado: {input_path}")
        return
        
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        r, g, b, a = item
        # Amarelo da marca é em torno de R=250, G=190, B=20
        # Se for muito amarelado, torna transparente
        if r > 200 and g > 160 and b < 110:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Sucesso: Fundo amarelo removido em {output_path}")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base_dir, "static", "images")
    
    # 1. Torna a logo branca transparente (remove fundo preto)
    white_logo_input = os.path.join(img_dir, "logo_white.png")
    remove_black_background(white_logo_input, white_logo_input)
    
    # 2. Torna a logo amarela transparente (remove fundo amarelo)
    yellow_logo_input = os.path.join(img_dir, "logo_yellow.png")
    remove_yellow_background(yellow_logo_input, yellow_logo_input)

if __name__ == "__main__":
    main()
