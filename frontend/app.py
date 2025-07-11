import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import re
import os
import requests
import json
import threading
import time as time_module

# Cache global para os dados
_cache_dados = {
    'dataframe': None,
    'timestamp': None,
    'lock': threading.Lock()
}

# Configurações de cache (5 minutos)
CACHE_TIMEOUT = 300  # segundos

# Função para definir faixa horária
def definir_faixa_horaria(hora):
    if 0 <= hora < 2: return '00-02h'
    elif 2 <= hora < 4: return '02-04h'
    elif 4 <= hora < 6: return '04-06h'
    elif 6 <= hora < 8: return '06-08h'
    elif 8 <= hora < 10: return '08-10h'
    elif 10 <= hora < 12: return '10-12h'
    elif 12 <= hora < 14: return '12-14h'
    elif 14 <= hora < 16: return '14-16h'
    elif 16 <= hora < 18: return '16-18h'
    elif 18 <= hora < 20: return '18-20h'
    elif 20 <= hora < 22: return '20-22h'
    else: return '22-24h'

# Função para carregar dados da API com cache
def carregar_dados_api():
    """
    Carrega dados da API CSV com cache inteligente de 5 minutos
    """
    global _cache_dados
    
    with _cache_dados['lock']:
        # Verificar se temos cache válido
        agora = time_module.time()
        if (_cache_dados['dataframe'] is not None and 
            _cache_dados['timestamp'] is not None and
            (agora - _cache_dados['timestamp']) < CACHE_TIMEOUT):
            
            print(f"📋 Usando dados em cache (válido por {CACHE_TIMEOUT - int(agora - _cache_dados['timestamp'])}s)")
            return _cache_dados['dataframe'].copy()
    
    # Cache expirado ou inexistente, buscar novos dados
    API_URL = 'http://10.24.46.31:8001/api/export-csv'
    JSON_PATH = 'dados.json'
    
    try:
        # Tentar carregar da API CSV primeiro
        print("🔄 Carregando dados da API CSV...")
        inicio = time_module.time()
        
        response = requests.get(API_URL, timeout=60)
        response.raise_for_status()
        
        # Carregar CSV diretamente do conteúdo da resposta
        from io import StringIO
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content)
        
        tempo_carregamento = time_module.time() - inicio
        
        # Converter colunas para os tipos corretos
        if not df.empty:
            # Converter cob para inteiro
            if 'cob' in df.columns:
                df['cob'] = pd.to_numeric(df['cob'], errors='coerce').astype('Int64')
            
            # Converter estado para inteiro
            if 'estado' in df.columns:
                df['estado'] = pd.to_numeric(df['estado'], errors='coerce').astype('Int64')
            
            # Converter duracao para numérico
            if 'duracao' in df.columns:
                df['duracao'] = pd.to_numeric(df['duracao'], errors='coerce')
            
            # Converter holdtime para numérico
            if 'holdtime' in df.columns:
                df['holdtime'] = pd.to_numeric(df['holdtime'], errors='coerce')
            
            # Converter fila para numérico se existir
            if 'fila' in df.columns:
                df['fila'] = pd.to_numeric(df['fila'], errors='coerce')
        
        # Atualizar cache
        with _cache_dados['lock']:
            _cache_dados['dataframe'] = df.copy()
            _cache_dados['timestamp'] = time_module.time()
        
        print(f"✅ Dados CSV carregados da API: {len(df)} registros em {tempo_carregamento:.2f}s")
        print(f"📊 Cache atualizado - válido por {CACHE_TIMEOUT}s")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao acessar API CSV: {e}")
        
        # Tentar usar cache expirado se disponível
        if _cache_dados['dataframe'] is not None:
            print("🔄 Usando cache expirado como fallback")
            return _cache_dados['dataframe'].copy()
        
        # Fallback para arquivo JSON
        if os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, 'r', encoding='utf-8') as f:
                    df = pd.read_json(f)
                print(f"📁 Dados carregados do arquivo JSON (fallback): {len(df)} registros")
                return df
            except Exception as e:
                print(f"❌ Erro ao carregar arquivo JSON: {e}")
        
        # Se tudo falhar, retorna DataFrame vazio
        print("⚠️ Retornando DataFrame vazio")
        return pd.DataFrame()
    
    except Exception as e:
        print(f"❌ Erro inesperado ao processar CSV: {e}")
        
        # Tentar usar cache expirado se disponível
        if _cache_dados['dataframe'] is not None:
            print("🔄 Usando cache expirado como fallback")
            return _cache_dados['dataframe'].copy()
        
        # Fallback para arquivo JSON
        if os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, 'r', encoding='utf-8') as f:
                    df = pd.read_json(f)
                print(f"📁 Dados carregados do arquivo JSON (fallback): {len(df)} registros")
                return df
            except Exception as e:
                print(f"❌ Erro ao carregar arquivo JSON: {e}")
        
        # Se tudo falhar, retorna DataFrame vazio
        print("⚠️ Retornando DataFrame vazio")
        return pd.DataFrame()

