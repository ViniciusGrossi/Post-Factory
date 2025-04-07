import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import tempfile
import base64
import zipfile
from pathlib import Path

# Configurações do aplicativo
st.set_page_config(page_title="Gerador de Posts em Massa", layout="wide")

def carregar_fonte(tamanho=48):
    """Tenta carregar a fonte Nexa Extra Bold ou usa uma fonte padrão disponível"""
    try:
        # Tenta carregar com o nome correto do arquivo
        return ImageFont.truetype("nexa-extrabold.ttf", tamanho)
    except IOError:
        try:
            # Tenta com outra variação do nome
            return ImageFont.truetype("NexaExtraBold.ttf", tamanho)
        except IOError:
            try:
                # Verifica outras possíveis variações de nome
                return ImageFont.truetype("Nexa-ExtraBold.ttf", tamanho)
            except IOError:
                try:
                    # Tenta carregar a fonte do sistema operacional
                    return ImageFont.truetype("Arial.ttf", tamanho)
                except IOError:
                    # Usa a fonte padrão embutida no PIL
                    fonte_default = ImageFont.load_default()
                    st.warning("Fonte Nexa Extra Bold não encontrada. Usando fonte padrão.")
                    return fonte_default

def adicionar_texto(imagem, textos, tamanho_fonte):
    """Adiciona até três frases na parte inferior da imagem"""
    largura, altura = imagem.size
    desenho = ImageDraw.Draw(imagem)
    
    # Carrega a fonte com o tamanho especificado
    fonte = carregar_fonte(tamanho_fonte)
    
    # Usa o fator de espaçamento definido pelo usuário
    espacamento = int(tamanho_fonte * st.session_state.fator_espacamento)
    
    # Posição inicial para as frases (parte inferior da imagem)
    posicao_y_inicial = altura - (250 + (tamanho_fonte - 48) // 2)  # Ajuste baseado no tamanho da fonte
    
    # Adiciona até três frases
    for i, texto in enumerate(textos[:3]):
        # Adiciona o hífen no início da frase se não existir
        if not texto.startswith('-'):
            texto = "- " + texto
        
        # Dimensões do texto
        bbox = desenho.textbbox((0, 0), texto, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        altura_texto = bbox[3] - bbox[1]
        
        # Centraliza o texto horizontalmente
        posicao_x = (largura - largura_texto) // 2
        posicao_y = posicao_y_inicial + (i * espacamento)
        
        # Adiciona texto em preto sem sombra branca
        desenho.text((posicao_x, posicao_y), texto, fill="black", font=fonte)
    
    return imagem

def processar_imagem(plano_de_fundo, logo, textos, posicao_logo=None):
    """Processa uma única imagem, colando o logo e adicionando o texto"""
    # Cria uma cópia do plano de fundo
    resultado = plano_de_fundo.copy().convert("RGB")
    
    # Redimensiona o plano de fundo se necessário
    if st.session_state.redimensionar_fundo:
        resultado = resultado.resize((st.session_state.largura_imagem, st.session_state.altura_imagem))
    
    largura_bg, altura_bg = resultado.size
    
    # Redimensiona o logo para um tamanho padrão
    largura_padrao = st.session_state.largura_logo
    altura_padrao = st.session_state.altura_logo
    logo = logo.resize((largura_padrao, altura_padrao))
    
    # Define a posição do logo (padrão ou personalizada)
    if posicao_logo:
        x, y = posicao_logo
    else:
        x = (largura_bg - largura_padrao) // 2 + st.session_state.deslocamento_x
        y = (altura_bg - altura_padrao) // 2 - st.session_state.deslocamento_y
    
    # Cola o logo na posição calculada
    resultado.paste(logo, (x, y), logo)
    
    # Adiciona o texto com o tamanho de fonte especificado
    resultado = adicionar_texto(resultado, textos, st.session_state.tamanho_fonte)
    
    return resultado

def get_image_download_link(img, filename, text):
    """Gera um link para download de uma única imagem"""
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/jpg;base64,{img_str}" download="{filename}">{text}</a>'
    return href

def get_zip_download_link(zip_data, filename, text):
    """Gera um link para download de um arquivo ZIP"""
    b64 = base64.b64encode(zip_data).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Inicializa variáveis na sessão se ainda não existirem
if 'largura_logo' not in st.session_state:
    st.session_state.largura_logo = 400
if 'altura_logo' not in st.session_state:
    st.session_state.altura_logo = 300
if 'deslocamento_y' not in st.session_state:
    st.session_state.deslocamento_y = 120
if 'deslocamento_x' not in st.session_state:
    st.session_state.deslocamento_x = 0
if 'qualidade_jpeg' not in st.session_state:
    st.session_state.qualidade_jpeg = 90
if 'tamanho_fonte' not in st.session_state:
    st.session_state.tamanho_fonte = 48
if 'fator_espacamento' not in st.session_state:
    st.session_state.fator_espacamento = 1.3
if 'redimensionar_fundo' not in st.session_state:
    st.session_state.redimensionar_fundo = False
if 'largura_imagem' not in st.session_state:
    st.session_state.largura_imagem = 1080
if 'altura_imagem' not in st.session_state:
    st.session_state.altura_imagem = 1080
if 'atualizar_preview' not in st.session_state:
    st.session_state.atualizar_preview = True

# Título e descrição
st.title("🖼️ Gerador de Posts em Massa")
st.markdown("Crie posts com seu plano de fundo padronizado e logos de empresas, incluindo frases personalizadas.")

# Cria layout com colunas
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Imagens")
    
    # Upload do plano de fundo
    plano_de_fundo_file = st.file_uploader("Upload do plano de fundo", type=["jpg", "jpeg", "png"])
    
    # Upload dos logos (múltiplos arquivos)
    logos_files = st.file_uploader("Upload dos logos (múltiplos)", type=["png"], accept_multiple_files=True)
    
    # Tamanho da imagem final
    st.subheader("2. Tamanho da Imagem Final")
    st.session_state.redimensionar_fundo = st.checkbox("Redimensionar imagem final", value=st.session_state.redimensionar_fundo)
    
    if st.session_state.redimensionar_fundo:
        col_w, col_h = st.columns(2)
        with col_w:
            st.session_state.largura_imagem = st.number_input("Largura (px)", min_value=100, max_value=2000, value=st.session_state.largura_imagem)
        with col_h:
            st.session_state.altura_imagem = st.number_input("Altura (px)", min_value=100, max_value=2000, value=st.session_state.altura_imagem)
    
    # Configurações de tamanho e posição do logo
    st.subheader("3. Configurações do Logo")
    st.session_state.largura_logo = st.slider("Largura do Logo", 100, 800, st.session_state.largura_logo)
    st.session_state.altura_logo = st.slider("Altura do Logo", 100, 600, st.session_state.altura_logo)
    
    # Posição do logo
    st.subheader("4. Posição do Logo")
    st.session_state.deslocamento_y = st.slider("Deslocamento vertical (para cima)", -300, 300, st.session_state.deslocamento_y)
    st.session_state.deslocamento_x = st.slider("Deslocamento horizontal", -300, 300, st.session_state.deslocamento_x)
    
    # Configuração da fonte e espaçamento
    st.subheader("5. Configuração do Texto")
    
    # Usa number_input em vez de slider para garantir que o valor seja exato
    st.session_state.tamanho_fonte = st.number_input(
        "Tamanho da fonte (pixels)", 
        min_value=24, 
        max_value=96, 
        value=st.session_state.tamanho_fonte,
        help="Ajuste o tamanho da fonte em pixels"
    )
    
    # Novo controle para o espaçamento entre frases
    st.session_state.fator_espacamento = st.slider(
        "Espaçamento entre frases", 
        min_value=0.8, 
        max_value=2.0, 
        value=st.session_state.fator_espacamento,
        step=0.1,
        help="Ajuste o espaçamento entre as frases (1.0 = normal, 2.0 = dobro do espaço)"
    )
    
    st.info(f"A fonte atual é de {st.session_state.tamanho_fonte} pixels com espaçamento de {st.session_state.fator_espacamento}x")
    
    # Botão para atualizar a prévia
    if st.button("Atualizar Prévia"):
        st.session_state.atualizar_preview = True
    
    # Qualidade da imagem
    st.session_state.qualidade_jpeg = st.slider("Qualidade da Imagem (%)", 50, 100, st.session_state.qualidade_jpeg)
    
    # Campos para as frases
    st.subheader("6. Frases sobre a Empresa")
    frases = []
    for i in range(3):
        frase = st.text_input(f"Frase {i+1}", key=f"frase_{i}")
        if frase:
            frases.append(frase)
    
    # Opção para usar frases personalizadas para cada logo
    usar_frases_personalizadas = st.checkbox("Usar frases personalizadas para cada logo")
    
    if usar_frases_personalizadas and logos_files:
        st.info(f"Por favor, forneça frases para cada um dos {len(logos_files)} logos no campo abaixo")
        texto_frases_personalizadas = st.text_area(
            "Insira as frases no formato 'Logo1: Frase1 | Frase2 | Frase3\nLogo2: Frase1 | Frase2 | Frase3'",
            height=150
        )

with col2:
    st.subheader("Visualização e Processamento")
    
    # Verifica se a fonte está disponível
    try:
        # Tenta carregar a fonte para mostrar mensagem de sucesso
        fonte_teste = carregar_fonte(48)
        if isinstance(fonte_teste, ImageFont.FreeTypeFont):
            st.success("Fonte Nexa Extra Bold carregada com sucesso!")
        else:
            st.warning("Não foi possível carregar a fonte Nexa Extra Bold. Usando fonte padrão.")
    except Exception as e:
        st.warning(f"Erro ao verificar a fonte: {str(e)}")
    
    # Exibe informações sobre o tamanho da imagem final
    if plano_de_fundo_file:
        try:
            plano_de_fundo_preview = Image.open(plano_de_fundo_file)
            largura_original, altura_original = plano_de_fundo_preview.size
            
            if st.session_state.redimensionar_fundo:
                st.info(f"Tamanho original: {largura_original}×{altura_original}px | Tamanho final: {st.session_state.largura_imagem}×{st.session_state.altura_imagem}px")
            else:
                st.info(f"Tamanho da imagem: {largura_original}×{altura_original}px")
        except:
            st.warning("Não foi possível ler o tamanho da imagem de fundo.")
    
    # Botão para processar as imagens
    if st.button("Processar Imagens"):
        if plano_de_fundo_file is None:
            st.error("Por favor, faça upload de uma imagem de plano de fundo.")
        elif not logos_files:
            st.error("Por favor, faça upload de pelo menos um logo.")
        elif not frases and not usar_frases_personalizadas:
            st.error("Por favor, insira pelo menos uma frase.")
        else:
            # Carrega o plano de fundo
            plano_de_fundo = Image.open(plano_de_fundo_file)
            
            # Processa as frases personalizadas se necessário
            frases_por_logo = {}
            if usar_frases_personalizadas and texto_frases_personalizadas:
                linhas = texto_frases_personalizadas.strip().split('\n')
                for linha in linhas:
                    if ':' in linha:
                        nome_logo, frases_texto = linha.split(':', 1)
                        nome_logo = nome_logo.strip()
                        frases_logo = [f.strip() for f in frases_texto.split('|')]
                        frases_por_logo[nome_logo] = frases_logo
            
            # Cria um ZIP para múltiplas imagens
            if len(logos_files) > 1:
                # Prepara o arquivo ZIP
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                    with zipfile.ZipFile(temp_zip.name, 'w') as zf:
                        for i, logo_file in enumerate(logos_files):
                            logo = Image.open(logo_file)
                            
                            # Determina quais frases usar para este logo
                            frases_atuais = frases
                            nome_logo = Path(logo_file.name).stem
                            if usar_frases_personalizadas and nome_logo in frases_por_logo:
                                frases_atuais = frases_por_logo[nome_logo]
                            elif usar_frases_personalizadas and str(i+1) in frases_por_logo:
                                frases_atuais = frases_por_logo[str(i+1)]
                            
                            # Processa a imagem
                            resultado = processar_imagem(plano_de_fundo, logo, frases_atuais)
                            
                            # Salva no arquivo ZIP
                            img_buffer = io.BytesIO()
                            resultado.save(img_buffer, format="JPEG", quality=st.session_state.qualidade_jpeg)
                            
                            # Adiciona ao ZIP
                            zf.writestr(f"{nome_logo}_resultante.jpg", img_buffer.getvalue())
                
                # Cria link para download do ZIP
                with open(temp_zip.name, "rb") as f:
                    zip_data = f.read()
                    
                st.markdown(get_zip_download_link(zip_data, "posts_gerados.zip", "⬇️ Baixar todas as imagens (ZIP)"), unsafe_allow_html=True)
                
                # Limpa o arquivo temporário
                os.unlink(temp_zip.name)
                
                # Mostra prévia da primeira imagem
                st.subheader("Prévia:")
                primeiro_logo = Image.open(logos_files[0])
                nome_primeiro_logo = Path(logos_files[0].name).stem
                
                frases_primeiro = frases
                if usar_frases_personalizadas and nome_primeiro_logo in frases_por_logo:
                    frases_primeiro = frases_por_logo[nome_primeiro_logo]
                elif usar_frases_personalizadas and "1" in frases_por_logo:
                    frases_primeiro = frases_por_logo["1"]
                
                resultado_preview = processar_imagem(plano_de_fundo, primeiro_logo, frases_primeiro)
                st.image(resultado_preview, caption=f"Prévia do post com {nome_primeiro_logo}", use_column_width=True)
                
            # Processa uma única imagem
            else:
                logo = Image.open(logos_files[0])
                resultado = processar_imagem(plano_de_fundo, logo, frases)
                
                # Exibe a imagem resultante
                st.image(resultado, caption="Post Gerado", use_column_width=True)
                
                # Link para download
                nome_arquivo = f"{Path(logos_files[0].name).stem}_resultante.jpg"
                st.markdown(get_image_download_link(resultado, nome_arquivo, "⬇️ Baixar Imagem"), unsafe_allow_html=True)
    
    # Visualização em tempo real (quando disponível)
    if plano_de_fundo_file and logos_files and st.session_state.atualizar_preview:
        st.subheader("Visualização em Tempo Real")
        try:
            plano_de_fundo_preview = Image.open(plano_de_fundo_file)
            primeiro_logo = Image.open(logos_files[0])
            
            # Usa as frases atuais ou um placeholder para visualização
            frases_preview = frases if frases else ["Exemplo de frase 1", "Exemplo de frase 2", "Exemplo de frase 3"]
            
            # Gera a prévia
            preview = processar_imagem(plano_de_fundo_preview, primeiro_logo, frases_preview)
            st.image(preview, caption="Visualização em Tempo Real", use_column_width=True)
            
            # Informações de posicionamento
            largura_bg, altura_bg = preview.size
            x_pos = (largura_bg - st.session_state.largura_logo) // 2 + st.session_state.deslocamento_x
            y_pos = (altura_bg - st.session_state.altura_logo) // 2 - st.session_state.deslocamento_y
            
            st.info(f"Posição do logo: X={x_pos}px, Y={y_pos}px | Tamanho da fonte: {st.session_state.tamanho_fonte}px | Espaçamento: {st.session_state.fator_espacamento}x")
        except Exception as e:
            st.warning(f"Não foi possível gerar a visualização em tempo real: {str(e)}")

# Área de personalização avançada e instruções
with st.expander("Instruções de Uso"):
    st.markdown("""
    ### Como usar:
    1. Faça upload de uma imagem de plano de fundo
    2. Faça upload de um ou mais logos (em formato PNG com transparência)
    3. Ajuste o tamanho final da imagem se necessário
    4. Configure o tamanho e posição do logo usando os controles deslizantes
    5. Ajuste o tamanho da fonte e o espaçamento entre as frases
    6. Adicione até três frases sobre a empresa (cada uma começará com um hífen automaticamente)
    7. Opcionalmente, configure frases personalizadas para cada logo
    8. Clique em "Atualizar Prévia" para ver o resultado antes de processar
    9. Clique em "Processar Imagens" para gerar os posts
    
    ### Frases Personalizadas:
    Para usar frases diferentes para cada logo, marque a caixa "Usar frases personalizadas" e insira-as no formato:
    ```
    NomeDoLogo1: Primeira frase | Segunda frase | Terceira frase
    NomeDoLogo2: Primeira frase | Segunda frase | Terceira frase
    ```
    
    O nome do logo deve corresponder ao nome do arquivo sem a extensão.
    
    ### Dicas:
    - Para melhor resultado, use imagens PNG com fundo transparente para os logos
    - Use o deslocamento horizontal e vertical para posicionar precisamente o logo
    - Ajuste o tamanho da fonte de acordo com o comprimento das suas frases
    - Personalize o espaçamento entre frases para melhor legibilidade
    - Use a visualização em tempo real para ajustar a configuração antes de processar
    """)
    
    st.markdown("### Sobre Fontes:")
    st.info("Este aplicativo está configurado para usar a fonte 'nexa-extrabold.ttf'. Certifique-se que o arquivo está na mesma pasta do script.")