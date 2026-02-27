import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================================================================
# 1. Configuração da Página do Streamlit
# ==============================================================================
st.set_page_config(page_title="Painel Tesouro Nacional - Anual", layout="wide")

# ==============================================================================
# 2. Leitura e Limpeza dos Dados (Função Dinâmica Anual)
# ==============================================================================
@st.cache_data
def carregar_dados_anuais(nome_arquivo):
    
    # 1. Leitura
    df_wide = pd.read_excel(nome_arquivo)
    
    # 2. Melt: Transforma as colunas de anos em linhas
    # Usamos var_name='Ano_Str' para capturar os cabeçalhos das colunas
    df_tidy = df_wide.melt(id_vars=['Discriminação'], var_name='Ano_Str', value_name='Valor_Bruto')
    
    # 3. Limpeza dos Anos: Garante que apenas colunas que sejam anos (números) fiquem na tabela
    # O errors='coerce' transforma colunas intrusas (ex: "%", "Total") em vazio (NaN)
    df_tidy['Ano'] = pd.to_numeric(df_tidy['Ano_Str'], errors='coerce')
    df_tidy = df_tidy.dropna(subset=['Ano'])
    df_tidy['Ano'] = df_tidy['Ano'].astype(int) # Converte para número inteiro (ex: 2024)
    
    # 4. Limpeza de números (preparado para lidar com o sinal de % da planilha do PIB)
    def limpar_numero(valor):
        if pd.isna(valor): 
            return None
        if isinstance(valor, (int, float)): 
            return float(valor)
            
        v_str = str(valor).strip()
        if v_str == '-': 
            return 0.0
            
        # Se a planilha tiver o sinal de %, nós o removemos antes de converter para número
        if '%' in v_str:
            v_str = v_str.replace('%', '')
            
        try: 
            return float(v_str.replace('.', '').replace(',', '.'))
        except: 
            return None 
        
    df_tidy['Valor'] = df_tidy['Valor_Bruto'].apply(limpar_numero)
    
    # Remove colunas antigas e organiza
    df_tidy = df_tidy.dropna(subset=['Valor']).drop(columns=['Valor_Bruto', 'Ano_Str'])
    return df_tidy[['Discriminação', 'Ano', 'Valor']].sort_values(by=['Discriminação', 'Ano'])

# Carregando as TRÊS planilhas anuais
df_corrente = carregar_dados_anuais('rtn_anual_corrente.xlsx')
df_constante = carregar_dados_anuais('rtn_anual_constante.xlsx')
df_pib = carregar_dados_anuais('rtn_anual_%pib.xlsx')


# ==============================================================================
# 3. Construção da Interface Visual
# ==============================================================================
st.title("📊 Painel de Execução Orçamentária Anual")
st.markdown("Selecione as discriminações e o intervalo de anos desejado:")

# --- FILTRO 1: Categoria ---
categorias = df_corrente['Discriminação'].unique()
categorias_selecionadas = st.multiselect(
    "Discriminação (selecione uma ou mais):", 
    options=categorias,
    default=[categorias[0]] 
)

# --- FILTROS DE DATA (Apenas Anos) ---
# Extraímos os anos únicos e os ordenamos
anos_disponiveis = sorted(df_corrente['Ano'].unique().tolist())

# Usamos apenas 2 colunas para ficar elegante na tela
col1, col2 = st.columns(2)

with col1:
    ano_inicio = st.selectbox("Ano Início", anos_disponiveis, index=0)
with col2:
    ano_fim = st.selectbox("Ano Fim", anos_disponiveis, index=len(anos_disponiveis)-1)

st.divider()

# ==============================================================================
# 4. Lógica de Filtragem e Geração dos 3 Gráficos
# ==============================================================================

# Regras de validação
if len(categorias_selecionadas) == 0:
    st.warning("⚠️ Por favor, selecione pelo menos uma discriminação.")
elif ano_fim < ano_inicio:
    st.error("⚠️ Atenção: O 'Ano Fim' não pode ser anterior ao 'Ano Início'.")
else:
    
    # ---------------------------------------------------------
    # GRÁFICO 1: VALORES CORRENTES
    # ---------------------------------------------------------
    st.subheader("📈 Valores Correntes")
    
    mask_corr = (df_corrente['Discriminação'].isin(categorias_selecionadas)) & \
                (df_corrente['Ano'] >= ano_inicio) & \
                (df_corrente['Ano'] <= ano_fim)
                
    fig_corr = px.line(
        df_corrente[mask_corr], x='Ano', y='Valor', color='Discriminação', markers=True, title=''
    )
    
    # O dtick=1 garante que o eixo X mostre os anos de 1 em 1 (sem quebrar em 2020.5)
    fig_corr.update_xaxes(title="", dtick=1)
    fig_corr.update_yaxes(title="Valor (R$ Milhões)")
    fig_corr.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Ano:</b> %{x}<br><b>Valor:</b> R$ %{y:,.1f} Milhões')
    fig_corr.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    st.plotly_chart(fig_corr, use_container_width=True)
    
    
    # ---------------------------------------------------------
    # GRÁFICO 2: VALORES CONSTANTES
    # ---------------------------------------------------------
    st.write("") 
    st.subheader("📊 Valores Constantes (Dez/2025)")
    
    mask_const = (df_constante['Discriminação'].isin(categorias_selecionadas)) & \
                 (df_constante['Ano'] >= ano_inicio) & \
                 (df_constante['Ano'] <= ano_fim)
                 
    fig_const = px.line(
        df_constante[mask_const], x='Ano', y='Valor', color='Discriminação', markers=True, title=''
    )
    
    fig_const.update_xaxes(title="", dtick=1)
    fig_const.update_yaxes(title="Valor (R$ Milhões)")
    fig_const.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Ano:</b> %{x}<br><b>Valor:</b> R$ %{y:,.1f} Milhões')
    fig_const.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    st.plotly_chart(fig_const, use_container_width=True)


    # ---------------------------------------------------------
    # GRÁFICO 3: PROPORÇÃO DO PIB
    # ---------------------------------------------------------
    st.write("") 
    st.subheader("🥧 Proporção do PIB")
    
    mask_pib = (df_pib['Discriminação'].isin(categorias_selecionadas)) & \
               (df_pib['Ano'] >= ano_inicio) & \
               (df_pib['Ano'] <= ano_fim)
               
    fig_pib = px.line(
        df_pib[mask_pib], x='Ano', y='Valor', color='Discriminação', markers=True, title=''
    )
    
    fig_pib.update_xaxes(title="", dtick=1)
    fig_pib.update_yaxes(title="% do PIB")
    # Formatação do texto do mouse mudou para mostrar o símbolo de % no final
    fig_pib.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Ano:</b> %{x}<br><b>Valor:</b> %{y:,.2f}%')
    fig_pib.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    st.plotly_chart(fig_pib, use_container_width=True)