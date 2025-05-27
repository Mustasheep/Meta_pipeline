# MetaAPI: Unificando Ciência de Dados e Gestão de Tráfego

## Descrição

Este repositório contém um script Python desenvolvido para interagir com a Meta API (Facebook Ads API), com o objetivo de extrair dados de campanhas e insights de performance. A finalidade é aplicar princípios de ciência de dados para analisar e otimizar campanhas de tráfego pago, servindo como uma ponte entre a gestão de tráfego e a análise de dados.

Este projeto visa facilitar a coleta automatizada de dados essenciais para tomada de decisões estratégicas em marketing digital.

## Objetivo do Projeto

O principal objetivo deste script é:

* Automatizar a coleta de dados detalhados de campanhas (configurações, status, orçamentos) da Meta API.
* Extrair métricas de performance (KPIs como spend, cliques, impressões, CTR, CPC) de campanhas ativas.
* Estruturar os dados coletados em formatos tabulares (DataFrames do Pandas) para fácil manipulação e análise subsequente.
* Fornecer uma base para análises mais aprofundadas, relatórios personalizados e, futuramente, a aplicação de modelos de ciência de dados para otimização de campanhas.

## Estrutura do Repositório
```
script_metaapi/
├── Scripts/                  
│   └── campanhas.py
├── .gitignore
├── LICENSE
├── README.md                
└── Requirements.txt          
```

## Funcionalidades do Script

O script principal realiza as seguintes operações:

1.  **Carregamento de Credenciais:** Importa de forma segura as credenciais da API (App ID, App Secret, Access Token, Ad Account ID) a partir de um arquivo local `my_credentials.py`.
2.  **Inicialização da API:** Estabelece conexão com a Facebook Ads API.
3.  **Extração de Dados de Campanhas:**
    * Conecta-se à conta de anúncios especificada.
    * Busca informações detalhadas de todas as campanhas, incluindo: `id`, `name`, `status`, `effective_status`, `objective`, `created_time`, `start_time`, `stop_time`, `spend_cap`, `daily_budget`, `lifetime_budget`.
    * Armazena esses dados em um DataFrame do Pandas chamado `df_campaigns`.
4.  **Extração de Insights de Performance:**
    * Busca métricas de desempenho para as campanhas `ATIVAS` nos últimos 7 dias (`last_7d`), com dados diários (`time_increment: 1`) e segmentados por plataforma de veiculação (`breakdowns: ['publisher_platform']`).
    * Os insights coletados incluem: `campaign_name`, `campaign_id`, `spend`, `inline_link_clicks`, `impressions`, `ctr`, `cpc`.
    * Converte as colunas numéricas relevantes para o tipo de dado correto.
    * Armazena esses dados em um DataFrame do Pandas chamado `df_insights`.
    * (Possui uma funcionalidade comentada para salvar os insights em um arquivo `insights_campanhas_por_plataforma.csv`).

## Tecnologias Utilizadas

* **Python 3.x**
* **Pandas:** Para manipulação e análise de dados em formato de DataFrame.
* **Facebook Business SDK (`facebook_business`):** Biblioteca oficial da Meta para interagir com a Ads API.

## Como Usar

1.  **Pré-requisitos:**
    * Python 3.x instalado.
    * Conta de Desenvolvedor da Meta configurada e aprovada para acesso à Ads API.
    * Um App da Meta criado com as permissões `ads_management` e `ads_read`.
    * As seguintes credenciais obtidas da sua aplicação Meta e conta de anúncios:
        * `APP_ID`
        * `APP_SECRET`
        * `ACCESS_TOKEN` (de preferência um token de acesso de longa duração)
        * `AD_ACCOUNT_ID` (no formato `act_XXXXXXXXXXXXX`)

2.  **Instalação:**
    ```bash
    git clone https://github.com/Mustasheep/script_metaapi.git
    cd script_metaapi
    pip install -r Requirements.txt
    ```

3.  **Configuração:**
    * Crie um arquivo chamado `my_credentials.py` na raiz do projeto (no mesmo nível que o script principal).
    * Adicione suas credenciais a este arquivo da seguinte forma:
        ```python
        # my_credentials.py
        APP_ID = 'SEU_APP_ID'
        APP_SECRET = 'SEU_APP_SECRET'
        ACCESS_TOKEN = 'SEU_ACCESS_TOKEN'
        AD_ACCOUNT_ID = 'SEU_AD_ACCOUNT_ID'
        ```

4.  **Execução:**
    * Navegue até a pasta onde o script está localizado.
    * Execute o script usando Python:
        ```bash
        python campanhas.py
        ```
    * O script imprimirá mensagens de status no console e, se bem-sucedido, os DataFrames `df_campaigns` e `df_insights` estarão disponíveis no ambiente do script para uso (recomendo executar em um interpretador Python interativo, como o Jupyter notebook).


## Próximos Passos e Evolução

Este script forma uma excelente base para análises mais complexas. Algumas ideias para evolução:

* **Visualização de Dados:** Gerar gráficos e dashboards (ex: com `matplotlib`, `seaborn`, `plotly` ou ferramentas de BI).
* **Detecção de Anomalias:** Identificar mudanças bruscas em KPIs.
* **Automação Avançada:** Agendar a execução do script para coletar dados regularmente.
* **Relatórios Automáticos:** Gerar e enviar relatórios por e-mail.
* **Machine Learning:** Aplicar modelos de regressão para prever performance, segmentação de audiências com clustering e NLP para análise de criativos.

## Licença

Este projeto está licenciado sob a Licença MIT - consulte o arquivo [LICENSE](LICENSE) para obter detalhes.
