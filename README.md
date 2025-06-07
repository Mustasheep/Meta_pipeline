# MetaAPI: Unificando Ciência de Dados e Gestão de Tráfego

## Descrição

Este repositório contém uma solução completa para extração e análise de dados da Meta API (Facebook Ads API), com o objetivo de aplicar princípios de ciência de dados para otimizar campanhas de tráfego pago. O projeto é composto por dois componentes principais:
1.  Um **script de extração** (`campanhas.py`) que coleta dados brutos de campanhas e performance.
2.  Um **pipeline de análise** (`pipeline_analise.py`) que processa esses dados, gera insights e cria relatórios visuais de forma automatizada.

Este projeto visa facilitar a coleta e análise de dados essenciais para tomada de decisões estratégicas em marketing digital.

## Objetivo do Projeto

O principal objetivo desta solução é:

* **Automatizar a coleta de dados** detalhados de campanhas (configurações, status, orçamentos) e métricas de performance (KPIs como spend, cliques, CTR, CPC) da Meta API.
* **Estruturar os dados** em formatos tabulares (DataFrames do Pandas) para fácil manipulação.
* **Processar e enriquecer os dados** através de um pipeline de análise que realiza limpeza, validação e engenharia de features.
* **Gerar relatórios automáticos** e visualizações que facilitem a compreensão da performance das campanhas.
* Fornecer uma base para análises mais aprofundadas e, futuramente, a aplicação de modelos de ciência de dados para otimização.

## Estrutura do Repositório

```
script_metaapi/
├── Scripts/
│   ├── campanhas.py          # Script para extração de dados da Meta API
│   └── pipeline_analise.py   # Pipeline para análise e geração de relatórios
├── relatorios_analise/       # Pasta de exemplo para os relatórios gerados
│   ├── distribuicao_gasto.png
│   ├── dados_enriquecidos.csv
│   └ ...
├── .gitignore
├── LICENSE
├── README.md
└── Requirements.txt
```

## Funcionalidades

### 1. Script de Extração (`campanhas.py`)

Este script se conecta à Meta API e realiza as seguintes operações:

* **Carregamento de Credenciais:** Importa de forma segura as credenciais da API (`App ID`, `App Secret`, etc.) de um arquivo local `my_credentials.py`.
* **Inicialização da API:** Estabelece conexão com a Facebook Ads API.
* **Extração de Dados de Campanhas:** Busca informações detalhadas de todas as campanhas (`id`, `name`, `status`, `budget`, etc.) e as armazena no DataFrame `df_campaigns`.
* **Extração de Insights de Performance:** Busca métricas de desempenho para as campanhas ativas nos últimos 7 dias, segmentadas por plataforma. Os dados (`spend`, `clicks`, `ctr`, `cpc`) são armazenados no DataFrame `df_insights`.
* **Geração de Arquivo:** Salva os insights de performance em um arquivo CSV, que servirá de entrada para o pipeline de análise.

### 2. Pipeline de Análise de Performance (`pipeline_analise.py`)

Este segundo script consome os dados gerados pelo extrator e executa um pipeline de análise automatizado com as seguintes funcionalidades:

* **Carga e Limpeza**: Carrega o CSV de insights, converte tipos de dados e trata valores ausentes.
* **Engenharia de Features**: Cria novas colunas com informações valiosas, como dia da semana, e recalcula métricas como CPC e CTR para garantir consistência.
* **Geração de Relatórios Visuais**: Cria e salva automaticamente gráficos em formato `.png` sobre a distribuição de gastos, performance por dia da semana e proporção por plataforma.
* **Saída de Dados Enriquecidos**: Salva um novo arquivo CSV contendo os dados originais acrescidos das novas features, pronto para análises mais profundas ou para ser usado em dashboards.

## Tecnologias Utilizadas

* **Python 3.x**
* **Pandas:** Para manipulação e análise de dados.
* **Facebook Business SDK (`facebook_business`):** Biblioteca oficial para interagir com a Ads API.
* **Matplotlib & Seaborn:** Para a geração dos gráficos e visualizações no pipeline de análise.

## Como Usar

O fluxo de trabalho consiste em duas etapas principais: extrair os dados e, em seguida, analisá-los.

### Etapa 1: Extrair os Dados com `campanhas.py`

1.  **Pré-requisitos:**
    * Python 3.x instalado.
    * Uma conta de Desenvolvedor da Meta com um App aprovado para acesso à Ads API (permissões `ads_management` e `ads_read`).
    * Suas credenciais: `APP_ID`, `APP_SECRET`, `ACCESS_TOKEN` e `AD_ACCOUNT_ID`.

2.  **Instalação:**
    ```bash
    git clone [https://github.com/Mustasheep/script_metaapi.git](https://github.com/Mustasheep/script_metaapi.git)
    cd script_metaapi
    pip install -r Requirements.txt
    ```

3.  **Configuração:**
    * Crie um arquivo chamado `my_credentials.py` na raiz do projeto.
    * Adicione suas credenciais a este arquivo:
        ```python
        # my_credentials.py
        APP_ID = 'SEU_APP_ID'
        APP_SECRET = 'SEU_APP_SECRET'
        ACCESS_TOKEN = 'SEU_ACCESS_TOKEN'
        AD_ACCOUNT_ID = 'SEU_AD_ACCOUNT_ID'
        ```

4.  **Execução da Extração:**
    * **Importante:** No script `Scripts/campanhas.py`, certifique-se de que a funcionalidade para salvar os insights em um arquivo CSV esteja ativa (descomentada). Ela será a fonte de dados para a próxima etapa.
    * Execute o script:
        ```bash
        python Scripts/campanhas.py
        ```
    * Ao final, um arquivo como `insights_campanhas_por_plataforma.csv` será criado na raiz do projeto.

### Etapa 2: Analisar os Dados com o Pipeline

1.  **Execução da Análise:**
    * O pipeline de análise (`pipeline_analise.py`) é executado via terminal e pode receber parâmetros para definir os arquivos de entrada e saída.
    * Execute o script, passando o arquivo gerado na etapa anterior como entrada:
        ```bash
        # Exemplo: usando o arquivo gerado e salvando na pasta 'meus_relatorios'
        python Scripts/pipeline_analise.py --entrada insights_campanhas_por_plataforma.csv --saida meus_relatorios
        ```

    * Para ver todas as opções de parametrização, utilize o comando de ajuda:
        ```bash
        python Scripts/pipeline_analise.py --help
        ```

## Próximos Passos e Evolução

Este projeto integrado forma uma excelente base para automação e análises mais complexas. Algumas ideias para evolução:

* **Orquestração de Dados:** Utilizar ferramentas como Cron ou Apache Airflow para agendar a execução sequencial dos scripts (primeiro a extração, depois a análise).
* **Aprimoramento dos Dashboards:** Enviar os dados do CSV enriquecido para ferramentas de BI (Power BI, Looker Studio) para criar painéis interativos.
* **Detecção de Anomalias:** Implementar algoritmos no pipeline de análise para identificar mudanças bruscas em KPIs e enviar alertas.
* **Machine Learning:** Aplicar modelos de regressão para prever performance, segmentação de audiências com clustering e NLP para análise de criativos.

## Autor

* [LinkedIn](https://www.linkedin.com/in/thiago-mustasheep/)

## Licença

Este projeto está licenciado sob a Licença MIT - consulte o arquivo [LICENSE](LICENSE) para obter detalhes.

