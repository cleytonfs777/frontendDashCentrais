import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time
import re
import os

# Carregar dados
# Carregar dados adicionais de JSON, se existir
JSON_PATH = 'dados.json'
if os.path.exists(JSON_PATH):
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        df = pd.read_json(f)
else:
    df = pd.DataFrame()

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
unique_cob_values = df['cob'].sort_values().unique()
unique_destinos = [{'label': cob_legend.get(cob, f'COB {cob}'), 'value': cob} for cob in unique_cob_values if cob in cob_legend]

# Converter coluna 'data' para datetime se não estiver vazia
if not df.empty and 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'])
    # Criar coluna datetime combinando data e hora
    df['datetime'] = pd.to_datetime(df['data'].dt.strftime('%Y-%m-%d') + ' ' + df['hora'].astype(str))
    # Mapear COB para nomes
    df['cob_nome'] = df['cob'].map(cob_legend)
    
    # Criar coluna de faixa horária
    df['hora_int'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.hour
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
    
    df['faixa_horaria'] = df['hora_int'].apply(definir_faixa_horaria)
    
    # Mapear estado para status legível
    df['status'] = df['estado'].map({0: 'Não Atendido', 1: 'Atendido'})
    
    min_date = df['data'].min().date()
    max_date = df['data'].max().date()
else:
    # Valores padrão caso não haja dados
    from datetime import date
    min_date = date.today()
    max_date = date.today()

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
        datahora_ini = df['datetime'].min() if not df.empty else datetime.now()
    try:
        datahora_fim = datetime.strptime(f"{date_fim} {hora_fim}", "%Y-%m-%d %H:%M")
    except:
        datahora_fim = df['datetime'].max() if not df.empty else datetime.now()

    # Filtrar dados
    if not df.empty:
        dff = df[(df['datetime'] >= datahora_ini) & (df['datetime'] <= datahora_fim)]
        if destinos:
            dff = dff[dff['cob'].isin(destinos)]
    else:
        dff = pd.DataFrame()

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
                color_discrete_map={'Atendido': '#00CC96', 'Não Atendido': '#FF6B6B'}
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

    return (fig_chamadas, fig_atendidas, fig_faixa, fig_linha_faixa, fig_pizza, fig_indicador, fig_top_cob_atendidas, fig_top_cob_nao_atendidas)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)