# Carregar dados
df = carregar_dados_api()

# Dicionário para mapear os valores de COB para os nomes das regiões
cob_legend = {
    21: '2ºCOB - Uberlândia',
    22: '2ºCOB - Uberaba',
    31: '3ºCOB - Juiz de Fora',
    32: '3ºCOB - Barbacena',
    4: '4ºCOB - Montes Claros',
    51: '5ºCOB - Governador Valadares',
    52: '5ºCOB - Ipatinga',
    61: '6ºCOB - Varginha'
}

# Preprocessamento para performance
if not df.empty and 'cob' in df.columns:
    # Remover valores nulos e obter valores únicos
    unique_cob_values = df['cob'].dropna().sort_values().unique()
    unique_destinos = [{'label': cob_legend.get(cob, f'COB {cob}'), 'value': cob} 
                      for cob in unique_cob_values if cob in cob_legend]
    print(f"🎯 COBs encontrados: {list(unique_cob_values)}")
    print(f"🎯 COBs mapeados: {[item['value'] for item in unique_destinos]}")
else:
    unique_destinos = []
    print("⚠️ Nenhum COB encontrado nos dados")

# Converter coluna 'data' para datetime se não estiver vazia
if not df.empty and 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'])
    # Criar coluna datetime combinando data e hora
    df['datetime'] = pd.to_datetime(df['data'].dt.strftime('%Y-%m-%d') + ' ' + df['hora'].astype(str))
    # Mapear COB para nomes
    df['cob_nome'] = df['cob'].map(cob_legend)
    
    # Criar coluna de faixa horária
    df['hora_int'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.hour
    df['faixa_horaria'] = df['hora_int'].apply(definir_faixa_horaria)
    
    # Mapear estado para status legível
    df['status'] = df['estado'].map({0: 'Não Atendido', 1: 'Atendido'})
    
    min_date = df['data'].min().date()
    max_date = df['data'].max().date()
    print(f"📅 Período dos dados: {min_date} até {max_date}")
    print(f"📊 Dados processados: {len(df)} registros com COB mapeados")
else:
    # Valores padrão caso não haja dados
    from datetime import date
    min_date = date.today()
    max_date = date.today()
    print("⚠️ Usando datas padrão (hoje)")

# App Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Painel de Monitoramento de Ligações - CBMMG'

# Logotipo
logo = html.Img(src='/assets/bombeiro.png', height='60px', style={'marginRight': '16px'})

# Filtros
filtros = dbc.Row([
    dbc.Col([logo], xs=12, md='auto', align='center', className='my-2'),
    dbc.Col([
        html.H2('Painel de Monitoramento Central Telefônica', className='titulo-topo mb-2', style={'marginBottom': 0}),
        html.H2('Detalhamento de Centrais', className='titulo-topo mb-2', style={'marginBottom': 0}),
        html.H5('Corpo de Bombeiros Militar de Minas Gerais', className='titulo-topo mb-2', style={'marginTop': 0})
    ], xs=12, md=6, align='center', className='my-2'),
], align='center', className='my-2')

filtros2 = dbc.Row([
    dbc.Col([
        html.Label('Data Inicial', style={'color': '#fff'}),
        dcc.DatePickerSingle(
            id='date-inicio',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            date=min_date,
            display_format='DD/MM/YYYY',
            style={'width': '100%'}
        ),
        dbc.Row([
            dbc.Col(dcc.Input(
                id='hh-inicio',
                type='number',
                min=0, max=23, step=1, inputMode='numeric', maxLength=2,
                value=0,
                style={'width': '100%', 'textAlign': 'center'}
            ), xs=5, md=4, className='my-2'),
            dbc.Col(html.Div(':', style={'textAlign': 'center', 'fontWeight': 'bold', 'fontSize': 22, 'color': '#fff'}), xs=2, md=1, className='my-2'),
            dbc.Col(dcc.Input(
                id='mm-inicio',
                type='number',
                min=0, max=59, step=1, inputMode='numeric', maxLength=2,
                value=0,
                style={'width': '100%', 'textAlign': 'center'}
            ), xs=5, md=4, className='my-2'),
        ], style={'marginTop': 4, 'marginBottom': 0, 'alignItems': 'center'}, justify='start'),
        html.Small('Ex: 08:30', style={'color': '#fff'})
    ], xs=12, md=2, className='my-2'),
    dbc.Col([
        html.Label('Data Final', style={'color': '#fff'}),
        dcc.DatePickerSingle(
            id='date-fim',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            date=max_date,
            display_format='DD/MM/YYYY',
            style={'width': '100%'}
        ),
        dbc.Row([
            dbc.Col(dcc.Input(
                id='hh-fim',
                type='number',
                min=0, max=23, step=1, inputMode='numeric', maxLength=2,
                value=23,
                style={'width': '100%', 'textAlign': 'center'}
            ), xs=5, md=4, className='my-2'),
            dbc.Col(html.Div(':', style={'textAlign': 'center', 'fontWeight': 'bold', 'fontSize': 22, 'color': '#fff'}), xs=2, md=1, className='my-2'),
            dbc.Col(dcc.Input(
                id='mm-fim',
                type='number',
                min=0, max=59, step=1, inputMode='numeric', maxLength=2,
                value=59,
                style={'width': '100%', 'textAlign': 'center'}
            ), xs=5, md=4, className='my-2'),
        ], style={'marginTop': 4, 'marginBottom': 0, 'alignItems': 'center'}, justify='start'),
        html.Small('Ex: 08:30', style={'color': '#fff'})
    ], xs=12, md=2, className='my-2'),
    dbc.Col([
        dcc.Dropdown(
            id='cob-dropdown',
            options=unique_destinos,
            value=[item['value'] for item in unique_destinos],
            multi=True,
            placeholder='Filtrar por Destino',
            style={'width': '100%', 'marginTop': 24}
        )
    ], xs=12, md=4, className='my-2'),
], className='mb-4')

# # Indicadores principais
# indicadores = dbc.Row([
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Total de Ligações', className='card-title'),
#         html.H2(id='total-ligacoes', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Atendidas', className='card-title'),
#         html.H2(id='total-atendidas', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Não Atendidas', className='card-title'),
#         html.H2(id='total-nao-atendidas', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
# ], className='mb-3')

# # Indicadores avançados
# indicadores_avancados = dbc.Row([
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Taxa de Atendimento', className='card-title'),
#         html.H2(id='taxa-atendimento', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Duração Média (s) - Atendidas', className='card-title'),
#         html.H2(id='duracao-media', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
#     dbc.Col(dbc.Card([dbc.CardBody([
#         html.H6('Total de Tempo Falado/dia', className='card-title'),
#         html.H2(id='total-segundos-dia', className='card-text')
#     ])]), xs=12, md=4, className='my-2'),
# ], className='mb-4')

# # Gráficos
# graficos = dbc.Row([
#     dbc.Col(dcc.Graph(id='grafico-linha-dia', className='my-2'), xs=12, md=6, className='my-2'),
#     dbc.Col(dcc.Graph(id='grafico-barra-faixa', className='my-2'), xs=12, md=6, className='my-2'),
# ], className='mb-4')

# graficos2 = dbc.Row([
#     dbc.Col(dcc.Graph(id='heatmap-hora-dia', className='my-2'), xs=12, md=6, className='my-2'),
#     dbc.Col(dcc.Graph(id='grafico-comparativo-tipo-dia', className='my-2'), xs=12, md=6, className='my-2'),
# ], className='mb-4')

# Indicadores principais com status da API
indicadores = dbc.Row([
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Total de Ligações', className='card-title'),
        html.H2(id='total-ligacoes', className='card-text')
    ])]), xs=12, md=3, className='my-2'),
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Atendidas', className='card-title'),
        html.H2(id='total-atendidas', className='card-text')
    ])]), xs=12, md=3, className='my-2'),
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Não Atendidas', className='card-title'),
        html.H2(id='total-nao-atendidas', className='card-text')
    ])]), xs=12, md=3, className='my-2'),
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Status dos Dados', className='card-title'),
        html.Div(id='status-api', className='card-text')
    ])]), xs=12, md=3, className='my-2'),
], className='mb-3')

