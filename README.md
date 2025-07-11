# Dashboard Central Telefônica

Dashboard interativo para análise de dados de central telefônica do Corpo de Bombeiros Militar de Minas Gerais.

## Funcionalidades

- Visualização de métricas principais (total de ligações, atendidas, não atendidas)
- Indicadores avançados (taxa de atendimento, duração média, tempo total por dia)
- Gráficos interativos:
  - Linha: ligações por dia
  - Barras: ligações por faixa horária  
  - Heatmap: hora x dia da semana
  - Pizza: dias úteis vs fim de semana
- Filtros por data e fila de atendimento

## Requisitos

- Python 3.7+
- Arquivo `dados.json` na raiz do projeto

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute o dashboard:
```bash
python app.py
```

3. Acesse no navegador: http://127.0.0.1:8050

## Estrutura do Projeto

```
├── app.py                 # Aplicação principal
├── dados.json            # Dados da central telefônica
├── requirements.txt      # Dependências Python
├── assets/
│   └── style.css        # Estilos CSS customizados
└── README.md            # Documentação
```

## Cores e Tema

- Fundo principal: #162447 (azul escuro)
- Cards: branco com bordas arredondadas
- Títulos: #c04f03 (laranja)
- Gráficos: #a84105 (laranja) e #162447 (azul escuro)
