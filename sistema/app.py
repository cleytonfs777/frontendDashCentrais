import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import re
import os
import threading
import sqlite3
from contextlib import contextmanager
from threading import Thread


# Configurações do banco de dados e arquivo CSV
DB_PATH = 'data/dados_chamadas.db'
CSV_PATH = 'data/geral_df.csv'

# Cache global para os dados
_cache_dados = {
    'dataframe': None,
    'lock': threading.Lock()
}

# Flag de carga inicial
INITIAL_LOAD_COMPLETE = False

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

# Funções do banco de dados
@contextmanager
def get_db_connection():
    """Context manager para conexões com o banco de dados"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Inicializa o banco de dados com as tabelas necessárias"""
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chamadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                duracao REAL,
                fila TEXT,
                teleatendente TEXT,
                estado INTEGER,
                cob INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data, hora, duracao, fila, teleatendente, estado, cob)
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_data ON chamadas(data)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_cob ON chamadas(cob)
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                url TEXT NOT NULL,
                records_added INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        ''')
        
        conn.commit()
        print("✅ Banco de dados inicializado")


def salvar_dados_banco(df, origem="csv"):
    """Salva dados no banco, evitando duplicatas"""
    if df.empty:
        print("⚠️ DataFrame vazio, nada para salvar")
        return 0
    
    records_added = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO chamadas 
                    (data, hora, duracao, fila, teleatendente, estado, cob)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['data'], row['hora'], row.get('duracao', 0), row.get('fila', ''),
                    row.get('teleatendente', ''), row.get('estado', 0), row.get('cob', 0)
                ))
                
                if cursor.rowcount > 0:
                    records_added += 1
                    
            except Exception as e:
                print(f"❌ Erro ao inserir registro: {e}")
                continue
        
        # Log da carga
        # cursor.execute('''
        #     INSERT INTO sync_log (arquivo, records_total, records_added, status, details)
        #     VALUES (?, ?, ?, ?, ?)
        # ''', (origem, len(df), records_added, "success", f"Processados {len(df)} registros"))
        
        conn.commit()
    
    print(f"💾 Salvos {records_added} novos registros no banco (de {len(df)} processados)")
    return records_added

def carregar_dados_banco():
    """Carrega todos os dados do banco para um DataFrame"""
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query('''
                SELECT data, hora, duracao, fila, teleatendente, estado, cob
                FROM chamadas 
                ORDER BY data DESC, hora DESC
            ''', conn)
        
        if not df.empty:
            # Converter tipos de forma mais robusta
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            
            # Remover linhas com data inválida
            df = df.dropna(subset=['data'])
            
            df['estado'] = df['estado'].astype('Int64')
            df['cob'] = df['cob'].astype('Int64')
            df['duracao'] = pd.to_numeric(df['duracao'], errors='coerce').fillna(0)
            
            print(f"📊 Carregados {len(df)} registros do banco")
        
        return df
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados do banco: {e}")
        return pd.DataFrame()


def carregar_csv_para_banco():
    """Carrega o CSV completo e salva no banco (executa apenas uma vez)"""
    global INITIAL_LOAD_COMPLETE, _cache_dados
    
    print("🔄 Iniciando carga do CSV para o banco...")
    
    try:
        if not os.path.exists(CSV_PATH):
            print(f"❌ Arquivo {CSV_PATH} não encontrado")
            return
        
        # Verificar se já existe dados no banco
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chamadas")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"✅ Banco já possui {count} registros, pulando carga do CSV")
                INITIAL_LOAD_COMPLETE = True
                
                # Carregar dados do banco para o cache
                df = carregar_dados_banco()
                if not df.empty:
                    _cache_dados['dataframe'] = df.copy()
                return
        
        # Ler o CSV
        print(f"📖 Lendo arquivo CSV: {CSV_PATH}")
        df = pd.read_csv(CSV_PATH)
        
        if df.empty:
            print("⚠️ CSV está vazio")
            return
        
        # Validar colunas necessárias
        colunas_necessarias = ['data', 'hora', 'duracao', 'fila', 'teleatendente', 'estado', 'cob']
        colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
        
        if colunas_faltantes:
            print(f"❌ Colunas faltantes no CSV: {colunas_faltantes}")
            return
        
        # Limpar e preparar dados
        print("🧹 Limpando e preparando dados...")
        
        # Remover linhas com valores nulos em colunas críticas
        df = df.dropna(subset=['data', 'hora'])
        
        # Converter tipos de dados
        df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.dropna(subset=['data'])  # Remover datas inválidas
        
        # Garantir que hora está no formato string
        df['hora'] = df['hora'].astype(str)
        
        # Converter duracao para float
        df['duracao'] = pd.to_numeric(df['duracao'], errors='coerce').fillna(0)
        
        # Converter estado e cob para inteiro
        df['estado'] = pd.to_numeric(df['estado'], errors='coerce').fillna(0).astype(int)
        df['cob'] = pd.to_numeric(df['cob'], errors='coerce').fillna(0).astype(int)
        
        # Garantir que fila e teleatendente são strings
        df['fila'] = df['fila'].astype(str).fillna('')
        df['teleatendente'] = df['teleatendente'].astype(str).fillna('')
        
        print(f"📝 Dados preparados: {len(df)} registros válidos")
        
        # Salvar no banco
        records_added = salvar_dados_banco(df, CSV_PATH)
        
        print(f"✅ Carga do CSV concluída: {records_added} registros adicionados ao banco")
        
        INITIAL_LOAD_COMPLETE = True
        
        # Atualizar cache
        _cache_dados['dataframe'] = df.copy()
        
    except Exception as e:
        print(f"❌ Erro ao carregar CSV para o banco: {e}")
        import traceback
        traceback.print_exc()
    