# Indicadores avançados
indicadores_avancados = dbc.Row([
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Taxa de Atendimento', className='card-title'),
        html.H2(id='taxa-atendimento', className='card-text')
    ])]), xs=12, md=4, className='my-2'),
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Duração Média - Atendidas', className='card-title'),
        html.H2(id='duracao-media', className='card-text')
    ])]), xs=12, md=4, className='my-2'),
    dbc.Col(dbc.Card([dbc.CardBody([
        html.H6('Tempo Médio de Espera', className='card-title'),
        html.H2(id='tempo-espera-medio', className='card-text')
    ])]), xs=12, md=4, className='my-2'),
], className='mb-4')

# Indicadores por COB para comparação
indicadores_por_cob = html.Div([
    html.H4('Indicadores por Região (COB)', style={'color': '#fff', 'marginBottom': '20px', 'textAlign': 'center'}),
    html.Div(id='indicadores-cob-container')
], className='mb-4')

# Gráficos
graficos = dbc.Row([
    dbc.Col([
        dbc.Row([
            dbc.Col([
                dbc.Label("Mostrar Legenda:", style={'color': '#fff', 'marginRight': '10px'}),
                dbc.Switch(
                    id="toggle-legenda",
                    value=True,
                    style={'transform': 'scale(1.2)'}
                )
            ], width='auto', className='d-flex align-items-center mb-2')
        ], justify='end'),
        dcc.Graph(id='grafico-chamadas-data-cob', className='my-2')
    ], xs=12, md=12, className='my-2'),
], className='mb-4')

# Gráficos adicionais
graficos2 = dbc.Row([
    dbc.Col(dcc.Graph(id='grafico-atendidas-nao-atendidas', className='my-2'), xs=12, md=6, className='my-2'),
    dbc.Col(dcc.Graph(id='grafico-faixa-horaria', className='my-2'), xs=12, md=6, className='my-2'),
], className='mb-4')

