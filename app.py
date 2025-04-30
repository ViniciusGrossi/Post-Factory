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
BACKGROUND_IMAGE = "Fundo.jpeg"

def carregar_fonte(tamanho=30):
    """Tenta carregar a fonte Nexa Extra Bold ou usa uma fonte padrão disponível"""
    try:
        return ImageFont.truetype("nexa-extrabold.ttf", tamanho)
    except IOError:
        try:
            return ImageFont.truetype("NexaExtraBold.ttf", tamanho)
        except IOError:
            try:
                return ImageFont.truetype("Nexa-ExtraBold.ttf", tamanho)
            except IOError:
                try:
                    return ImageFont.truetype("Arial.ttf", tamanho)
                except IOError:
                    fonte_default = ImageFont.load_default()
                    st.warning("Fonte Nexa Extra Bold não encontrada. Usando fonte padrão.")
                    return fonte_default

def adicionar_texto(imagem, textos, tamanho_fonte):
    """Adiciona até três frases na parte inferior da imagem"""
    largura, altura = imagem.size
    desenho = ImageDraw.Draw(imagem)
    
    fonte = carregar_fonte(tamanho_fonte)
    espacamento = int(tamanho_fonte * st.session_state.fator_espacamento)
    posicao_y_inicial = altura - (250 + (tamanho_fonte - 30) // 2)
    
    for i, texto in enumerate(textos[:3]):
        if not texto.startswith('-'):
            texto = "- " + texto
        
        bbox = desenho.textbbox((0, 0), texto, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        altura_texto = bbox[3] - bbox[1]
        
        posicao_x = (largura - largura_texto) // 2
        posicao_y = posicao_y_inicial + (i * espacamento)
        
        desenho.text((posicao_x, posicao_y), texto, fill='#7a7a7a', font=fonte)
    
    return imagem

def processar_imagem(plano_de_fundo, logo, textos, posicao_logo=None):
    """Processa uma única imagem, colando o logo e adicionando o texto"""
    # Cria uma cópia do plano de fundo e mantém o modo original quando possível
    resultado = plano_de_fundo.copy()
    
    # Converte para RGB se não estiver em RGB (necessário para salvar como JPEG)
    if resultado.mode != "RGB":
        resultado = resultado.convert("RGB")
    
    # Redimensiona com alta qualidade se necessário
    if st.session_state.redimensionar_fundo:
        resultado = resultado.resize(
            (st.session_state.largura_imagem, st.session_state.altura_imagem), 
            Image.LANCZOS  # Usando o método de alta qualidade LANCZOS (antigo ANTIALIAS)
        )
    
    largura_bg, altura_bg = resultado.size
    largura_padrao = st.session_state.largura_logo
    altura_padrao = st.session_state.altura_logo
    
    # Redimensiona o logo com alta qualidade
    logo = logo.resize((largura_padrao, altura_padrao), Image.LANCZOS)
    
    if posicao_logo:
        x, y = posicao_logo
    else:
        x = (largura_bg - largura_padrao) // 2 + st.session_state.deslocamento_x
        y = (altura_bg - altura_padrao) // 2 - st.session_state.deslocamento_y
    
    # Cola o logo com transparência
    if logo.mode == 'RGBA':
        resultado.paste(logo, (x, y), logo)
    else:
        # Tenta usar o logo sem canal alfa se não tiver RGBA
        resultado.paste(logo, (x, y))
    
    resultado = adicionar_texto(resultado, textos, st.session_state.tamanho_fonte)
    
    return resultado

def get_image_download_link(img, filename, text):
    """Gera um link para download de uma única imagem"""
    buffered = io.BytesIO()
    
    # Salva com otimizações habilitadas e alta qualidade
    img.save(
        buffered, 
        format="JPEG", 
        quality=st.session_state.qualidade_jpeg,
        optimize=True,  # Ativa otimizações
        subsampling=0   # Melhor qualidade de subsampling de cor
    )
    
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/jpg;base64,{img_str}" download="{filename}">{text}</a>'
    return href

def get_zip_download_link(zip_data, filename, text):
    """Gera um link para download de um arquivo ZIP"""
    b64 = base64.b64encode(zip_data).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Inicialização das variáveis de sessão
if 'largura_logo' not in st.session_state:
    st.session_state.largura_logo = 400
if 'altura_logo' not in st.session_state:
    st.session_state.altura_logo = 300
if 'deslocamento_y' not in st.session_state:
    st.session_state.deslocamento_y = 120
if 'deslocamento_x' not in st.session_state:
    st.session_state.deslocamento_x = 0
if 'qualidade_jpeg' not in st.session_state:
    st.session_state.qualidade_jpeg = 95  # Aumentei a qualidade padrão para 95%
if 'tamanho_fonte' not in st.session_state:
    st.session_state.tamanho_fonte = 30
if 'fator_espacamento' not in st.session_state:
    st.session_state.fator_espacamento = 2.0
if 'redimensionar_fundo' not in st.session_state:
    st.session_state.redimensionar_fundo = False
if 'largura_imagem' not in st.session_state:
    st.session_state.largura_imagem = 1080
if 'altura_imagem' not in st.session_state:
    st.session_state.altura_imagem = 1080
if 'atualizar_preview' not in st.session_state:
    st.session_state.atualizar_preview = True
if 'qualidade_preview' not in st.session_state:
    st.session_state.qualidade_preview = "Alta"  # Opção para qualidade da prévia

# Verificação do fundo.jpg
try:
    with open(BACKGROUND_IMAGE, "rb") as f:
        pass
except FileNotFoundError:
    st.error(f"Arquivo obrigatório '{BACKGROUND_IMAGE}' não encontrado na pasta do aplicativo!")
    st.stop()

# Interface do usuário
st.title("🖼️ Gerador de Posts em Massa")
st.markdown("Crie posts com o plano de fundo padrão e logos de empresas, incluindo frases personalizadas.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Configurações Gerais")
    logos_files = st.file_uploader("Upload dos logos (múltiplos)", type=["png"], accept_multiple_files=True)
    
    st.subheader("2. Tamanho da Imagem Final")
    st.session_state.redimensionar_fundo = st.checkbox("Redimensionar imagem final", value=st.session_state.redimensionar_fundo)
    
    if st.session_state.redimensionar_fundo:
        col_w, col_h = st.columns(2)
        with col_w:
            st.session_state.largura_imagem = st.number_input("Largura (px)", min_value=100, max_value=4000, value=st.session_state.largura_imagem)
        with col_h:
            st.session_state.altura_imagem = st.number_input("Altura (px)", min_value=100, max_value=4000, value=st.session_state.altura_imagem)
    
    st.subheader("3. Configurações do Logo")
    st.session_state.largura_logo = st.slider("Largura do Logo", 100, 800, st.session_state.largura_logo)
    st.session_state.altura_logo = st.slider("Altura do Logo", 100, 600, st.session_state.altura_logo)
    
    st.subheader("4. Posição do Logo")
    st.session_state.deslocamento_y = st.slider("Deslocamento vertical (para cima)", -300, 300, st.session_state.deslocamento_y)
    st.session_state.deslocamento_x = st.slider("Deslocamento horizontal", -300, 300, st.session_state.deslocamento_x)
    
    st.subheader("5. Configuração do Texto")
    st.session_state.tamanho_fonte = st.number_input(
        "Tamanho da fonte (pixels)", 
        min_value=4, 
        max_value=96, 
        value=st.session_state.tamanho_fonte,
        help="Ajuste o tamanho da fonte em pixels"
    )
    
    st.session_state.fator_espacamento = st.slider(
        "Espaçamento entre frases", 
        min_value=0.8, 
        max_value=3.0, 
        value=st.session_state.fator_espacamento,
        step=0.1
    )
    
    st.info(f"A fonte atual é de {st.session_state.tamanho_fonte} pixels com espaçamento de {st.session_state.fator_espacamento}x")
    
    # Configurações avançadas de qualidade
    st.subheader("6. Configurações de Qualidade")
    st.session_state.qualidade_jpeg = st.slider("Qualidade de Exportação (%)", 50, 100, st.session_state.qualidade_jpeg)
    
    # Opção para qualidade da prévia
    st.session_state.qualidade_preview = st.radio(
        "Qualidade da Prévia:",
        options=["Padrão", "Alta"],
        index=1 if st.session_state.qualidade_preview == "Alta" else 0,
        help="Alta qualidade pode consumir mais recursos"
    )
    
    if st.button("Atualizar Prévia"):
        st.session_state.atualizar_preview = True
    
    st.subheader("7. Frases sobre a Empresa")
    frases = []
    for i in range(3):
        frase = st.text_input(f"Frase {i+1}", key=f"frase_{i}")
        if frase:
            frases.append(frase)
    
    usar_frases_personalizadas = st.checkbox("Usar frases personalizadas para cada logo")
    
    if usar_frases_personalizadas and logos_files:
        st.info(f"Forneça frases para cada um dos {len(logos_files)} logos:")
        texto_frases_personalizadas = st.text_area(
            "Formato: 'Logo1: Frase1 | Frase2 | Frase3\nLogo2: Frase1 | Frase2 | Frase3'",
            height=150
        )

with col2:
    st.subheader("Visualização e Processamento")
    
    try:
        fonte_teste = carregar_fonte(30)
        if isinstance(fonte_teste, ImageFont.FreeTypeFont):
            st.success("Fonte Nexa Extra Bold carregada com sucesso!")
        else:
            st.warning("Usando fonte padrão.")
    except Exception as e:
        st.warning(f"Erro na fonte: {str(e)}")
    
    if st.button("Processar Imagens"):
        if not logos_files:
            st.error("Por favor, faça upload de pelo menos um logo.")
        elif not frases and not usar_frases_personalizadas:
            st.error("Por favor, insira pelo menos uma frase.")
        else:
            try:
                # Carrega o plano de fundo na melhor qualidade possível
                plano_de_fundo = Image.open(BACKGROUND_IMAGE)
                
                frases_por_logo = {}
                if usar_frases_personalizadas and texto_frases_personalizadas:
                    linhas = texto_frases_personalizadas.strip().split('\n')
                    for linha in linhas:
                        if ':' in linha:
                            nome_logo, frases_texto = linha.split(':', 1)
                            nome_logo = nome_logo.strip()
                            frases_logo = [f.strip() for f in frases_texto.split('|')]
                            frases_por_logo[nome_logo] = frases_logo
                
                if len(logos_files) > 1:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for i, logo_file in enumerate(logos_files):
                                # Carrega cada logo com a melhor qualidade possível
                                logo = Image.open(logo_file)
                                nome_logo = Path(logo_file.name).stem
                                frases_atuais = frases
                                
                                if usar_frases_personalizadas and nome_logo in frases_por_logo:
                                    frases_atuais = frases_por_logo[nome_logo]
                                elif usar_frases_personalizadas and str(i+1) in frases_por_logo:
                                    frases_atuais = frases_por_logo[str(i+1)]
                                
                                resultado = processar_imagem(plano_de_fundo, logo, frases_atuais)
                                img_buffer = io.BytesIO()
                                resultado.save(
                                    img_buffer, 
                                    format="JPEG", 
                                    quality=st.session_state.qualidade_jpeg,
                                    optimize=True,
                                    subsampling=0
                                )
                                zf.writestr(f"{nome_logo}_resultante.jpg", img_buffer.getvalue())
                    
                    with open(temp_zip.name, "rb") as f:
                        zip_data = f.read()
                    
                    st.markdown(get_zip_download_link(zip_data, "posts_gerados.zip", "⬇️ Baixar todas as imagens (ZIP)"), unsafe_allow_html=True)
                    os.unlink(temp_zip.name)
                    
                    st.subheader("Prévia:")
                    primeiro_logo = Image.open(logos_files[0])
                    nome_primeiro_logo = Path(logos_files[0].name).stem
                    frases_primeiro = frases
                    
                    if usar_frases_personalizadas and nome_primeiro_logo in frases_por_logo:
                        frases_primeiro = frases_por_logo[nome_primeiro_logo]
                    
                    resultado_preview = processar_imagem(plano_de_fundo, primeiro_logo, frases_primeiro)
                    st.image(resultado_preview, caption=f"Prévia do post com {nome_primeiro_logo}", use_column_width=True)
                
                else:
                    logo = Image.open(logos_files[0])
                    resultado = processar_imagem(plano_de_fundo, logo, frases)
                    st.image(resultado, caption="Post Gerado", use_column_width=True)
                    nome_arquivo = f"{Path(logos_files[0].name).stem}_resultante.jpg"
                    st.markdown(get_image_download_link(resultado, nome_arquivo, "⬇️ Baixar Imagem"), unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Erro no processamento: {str(e)}")
    
    if logos_files and st.session_state.atualizar_preview:
        st.subheader("Visualização em Tempo Real")
        try:
            plano_de_fundo_preview = Image.open(BACKGROUND_IMAGE)
            primeiro_logo = Image.open(logos_files[0])
            frases_preview = frases if frases else ["Exemplo de frase 1", "Exemplo de frase 2", "Exemplo de frase 3"]
            
            # Usa alta qualidade para a prévia se selecionado
            preview = processar_imagem(plano_de_fundo_preview, primeiro_logo, frases_preview)
            
            st.image(preview, caption="Visualização em Tempo Real", use_column_width=True)
            
            largura_bg, altura_bg = preview.size
            x_pos = (largura_bg - st.session_state.largura_logo) // 2 + st.session_state.deslocamento_x
            y_pos = (altura_bg - st.session_state.altura_logo) // 2 - st.session_state.deslocamento_y
            
            st.info(f"Posição do logo: X={x_pos}px, Y={y_pos}px | Tamanho da fonte: {st.session_state.tamanho_fonte}px | Espaçamento: {st.session_state.fator_espacamento}x")
            st.info(f"Qualidade de exportação: {st.session_state.qualidade_jpeg}% | Prévia: {st.session_state.qualidade_preview}")
        except Exception as e:
            st.warning(f"Erro na visualização: {str(e)}")

with st.expander("Instruções de Uso"):
    st.markdown("""
    ### Requisito Obrigatório:
    - Coloque um arquivo chamado **Fundo.jpg** na mesma pasta do aplicativo
    
    ### Como usar:
    1. Prepare seu arquivo Fundo.jpg (1080x1080px recomendado)
    2. Faça upload dos logos em PNG com transparência
    3. Ajuste o tamanho final da imagem se necessário
    4. Configure tamanho e posição do logo
    5. Ajuste fonte e espaçamento das frases
    6. Configure a qualidade de exportação (95-100% para melhor resultado)
    7. Adicione até 3 frases
    8. Clique em "Processar Imagens"
    
    ### Formato para Frases Personalizadas:
    ```
    NomeDoLogo1: Frase 1 | Frase 2 | Frase 3
    NomeDoLogo2: Frase 1 | Frase 2 | Frase 3
    ```
    
    ### Dicas para Melhor Qualidade:
    - Use arquivos de origem de alta resolução
    - Defina qualidade de exportação para 95% ou superior
    - Evite redimensionar imagens para tamanhos muito menores
    - Logos devem ter fundo transparente (PNG)
    - Se disponível, use a opção de prévia de alta qualidade
    """)
    
    st.markdown("### Configurações Recomendadas para Alta Qualidade:")
    st.code("""
    - Qualidade de Exportação: 95-100%
    - Tamanho da Imagem: Deixe no tamanho original se possível 
    - Formato do Logo: PNG com alta resolução e fundo transparente
    """)