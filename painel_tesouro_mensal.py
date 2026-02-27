import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================================================================
# 1. Configuração da Página do Streamlit
# ==============================================================================
st.set_page_config(page_title="Painel Tesouro Nacional - Mensal", layout="wide")

# ==============================================================================
# 2. Leitura e Limpeza dos Dados (Função Dinâmica)
# ==============================================================================
# Adicionamos 'nome_arquivo' como parâmetro. O cache agora é inteligente: 
# ele guarda na memória o resultado para cada arquivo diferente.
@st.cache_data
def carregar_dados(nome_arquivo):
    
    # 1. Leitura do arquivo passado como parâmetro
    df_wide = pd.read_excel(nome_arquivo)
    
    # 2. Melt (Transformando Largo em Longo)
    df_tidy = df_wide.melt(id_vars=['Discriminação'], var_name='Mes_Ano_Str', value_name='Valor_Bruto')
    
    # 3. Limpeza de números
    def limpar_numero(valor):
        if pd.isna(valor) or isinstance(valor, (int, float)): 
            return valor
        v_str = str(valor).strip()
        if v_str == '-': 
            return 0.0
        try: 
            return float(v_str.replace('.', '').replace(',', '.'))
        except: 
            return None 
        
    df_tidy['Valor'] = df_tidy['Valor_Bruto'].apply(limpar_numero)
    
    # 4. Ajuste de Datas
    df_tidy['Data'] = pd.to_datetime(df_tidy['Mes_Ano_Str'], errors='coerce')
    df_tidy = df_tidy.dropna(subset=['Data']).drop(columns=['Valor_Bruto'])
    
    # Retorna o DataFrame final organizado
    return df_tidy[['Discriminação', 'Data', 'Valor']].sort_values(by=['Discriminação', 'Data'])

# Carregamos as DUAS planilhas usando a mesma função!
df_corrente = carregar_dados('rtn_mensal_corrente.xlsx')
df_constante = carregar_dados('rtn_mensal_constante.xlsx')


# ==============================================================================
# 3. Construção da Interface Visual (Filtros Únicos para ambos)
# ==============================================================================
# Título principal do aplicativo
st.title("📊 Painel de Execução Orçamentária Mensal")
st.markdown("Selecione as discriminações e o período desejado abaixo para atualizar ambos os gráficos:")

# --- FILTRO 1: Categoria ---
# Como as categorias são as mesmas nas duas planilhas, podemos puxar a lista de qualquer uma
categorias = df_corrente['Discriminação'].unique()
categorias_selecionadas = st.multiselect(
    "Discriminação (selecione uma ou mais):", 
    options=categorias,
    default=[categorias[0]] 
)

# --- FILTROS DE DATA ---
meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
              7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
nomes_meses = list(meses_dict.values())
anos_disponiveis = sorted(df_corrente['Data'].dt.year.unique().tolist())

col1, col2, col3, col4 = st.columns(4)

with col1:
    mes_inicio_nome = st.selectbox("Mês Início", nomes_meses, index=0)
with col2:
    ano_inicio = st.selectbox("Ano Início", anos_disponiveis, index=0)
with col3:
    mes_fim_nome = st.selectbox("Mês Fim", nomes_meses, index=len(nomes_meses)-1)
with col4:
    ano_fim = st.selectbox("Ano Fim", anos_disponiveis, index=len(anos_disponiveis)-1)

# Adiciona uma linha divisória charmosa para separar os filtros dos gráficos
st.divider()

# ==============================================================================
# 4. Lógica de Filtragem e Geração dos Gráficos
# ==============================================================================
mes_inicio_num = list(meses_dict.keys())[nomes_meses.index(mes_inicio_nome)]
mes_fim_num = list(meses_dict.keys())[nomes_meses.index(mes_fim_nome)]

data_inicio = pd.to_datetime(f"{ano_inicio}-{mes_inicio_num:02d}-01")
data_fim = pd.to_datetime(f"{ano_fim}-{mes_fim_num:02d}-01")

# Regras de validação
if len(categorias_selecionadas) == 0:
    st.warning("⚠️ Por favor, selecione pelo menos uma discriminação para visualizar os gráficos.")
elif data_fim < data_inicio:
    st.error("⚠️ Atenção: O 'Período Fim' não pode ser anterior ao 'Período Início'. Ajuste as datas.")
else:
    # ---------------------------------------------------------
    # GRÁFICO 1: VALORES CORRENTES
    # ---------------------------------------------------------
    st.subheader("📈 Valores Correntes")
    
    # Filtra o DataFrame de valores correntes
    mask_corrente = (df_corrente['Discriminação'].isin(categorias_selecionadas)) & \
                    (df_corrente['Data'] >= data_inicio) & \
                    (df_corrente['Data'] <= data_fim)
    df_filtrado_corr = df_corrente[mask_corrente]
    
    fig_corr = px.line(
        df_filtrado_corr, 
        x='Data', y='Valor', color='Discriminação', markers=True,
        title='' # Deixamos o título em branco pois já usamos o st.subheader acima
    )
    
    fig_corr.update_xaxes(title="", tickformat="%m/%Y")
    fig_corr.update_yaxes(title="Valor (R$ Milhões)")
    fig_corr.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Data:</b> %{x|%m/%Y}<br><b>Valor:</b> R$ %{y:,.1f} Milhões')
    fig_corr.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # ---------------------------------------------------------
    # GRÁFICO 2: VALORES CONSTANTES
    # ---------------------------------------------------------
    # Colocamos um espaçamento visual entre os gráficos
    st.write("") 
    st.write("")
    st.subheader("📊 Valores Constantes (Dez/2025)")
    
    # Filtra o DataFrame de valores constantes
    mask_constante = (df_constante['Discriminação'].isin(categorias_selecionadas)) & \
                     (df_constante['Data'] >= data_inicio) & \
                     (df_constante['Data'] <= data_fim)
    df_filtrado_const = df_constante[mask_constante]
    
    fig_const = px.line(
        df_filtrado_const, 
        x='Data', y='Valor', color='Discriminação', markers=True,
        title=''
    )
    
    fig_const.update_xaxes(title="", tickformat="%m/%Y")
    fig_const.update_yaxes(title="Valor (R$ Milhões)")
    fig_const.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Data:</b> %{x|%m/%Y}<br><b>Valor:</b> R$ %{y:,.1f} Milhões')
    fig_const.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    st.plotly_chart(fig_const, use_container_width=True)