# Gráfico adicional - linha
graficos3 = dbc.Row([
    dbc.Col(dcc.Graph(id='grafico-linha-faixa-horaria', className='my-2'), xs=12, md=12, className='my-2'),
], className='mb-4')

# Gráficos adicionais - pizza e indicador
graficos4 = dbc.Row([
    dbc.Col(dcc.Graph(id='grafico-pizza-atendidas', className='my-2'), xs=12, md=6, className='my-2'),
    dbc.Col(dcc.Graph(id='grafico-top-atendente', className='my-2'), xs=12, md=6, className='my-2'),
], className='mb-4')

# Gráficos adicionais - Top COBs
graficos5 = dbc.Row([
    dbc.Col(dcc.Graph(id='grafico-top-cob-atendidas', className='my-2'), xs=12, md=6, className='my-2'),
    dbc.Col(dcc.Graph(id='grafico-top-cob-nao-atendidas', className='my-2'), xs=12, md=6, className='my-2'),
], className='mb-4')

# Layout
app.layout = dbc.Container([
        filtros,
        filtros2,
        indicadores,
        indicadores_avancados,
        indicadores_por_cob,
        graficos,
        graficos2,
        graficos3,
        graficos4,
        graficos5,
        html.Footer([
            html.Hr(),
        html.P('Desenvolvido para o Corpo de Bombeiros Militar de Minas Gerais', style={'textAlign': 'center', 'color': '#fff'})
    ], className='footer')
], fluid=True, id='main-container')

# Função para obter status dos dados
def obter_status_dados():
    """
    Retorna o status atual dos dados (API, Cache, JSON local)
    """
    global _cache_dados
    
    if _cache_dados['timestamp'] is None:
        return html.Span([
            html.I(className="fas fa-circle", style={'color': 'gray', 'marginRight': '5px'}),
            "Sem dados"
        ], style={'fontSize': '14px'})
    
    agora = time_module.time()
    tempo_desde_update = agora - _cache_dados['timestamp']
    
    if tempo_desde_update < CACHE_TIMEOUT:
        # Cache válido
        minutos_restantes = (CACHE_TIMEOUT - tempo_desde_update) / 60
        return html.Span([
            html.I(className="fas fa-circle", style={'color': 'green', 'marginRight': '5px'}),
            f"Dados atuais",
            html.Br(),
            html.Small(f"Próxima atualização em {minutos_restantes:.1f}min", style={'color': 'gray'})
        ], style={'fontSize': '14px'})
    else:
        # Cache expirado
        return html.Span([
            html.I(className="fas fa-circle", style={'color': 'orange', 'marginRight': '5px'}),
            "Cache expirado",
            html.Br(),
            html.Small("Clique para atualizar", style={'color': 'gray'})
        ], style={'fontSize': '14px'})

# Função para converter segundos em formato legível
def segundos_legiveis(segundos):
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos}s"
    minutos = segundos // 60
    s = segundos % 60
    if minutos < 60:
        return f"{minutos}min {s}s" if s else f"{minutos}min"
    horas = minutos // 60
    m = minutos % 60
    return f"{horas}h {m}min {s}s" if s else (f"{horas}h {m}min" if m else f"{horas}h")

