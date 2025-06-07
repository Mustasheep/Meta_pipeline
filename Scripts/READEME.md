# Guia do pipeline de Análise de Dados de Anúncios

## Visão Geral

O pipeline executa um processo de ETL (Extração, Transformação e Carga) que consiste em:
1.  **Extração**: Carrega os dados de um arquivo CSV.
2.  **Transformação**: Limpa os dados, converte tipos, calcula métricas essenciais (como CPC e CTR) e cria novas features a partir das datas (engenharia de features).
3.  **Carga**: Salva um novo arquivo CSV com os dados enriquecidos e gera relatórios visuais em formato de imagem (`.png`).

O script é totalmente parametrizável via linha de comando, permitindo flexibilidade para processar diferentes arquivos de entrada e especificar diretórios de saída.

## Features

- **Limpeza de Dados**: Converte colunas de data e preenche valores numéricos ausentes.
- **Engenharia de Features**:
    - Recalcula os valores de **CPC** (Custo Por Clique) e **CTR** (Taxa de Clique) para garantir a precisão.
    - Extrai informações valiosas de datas, como dia da semana, mês, semana do ano e se é fim de semana.
    - Categoriza o CPC em faixas (Muito Baixo, Baixo, Médio, Alto).
- **Geração de Relatórios**: Cria e salva automaticamente os seguintes gráficos:
    - Distribuição do Gasto Diário.
    - Contagem de Anúncios por Dia da Semana.
    - Proporção de Anúncios por Plataforma (Facebook, Instagram, etc.).
- **Parametrização**: Permite especificar arquivos de entrada e pastas de saída via linha de comando.

## Pré-requisitos

Para executar este pipeline, você precisará ter o Python 3 instalado, juntamente com as seguintes bibliotecas:

- pandas
- numpy
- seaborn
- matplotlib

Você pode instalar todas as dependências de uma vez executando o seguinte comando no seu terminal:

```bash
pip install pandas numpy seaborn matplotlib
```

## Como Usar

O pipeline é executado através do terminal. Abaixo estão os comandos para diferentes cenários de uso.

### 1. Execução Padrão

Este comando executará o pipeline usando os valores padrão definidos no script:
- **Arquivo de entrada**: `arquivo.csv`
- **Pasta de saída**: `relatorios_analise`
- **Arquivo final**: `dados_enriquecidos.csv`

```bash
python pipeline_parametrizado.py
```

### 2. Especificando Arquivos de Entrada e Saída

Use as flags `--entrada` e `--saida` para processar um arquivo diferente e salvar os resultados em uma pasta específica.

**Exemplo:**
Vamos supor que você tenha os dados de Maio em `dados_maio.csv` e queira salvar os relatórios na pasta `relatorios_de_maio`.

```bash
python pipeline_parametrizado.py --entrada dados_maio.csv --saida relatorios_de_maio
```

### 3. Customizando Todos os Parâmetros

Você também pode customizar o nome do arquivo CSV de saída com a flag `--arquivo_final`.

**Exemplo:**

```bash
python pipeline_parametrizado.py --entrada dados_junho.csv --saida relatorios_junho --arquivo_final dados_processados_jun.csv
```

### 4. Obtendo Ajuda

Para ver todas as opções disponíveis e suas descrições, use a flag `--help`.

```bash
python pipeline_parametrizado.py --help
```

## Formato do Arquivo de Entrada

O arquivo CSV de entrada (`--entrada`) deve conter, no mínimo, as seguintes colunas para que o pipeline funcione corretamente:
- `campaign_name`
- `campaign_id`
- `spend`
- `inline_link_clicks`
- `impressions`
- `ctr`
- `cpc`
- `date_start`
- `date_stop`
- `publisher_platform`

## Arquivos de Saída

Ao final da execução, os seguintes arquivos serão gerados dentro da pasta especificada pelo argumento `--saida`:

1.  **`distribuicao_gasto.png`**: Gráfico de histograma mostrando a distribuição dos gastos diários.
2.  **`anuncios_por_dia.png`**: Gráfico de barras mostrando a quantidade de registros de anúncios por dia da semana.
3.  **`proporcao_plataforma.png`**: Gráfico de pizza mostrando a distribuição de anúncios entre as plataformas (ex: Instagram, Facebook).
4.  **`gasto_vs_cliques.png`**: Gráfico de dispersão multivariado.
4.  **`[nome_do_arquivo_final].csv`**: Um novo arquivo CSV contendo todos os dados originais mais as colunas de features criadas durante o processo de transformação. Por padrão, o nome é `dados_enriquecidos.csv`.