def carregar_dados():
    """Função principal para carregar dados (do cache ou do banco)"""
    global _cache_dados
    
    with _cache_dados['lock']:
        # Se já temos dados em cache, usar
        if _cache_dados['dataframe'] is not None:
            print("✅ Usando dados em cache")
            return _cache_dados['dataframe'].copy()
        
        # Carregar do banco
        print("📊 Carregando dados do banco...")
        df = carregar_dados_banco()
        
        if not df.empty:
            _cache_dados['dataframe'] = df.copy()
            return df
        
        return pd.DataFrame()

# Inicialização do banco de dados
print("🚀 Inicializando aplicação...")
init_database()

# Carregar CSV para o banco (sincronamente) na inicialização para garantir que
# as datas mínimas/máximas e opções dos filtros sejam definidas corretamente.
carregar_csv_para_banco()

# Carregar dados iniciais
df = carregar_dados()

# Dicionário para mapear os valores de COB para os nomes das regiões
cob_legend = {
    11: '1ºCOB - Divinópolis',
    21: '2ºCOB - Uberlândia',
    22: '2ºCOB - Uberaba',
    31: '3ºCOB - Juiz de Fora',
    32: '3ºCOB - Barbacena',
    4: '4ºCOB - Montes Claros',
    51: '5ºCOB - Governador Valadares',
    52: '5ºCOB - Ipatinga',
    61: '6ºCOB - Varginha'
}

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
        html.H2('Dashboard - Centrais Telefônicas CBMMG', className='titulo-topo mb-2', style={'marginBottom': 0}),
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
            options=[],  # Será populado dinamicamente
            value=[],    # Será populado dinamicamente
            multi=True,
            placeholder='Filtrar por Destino',
            style={'width': '100%', 'marginTop': 24}
        )
    ], xs=12, md=4, className='my-2'),
], className='mb-4')

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
        html.H6('Total de Tempo Falado', className='card-title'),
        html.H2(id='total-tempo-falado', className='card-text')
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
    """Retorna o status atual dos dados do banco"""
    global INITIAL_LOAD_COMPLETE
    
    if not INITIAL_LOAD_COMPLETE:
        return html.Span([
            html.I(className="fas fa-clock", style={'color': '#ffc107', 'marginRight': '5px'}),
            "Carregando dados..."
        ], style={'fontSize': '14px'})
    
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chamadas")
            total_registros = cursor.fetchone()[0]
            
            # Obter data da última atualização do banco
            cursor = conn.execute("SELECT MAX(created_at) FROM chamadas")
            ultima_atualizacao = cursor.fetchone()[0]
        
        return html.Span([
            html.I(className="fas fa-database", style={'color': '#28a745', 'marginRight': '5px'}),
            f"{total_registros:,} registros",
            html.Br(),
            html.Small("Dados do banco local", style={'color': 'gray'})
        ], style={'fontSize': '14px'})
    except:
        return html.Span([
            html.I(className="fas fa-database", style={'color': '#17a2b8', 'marginRight': '5px'}),
            "Banco de dados"
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

# Callback principal
@app.callback(
    [
        Output('total-ligacoes', 'children'),
        Output('total-atendidas', 'children'),
        Output('total-nao-atendidas', 'children'),
        Output('status-api', 'children'),
        Output('taxa-atendimento', 'children'),
        Output('duracao-media', 'children'),
        Output('total-tempo-falado', 'children'),
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
    # Carregar dados do cache/banco
    df_atual = carregar_dados()
    
    # Obter status dos dados
    status_texto = obter_status_dados()
    
    if df_atual is None or df_atual.empty:
        print("Dados não encontrados ou vazios")
        return [
            0, 0, 0, status_texto, "0%", "0s", "0s", [], 
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
        if 'datetime' not in df_atual.columns:
            print("❌ Coluna 'datetime' não encontrada no DataFrame")
            dff = pd.DataFrame()
        else:
            if not pd.api.types.is_datetime64_any_dtype(df_atual['datetime']):
                df_atual['datetime'] = pd.to_datetime(df_atual['datetime'], errors='coerce')
                df_atual = df_atual.dropna(subset=['datetime'])
            
            if not df_atual.empty:
                dff = df_atual[(df_atual['datetime'] >= datahora_ini) & (df_atual['datetime'] <= datahora_fim)]
                
                if destinos:
                    dff = dff[dff['cob'].isin(destinos)]
            else:
                dff = pd.DataFrame()
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
        
        # Total de tempo falado (soma de todas as durações de ligações atendidas)
        total_tempo_falado = ligacoes_atendidas['duracao'].sum() if not ligacoes_atendidas.empty else 0
        
        # Formatação dos valores
        total_ligacoes_str = f"{total_ligacoes:,}"
        total_atendidas_str = f"{total_atendidas:,}"
        total_nao_atendidas_str = f"{total_nao_atendidas:,}"
        taxa_atendimento_str = f"{taxa_atendimento:.1f}%"
        duracao_media_str = segundos_legiveis(duracao_media)
        total_tempo_falado_str = segundos_legiveis(total_tempo_falado)
        
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
                
                # Total de tempo falado
                total_tempo_cob = atendidas_dados['duracao'].sum() if not atendidas_dados.empty else 0
                
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
                                    html.Small('Tempo Total', className='text-muted'),
                                    html.H6(segundos_legiveis(total_tempo_cob), style={'color': '#AB63FA'})
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
        total_tempo_falado_str = "0s"
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
                barmode='stack'
            )
            
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
                hovermode='closest',
                bargap=0.2,
                showlegend=mostrar_legenda
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
                color_discrete_sequence=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880', '#EF553B']
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
                color_discrete_sequence=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880', '#EF553B'],
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
                marker=dict(colors=['#636EFA', '#FF0000', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FFFF00', '#B6E880', '#EF553B'])
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
        taxa_atendimento_str, duracao_media_str, total_tempo_falado_str,
        indicadores_cob_layout,
        fig_chamadas, fig_atendidas, fig_faixa, fig_linha_faixa, 
        fig_pizza, fig_indicador, fig_top_cob_atendidas, fig_top_cob_nao_atendidas
    )


# Callback para popular o dropdown de COB dinamicamente
@app.callback(
    [Output('cob-dropdown', 'options'),
     Output('cob-dropdown', 'value')],
    [Input('cob-dropdown', 'id')]  # Trigger na inicialização
)
def popular_dropdown_cob(_):
    """Popula o dropdown de COB com os dados disponíveis"""
    df_atual = carregar_dados_banco()
    
    if not df_atual.empty and 'cob' in df_atual.columns:
        # Remover valores nulos e obter valores únicos
        unique_cob_values = df_atual['cob'].dropna().sort_values().unique()
        
        # Criar opções do dropdown
        opcoes = [{'label': cob_legend.get(cob, f'COB {cob}'), 'value': cob} 
                  for cob in unique_cob_values if cob in cob_legend]
        
        # Definir valores selecionados (todos por padrão)
        valores_selecionados = [item['value'] for item in opcoes]
        
        print(f"🎯 COBs encontrados para dropdown: {list(unique_cob_values)}")
        print(f"🎯 COBs mapeados para dropdown: {valores_selecionados}")
        
        return opcoes, valores_selecionados
    else:
        print("⚠️ Nenhum COB encontrado para popular dropdown")
        return [], []


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)