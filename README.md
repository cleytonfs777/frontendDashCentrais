# Dashboard Central Telefônica - CBMMG

Dashboard para monitoramento de ligações do Corpo de Bombeiros Militar de Minas Gerais.

## 🚀 Como executar com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Executar a aplicação

1. **Clonar/baixar o projeto**
   ```bash
   # Se usando git
   git clone <url-do-repositorio>
   cd dashcentraltelefonica
   ```

2. **Construir e executar com Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Acessar a aplicação**
   ```
   http://localhost:8050
   ```

### Comandos úteis

- **Parar a aplicação:**
  ```bash
  docker-compose down
  ```

- **Executar em background:**
  ```bash
  docker-compose up -d --build
  ```

- **Ver logs:**
  ```bash
  docker-compose logs -f dashboard-frontend
  ```

- **Reconstruir apenas a imagem:**
  ```bash
  docker-compose build --no-cache
  ```

## 📁 Estrutura do projeto

```
├── docker-compose.yml          # Configuração do Docker Compose
├── frontend/                   # Aplicação Dash
│   ├── Dockerfile             # Configuração do container
│   ├── app.py                 # Aplicação principal
│   ├── dados.json             # Dados das ligações
│   ├── requirements.txt       # Dependências Python
│   └── assets/                # Arquivos estáticos
│       ├── bombeiro.png       # Logo
│       └── *.css             # Estilos CSS
└── README.md                  # Este arquivo
```

## 🔧 Desenvolvimento

Para desenvolvimento local sem Docker:

1. **Instalar dependências:**
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. **Executar aplicação:**
   ```bash
   python app.py
   ```

## 📊 Funcionalidades

- **Indicadores Gerais:** Total de ligações, atendidas, não atendidas
- **Indicadores Avançados:** Taxa de atendimento, duração média, tempo de espera
- **Indicadores por COB:** Comparação entre regiões
- **Gráficos Interativos:** 
  - Quantidade de chamadas por data e COB
  - Atendidas vs Não atendidas por região
  - Distribuição por faixa horária
  - Gráfico pizza de distribuição
  - Top atendente e top COB

## 🎯 COBs Monitorados

- 2ºCOB - Uberlândia
- 2ºCOB - Uberaba  
- 3ºCOB - Juiz de Fora
- 3ºCOB - Barbacena
- 4ºCOB - Montes Claros
- 5ºCOB - Governador Valadares
- 5ºCOB - Ipatinga
- 6ºCOB - Varginha

## 🔄 Atualizações

Para atualizar dados ou fazer modificações:

1. Edite os arquivos necessários
2. Reconstrua a imagem: `docker-compose build --no-cache`
3. Reinicie: `docker-compose up -d`
