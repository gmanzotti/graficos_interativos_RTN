import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================================================================
# 1. Configuração da Página do Streamlit
# ==============================================================================
st.set_page_config(page_title="Painel Tesouro Nacional", layout="wide")

# ==============================================================================
# 2. Leitura e Limpeza dos Dados (Com Cache para velocidade)
# ==============================================================================
@st.cache_data
def carregar_dados():
    # Caminho relativo: o arquivo Excel deve estar na mesma pasta que este código no GitHub
    caminho_do_arquivo = 'rtn_mensal_corrente.xlsx'
    
    # 1. Leitura
    df_wide = pd.read_excel(caminho_do_arquivo)
    
    # 2. Melt (Transformando Largo em Longo)
    df_tidy = df_wide.melt(id_vars=['Discriminação'], var_name='Mes_Ano_Str', value_name='Valor_Bruto')
    
    # 3. Limpeza de números (Formato Brasileiro)
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

# Executa a função e guarda os dados
df_final = carregar_dados()

# ==============================================================================
# 3. Construção da Interface Visual (Filtros)
# ==============================================================================
st.title("📊 Painel de Execução Orçamentária Mensal - Valores Correntes")
st.markdown("Selecione as discriminações e o período desejado abaixo:")

# --- FILTRO 1: Categoria (Agora aceita várias opções!) ---
categorias = df_final['Discriminação'].unique()
categorias_selecionadas = st.multiselect(
    "Discriminação (selecione uma ou mais):", 
    options=categorias,
    default=[categorias[0]] # Começa com a primeira opção já selecionada
)

# --- FILTROS DE DATA (Meses e Anos separados) ---
meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
              7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
nomes_meses = list(meses_dict.values())
anos_disponiveis = sorted(df_final['Data'].dt.year.unique().tolist())

col1, col2, col3, col4 = st.columns(4)

with col1:
    mes_inicio_nome = st.selectbox("Mês Início", nomes_meses, index=0)
with col2:
    ano_inicio = st.selectbox("Ano Início", anos_disponiveis, index=0)
with col3:
    mes_fim_nome = st.selectbox("Mês Fim", nomes_meses, index=len(nomes_meses)-1)
with col4:
    ano_fim = st.selectbox("Ano Fim", anos_disponiveis, index=len(anos_disponiveis)-1)

# ==============================================================================
# 4. Lógica de Filtragem e Gráfico Interativo
# ==============================================================================
# Descobrindo o número do mês com base no nome escolhido
mes_inicio_num = list(meses_dict.keys())[nomes_meses.index(mes_inicio_nome)]
mes_fim_num = list(meses_dict.keys())[nomes_meses.index(mes_fim_nome)]

# Recriando as datas reais que o Pandas entende para fazer a matemática
data_inicio = pd.to_datetime(f"{ano_inicio}-{mes_inicio_num:02d}-01")
data_fim = pd.to_datetime(f"{ano_fim}-{mes_fim_num:02d}-01")

# REGRA DE OURO 1: A caixa de categorias não pode estar vazia
if len(categorias_selecionadas) == 0:
    st.warning("⚠️ Por favor, selecione pelo menos uma discriminação para visualizar o gráfico.")

# REGRA DE OURO 2: A data final não pode ser antes da data inicial
elif data_fim < data_inicio:
    st.error("⚠️ Atenção: O 'Período Fim' não pode ser anterior ao 'Período Início'. Ajuste as datas.")

else:
    # Se passou nas regras, filtramos os dados (usando .isin para a lista de categorias)
    mask = (df_final['Discriminação'].isin(categorias_selecionadas)) & \
           (df_final['Data'] >= data_inicio) & \
           (df_final['Data'] <= data_fim)
    
    df_filtrado = df_final[mask]
    
    # Criando o Gráfico (color='Discriminação' pinta cada linha de uma cor!)
    fig = px.line(
        df_filtrado, 
        x='Data', 
        y='Valor',
        color='Discriminação',
        markers=True,
        title='Evolução Temporal Comparativa'
    )
    
    # Formatando eixos e tooltips
    fig.update_xaxes(title="", tickformat="%m/%Y")
    fig.update_yaxes(title="Valor (R$ Milhões)")
    fig.update_traces(hovertemplate='<b>%{data.name}</b><br><b>Data:</b> %{x|%m/%Y}<br><b>Valor:</b> R$ %{y:,.1f} Milhões')
    
    # Jogando a legenda lá para baixo para dar mais espaço de tela para o gráfico
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=""))
    
    # Exibe o gráfico final no site
    st.plotly_chart(fig, use_container_width=True)