# Callback
@app.callback(
    [
        Output('total-ligacoes', 'children'),
        Output('total-atendidas', 'children'),
        Output('total-nao-atendidas', 'children'),
        Output('status-api', 'children'),
        Output('taxa-atendimento', 'children'),
        Output('duracao-media', 'children'),
        Output('tempo-espera-medio', 'children'),
        Output('indicadores-cob-container', 'children'),
        Output('grafico-chamadas-data-cob', 'figure'),
        Output('grafico-atendidas-nao-atendidas', 'figure'),
        Output('grafico-faixa-horaria', 'figure'),
        Output('grafico-linha-faixa-horaria', 'figure'),
        Output('grafico-pizza-atendidas', 'figure'),
        Output('grafico-top-atendente', 'figure'),
        Output('grafico-top-cob-atendidas', 'figure'),
        Output('grafico-top-cob-nao-atendidas', 'figure'),
    ],
    [
        Input('date-inicio', 'date'),
        Input('hh-inicio', 'value'),
        Input('mm-inicio', 'value'),
        Input('date-fim', 'date'),
        Input('hh-fim', 'value'),
        Input('mm-fim', 'value'),
        Input('cob-dropdown', 'value'),
        Input('toggle-legenda', 'value'),
    ]
)
def atualizar_dashboard(date_ini, hh_ini, mm_ini, date_fim, hh_fim, mm_fim, destinos, mostrar_legenda):
    # Usar dados em cache (não recarregar a cada interação)
    df_atual = carregar_dados_api()
    
    # Obter status dos dados
    status_texto = obter_status_dados()
    
    if df_atual is None or df_atual.empty:
        print("Dados não encontrados ou vazios")
        return [
            0, 0, 0, status_texto, "0%", "0 min", "0 min", [], 
            {}, {}, {}, {}, {}, {}, {}, {}
        ]
    
    # Processar dados se não estiver vazio
    if not df_atual.empty and 'data' in df_atual.columns:
        # Converter coluna 'data' para datetime (apenas se não já processado)
        if df_atual['data'].dtype == 'object':
            df_atual['data'] = pd.to_datetime(df_atual['data'])
        
        # Criar colunas derivadas apenas se não existirem
        if 'datetime' not in df_atual.columns:
            df_atual['datetime'] = pd.to_datetime(df_atual['data'].dt.strftime('%Y-%m-%d') + ' ' + df_atual['hora'].astype(str))
        
        if 'cob_nome' not in df_atual.columns:
            df_atual['cob_nome'] = df_atual['cob'].map(cob_legend)
        
        if 'hora_int' not in df_atual.columns:
            df_atual['hora_int'] = pd.to_datetime(df_atual['hora'], format='%H:%M:%S').dt.hour
        
        if 'faixa_horaria' not in df_atual.columns:
            df_atual['faixa_horaria'] = df_atual['hora_int'].apply(definir_faixa_horaria)
        
        if 'status' not in df_atual.columns:
            df_atual['status'] = df_atual['estado'].map({0: 'Não Atendido', 1: 'Atendido'})
    
    # Validação dos campos de hora/minuto
    try:
        hh_ini = int(hh_ini)
        if not (0 <= hh_ini <= 23):
            hh_ini = 0
    except:
        hh_ini = 0
    try:
        mm_ini = int(mm_ini)
        if not (0 <= mm_ini <= 59):
            mm_ini = 0
    except:
        mm_ini = 0
    try:
        hh_fim = int(hh_fim)
        if not (0 <= hh_fim <= 23):
            hh_fim = 23
    except:
        hh_fim = 23
    try:
        mm_fim = int(mm_fim)
        if not (0 <= mm_fim <= 59):
            mm_fim = 59
    except:
        mm_fim = 59
    hora_ini = f'{hh_ini:02d}:{mm_ini:02d}'
    hora_fim = f'{hh_fim:02d}:{mm_fim:02d}'
    # Combinar data e hora
    try:
        datahora_ini = datetime.strptime(f"{date_ini} {hora_ini}", "%Y-%m-%d %H:%M")
    except:
        datahora_ini = df_atual['datetime'].min() if not df_atual.empty else datetime.now()
    try:
        datahora_fim = datetime.strptime(f"{date_fim} {hora_fim}", "%Y-%m-%d %H:%M")
    except:
        datahora_fim = df_atual['datetime'].max() if not df_atual.empty else datetime.now()

    # Filtrar dados
    if not df_atual.empty:
        dff = df_atual[(df_atual['datetime'] >= datahora_ini) & (df_atual['datetime'] <= datahora_fim)]
        if destinos:
            dff = dff[dff['cob'].isin(destinos)]
    else:
        dff = pd.DataFrame()

    # Calcular indicadores
    if not dff.empty:
        # Indicadores principais
        total_ligacoes = len(dff)
        total_atendidas = len(dff[dff['estado'] == 1])
        total_nao_atendidas = len(dff[dff['estado'] == 0])
        
        # Indicadores avançados
        taxa_atendimento = (total_atendidas / total_ligacoes * 100) if total_ligacoes > 0 else 0
        
        # Duração média apenas para ligações atendidas
        ligacoes_atendidas = dff[dff['estado'] == 1]
        duracao_media = ligacoes_atendidas['duracao'].mean() if not ligacoes_atendidas.empty else 0
        
        # Tempo médio de espera para todas as ligações
        tempo_espera_medio = dff['holdtime'].mean()
        
        # Formatação dos valores
        total_ligacoes_str = f"{total_ligacoes:,}"
        total_atendidas_str = f"{total_atendidas:,}"
        total_nao_atendidas_str = f"{total_nao_atendidas:,}"
        taxa_atendimento_str = f"{taxa_atendimento:.1f}%"
        duracao_media_str = segundos_legiveis(duracao_media)
        tempo_espera_medio_str = segundos_legiveis(tempo_espera_medio)
        
        # Calcular indicadores por COB
        indicadores_cob_cards = []
        cobs_no_periodo = dff['cob_nome'].unique()
        
        for cob in sorted(cobs_no_periodo):
            dados_cob = dff[dff['cob_nome'] == cob]
            
            if not dados_cob.empty:
                # Calcular métricas para este COB
                total_cob = len(dados_cob)
                atendidas_cob = len(dados_cob[dados_cob['estado'] == 1])
                nao_atendidas_cob = len(dados_cob[dados_cob['estado'] == 0])
                taxa_cob = (atendidas_cob / total_cob * 100) if total_cob > 0 else 0
                
                # Duração média para ligações atendidas
                atendidas_dados = dados_cob[dados_cob['estado'] == 1]
                duracao_cob = atendidas_dados['duracao'].mean() if not atendidas_dados.empty else 0
                
                # Tempo médio de espera
                espera_cob = dados_cob['holdtime'].mean()
                
                # Card para este COB
                card_cob = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5(cob, className='mb-0', style={'color': '#162447'})),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Small('Total', className='text-muted'),
                                    html.H6(f"{total_cob}", style={'color': '#162447'})
                                ], xs=4),
                                dbc.Col([
                                    html.Small('Atendidas', className='text-muted'),
                                    html.H6(f"{atendidas_cob}", style={'color': '#00CC96'})
                                ], xs=4),
                                dbc.Col([
                                    html.Small('Não Atend.', className='text-muted'),
                                    html.H6(f"{nao_atendidas_cob}", style={'color': '#FF6B6B'})
                                ], xs=4),
                            ]),
                            html.Hr(style={'margin': '10px 0'}),
                            dbc.Row([
                                dbc.Col([
                                    html.Small('Taxa Atend.', className='text-muted'),
                                    html.H6(f"{taxa_cob:.1f}%", style={'color': '#a84105'})
                                ], xs=4),
                                dbc.Col([
                                    html.Small('Dur. Média', className='text-muted'),
                                    html.H6(segundos_legiveis(duracao_cob), style={'color': '#636EFA'})
                                ], xs=4),
                                dbc.Col([
                                    html.Small('Esp. Média', className='text-muted'),
                                    html.H6(segundos_legiveis(espera_cob), style={'color': '#AB63FA'})
                                ], xs=4),
                            ])
                        ])
                    ], style={'height': '100%'})
                ], xs=12, md=6, lg=4, className='mb-3')
                
                indicadores_cob_cards.append(card_cob)
        
        # Criar layout dos cards por COB
        if indicadores_cob_cards:
            indicadores_cob_layout = dbc.Row(indicadores_cob_cards)
        else:
            indicadores_cob_layout = html.Div("Nenhum dado disponível para o período selecionado", 
                                            style={'textAlign': 'center', 'color': '#fff', 'padding': '20px'})
    else:
        # Valores padrão quando não há dados
        total_ligacoes_str = "0"
        total_atendidas_str = "0"
        total_nao_atendidas_str = "0"
        taxa_atendimento_str = "0.0%"
        duracao_media_str = "0s"
        tempo_espera_medio_str = "0s"
        indicadores_cob_layout = html.Div("Nenhum dado disponível", 
                                        style={'textAlign': 'center', 'color': '#fff', 'padding': '20px'})

    # Função para gráfico vazio
    def grafico_vazio(titulo):
        return {
            'data': [],
            'layout': {
                'xaxis': {'visible': False},
                'yaxis': {'visible': False},
                'annotations': [{
                    'text': 'Sem dados para exibir',
                    'xref': 'paper', 'yref': 'paper',
                    'x': 0.5, 'y': 0.5,
                    'showarrow': False,
                    'font': {'size': 18, 'color': '#a84105'}
                }],
                'plot_bgcolor': '#fff',
                'paper_bgcolor': '#fff',
                'title': {'text': titulo, 'font': {'color': '#162447'}},
                'font': {'color': '#162447'}
            }
        }

    # Gráfico de chamadas por data/hora e COB
    if not dff.empty:
        # Agrupar por data e COB para contar chamadas (apenas por dia, não por hora)
        chamadas_data_cob = dff.groupby([dff['data'].dt.date, 'cob_nome']).size().reset_index(name='quantidade_chamadas')
        chamadas_data_cob.rename(columns={chamadas_data_cob.columns[0]: 'data'}, inplace=True)
        
        if not chamadas_data_cob.empty:
            fig_chamadas = px.bar(
                chamadas_data_cob, 
                x='data', 
                y='quantidade_chamadas',
                color='cob_nome',
                title='Quantidade de Chamadas por Data e COB',
                template='plotly',
                barmode='stack'  # Barras empilhadas
            )
            
            # Customizar aparência
            fig_chamadas.update_traces(
                marker_line_width=1,
                marker_line_color='rgba(255,255,255,0.5)'
            )
            
            fig_chamadas.update_layout(
                xaxis_title='Data',
                yaxis_title='Quantidade de Chamadas',
                font_color='#162447',
                title_font_color='#a84105',
                title_font_size=16,
                margin=dict(l=0, r=0, t=40, b=0),
                legend_title_text='COB',
                hovermode='closest',  # Hover apenas no elemento específico
                bargap=0.2,  # Espaço entre barras
                showlegend=mostrar_legenda  # Controla a visibilidade da legenda
            )
        else:
            fig_chamadas = grafico_vazio('Quantidade de Chamadas por Data e COB')
    else:
        fig_chamadas = grafico_vazio('Quantidade de Chamadas por Data e COB')

    # Gráfico de atendidas/não atendidas por COB
    if not dff.empty:
        atendidas_nao_atendidas = dff.groupby(['cob_nome', 'status']).size().reset_index(name='quantidade')
        
        if not atendidas_nao_atendidas.empty:
            fig_atendidas = px.bar(
                atendidas_nao_atendidas, 
                x='cob_nome', 
                y='quantidade',
                color='status',
                title='Atendidas e Não Atendidas por Região (COB)',
                labels={'quantidade': 'Número de Chamadas', 'cob_nome': 'Região (COB)', 'status': 'Atendimento'},
                template='plotly',
                color_discrete_map={'Atendido': "#09F028", 'Não Atendido': "#C90000"}
            )
            
            fig_atendidas.update_layout(
                legend_title_text='Atendimento',
                font_color='#162447',
                title_font_color='#a84105',
                title_font_size=14,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=mostrar_legenda,
                xaxis_tickangle=-45
            )
        else:
            fig_atendidas = grafico_vazio('Atendidas e Não Atendidas por Região (COB)')
    else:
        fig_atendidas = grafico_vazio('Atendidas e Não Atendidas por Região (COB)')

    # Gráfico de chamadas por faixa horária
    if not dff.empty:
        chamadas_por_faixa_horaria = dff.groupby(['faixa_horaria', 'cob_nome']).size().reset_index(name='quantidade')
        
        if not chamadas_por_faixa_horaria.empty:
            fig_faixa = px.bar(
                chamadas_por_faixa_horaria, 
                x='faixa_horaria', 
                y='quantidade', 
                color='cob_nome',
                title='Quantidade de Chamadas por Faixa Horária e Região (COB)',
                labels={'quantidade': 'Número de Chamadas', 'faixa_horaria': 'Faixa Horária', 'cob_nome': 'Região (COB)'},
                template='plotly',
                color_discrete_sequence=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880']
            )
            
            fig_faixa.update_layout(
                legend_title_text='Região (COB)',
                font_color='#162447',
                title_font_color='#a84105',
                title_font_size=14,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=mostrar_legenda,
                xaxis_tickangle=-45
            )
        else:
            fig_faixa = grafico_vazio('Quantidade de Chamadas por Faixa Horária e Região (COB)')
    else:
        fig_faixa = grafico_vazio('Quantidade de Chamadas por Faixa Horária e Região (COB)')

    # Gráfico de linha - chamadas por faixa horária
    if not dff.empty:
        chamadas_por_faixa_cob = dff.groupby(['faixa_horaria', 'cob_nome']).size().reset_index(name='quantidade')
        
        if not chamadas_por_faixa_cob.empty:
            fig_linha_faixa = px.line(
                chamadas_por_faixa_cob, 
                x='faixa_horaria', 
                y='quantidade', 
                color='cob_nome',
                title='Quantidade de Chamadas por Faixa Horária e Região (COB) - Linha',
                labels={'faixa_horaria': 'Faixa Horária', 'quantidade': 'Número de Chamadas', 'cob_nome': 'Região (COB)'},
                template='plotly',
                color_discrete_sequence=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880'],
                markers=True
            )
            
            fig_linha_faixa.update_layout(
                legend_title_text='Região (COB)',
                font_color='#162447',
                title_font_color='#a84105',
                title_font_size=16,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=mostrar_legenda,
                xaxis_tickangle=-45
            )
        else:
            fig_linha_faixa = grafico_vazio('Quantidade de Chamadas por Faixa Horária e Região (COB) - Linha')
    else:
        fig_linha_faixa = grafico_vazio('Quantidade de Chamadas por Faixa Horária e Região (COB) - Linha')

    # Gráfico pizza - distribuição de chamadas atendidas por COB
    if not dff.empty:
        chamadas_atendidas = dff[dff['estado'] == 1]
        
        if not chamadas_atendidas.empty:
            distribuicao_atendidas = chamadas_atendidas.groupby('cob_nome').size().reset_index(name='quantidade')
            
            fig_pizza = go.Figure(data=[go.Pie(
                labels=distribuicao_atendidas['cob_nome'],
                values=distribuicao_atendidas['quantidade'],
                hole=0.4,
                textinfo='label+percent',
                textposition='outside',
                marker=dict(colors=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880'])
            )])
            
            fig_pizza.update_layout(
                title='Distribuição de Chamadas Atendidas por Região (COB)',
                title_font_color='#a84105',
                title_font_size=16,
                font_color='#162447',
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=mostrar_legenda,
                height=350
            )
        else:
            fig_pizza = grafico_vazio('Distribuição de Chamadas Atendidas por Região (COB)')
    else:
        fig_pizza = grafico_vazio('Distribuição de Chamadas Atendidas por Região (COB)')

    # Gráfico indicador - top atendente
    if not dff.empty:
        chamadas_atendidas = dff[dff['estado'] == 1]
        
        if not chamadas_atendidas.empty:
            atendimentos_por_atendente = chamadas_atendidas.groupby('teleatendente').size().reset_index(name='atendimentos')
            
            if not atendimentos_por_atendente.empty:
                top_atendente = atendimentos_por_atendente.loc[atendimentos_por_atendente['atendimentos'].idxmax()]
                media_atendimentos = atendimentos_por_atendente['atendimentos'].mean()
                delta = top_atendente['atendimentos'] - media_atendimentos
                
                # Buscar o COB do top atendente
                cob_top_atendente = chamadas_atendidas[chamadas_atendidas['teleatendente'] == top_atendente['teleatendente']]['cob_nome'].iloc[0]
                
                fig_indicador = go.Figure(go.Indicator(
                    mode = "number+delta",
                    value = top_atendente['atendimentos'],
                    delta = {"reference": media_atendimentos, "valueformat": "+.0f"},
                    title = {"text": f"Top Atendente<br><span style='font-size:0.8em;color:gray'>{top_atendente['teleatendente']}</span><br><span style='font-size:0.7em;color:#a84105'>{cob_top_atendente}</span>"},
                    number = {"font": {"size": 60}},
                    domain = {'x': [0, 1], 'y': [0, 1]}
                ))
                
                fig_indicador.update_layout(
                    height=350,
                    margin=dict(l=0, r=0, t=40, b=0),
                    font_color='#162447'
                )
            else:
                fig_indicador = grafico_vazio('Top Atendente')
        else:
            fig_indicador = grafico_vazio('Top Atendente')
    else:
        fig_indicador = grafico_vazio('Top Atendente')

    # Gráfico 7 - Top COB por número de ligações atendidas
    if not dff.empty:
        chamadas_atendidas = dff[dff['estado'] == 1]
        
        if not chamadas_atendidas.empty:
            atendidas_por_cob = chamadas_atendidas.groupby('cob_nome').size().reset_index(name='Quantidade')
            atendidas_por_cob.sort_values(by='Quantidade', ascending=False, inplace=True)
            
            if not atendidas_por_cob.empty:
                media_atendidas_por_cob = atendidas_por_cob['Quantidade'].mean()
                
                fig_top_cob_atendidas = go.Figure(go.Indicator(
                    mode='number+delta',
                    title={
                        "text": f"<span>{atendidas_por_cob['cob_nome'].iloc[0]} - Top COB</span><br>"
                        f"<span style='font-size:90%'>Região com mais ligações atendidas</span><br>"
                        f"<span style='font-size:90%'>Ligações atendidas - em relação à média</span>"
                    },
                    value=atendidas_por_cob['Quantidade'].iloc[0],
                    number={'suffix': " ligações", 'font': {'size': 50}},
                    delta={'relative': True, 'valueformat': '.1%', 'reference': media_atendidas_por_cob, 'position': "bottom", 'font': {'size': 30}}
                ))
                
                fig_top_cob_atendidas.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=350,
                    template='plotly',
                    autosize=True,
                    font_color='#162447'
                )
            else:
                fig_top_cob_atendidas = grafico_vazio('Top COB - Atendidas')
        else:
            fig_top_cob_atendidas = grafico_vazio('Top COB - Atendidas')
    else:
        fig_top_cob_atendidas = grafico_vazio('Top COB - Atendidas')

    # Gráfico 8 - Top COB por número de ligações não atendidas
    if not dff.empty:
        chamadas_nao_atendidas = dff[dff['estado'] == 0]
        
        if not chamadas_nao_atendidas.empty:
            nao_atendidas_por_cob = chamadas_nao_atendidas.groupby('cob_nome').size().reset_index(name='Quantidade')
            nao_atendidas_por_cob.sort_values(by='Quantidade', ascending=False, inplace=True)
            
            if not nao_atendidas_por_cob.empty:
                media_nao_atendidas_por_cob = nao_atendidas_por_cob['Quantidade'].mean()
                
                fig_top_cob_nao_atendidas = go.Figure(go.Indicator(
                    mode='number+delta',
                    title={
                        "text": f"<span>{nao_atendidas_por_cob['cob_nome'].iloc[0]} - Top COB</span><br>"
                        f"<span style='font-size:90%'>Região com mais ligações não atendidas</span><br>"
                        f"<span style='font-size:90%'>Ligações não atendidas - em relação à média</span>"
                    },
                    value=nao_atendidas_por_cob['Quantidade'].iloc[0],
                    number={'suffix': " ligações", 'font': {'size': 50}},
                    delta={'relative': True, 'valueformat': '.1%', 'reference': media_nao_atendidas_por_cob, 'position': "bottom", 'font': {'size': 30}}
                ))
                
                fig_top_cob_nao_atendidas.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=350,
                    template='plotly',
                    autosize=True,
                    font_color='#162447'
                )
            else:
                fig_top_cob_nao_atendidas = grafico_vazio('Top COB - Não Atendidas')
        else:
            fig_top_cob_nao_atendidas = grafico_vazio('Top COB - Não Atendidas')
    else:
        fig_top_cob_nao_atendidas = grafico_vazio('Top COB - Não Atendidas')

    return (
        total_ligacoes_str, total_atendidas_str, total_nao_atendidas_str,
        status_texto,
        taxa_atendimento_str, duracao_media_str, tempo_espera_medio_str,
        indicadores_cob_layout,
        fig_chamadas, fig_atendidas, fig_faixa, fig_linha_faixa, 
        fig_pizza, fig_indicador, fig_top_cob_atendidas, fig_top_cob_nao_atendidas
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)