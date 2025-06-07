import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import logging
import argparse

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- PARSE DE ARGUMENTOS ---
def parse_argumentos():
    """
    Analisa e processa os argumentos passados pela linha de comando.
    """
    parser = argparse.ArgumentParser(description="Pipeline de análise de dados de anúncios.")
    
    parser.add_argument(
        '--entrada',
        type=str,
        default='arquivo.csv',
        help='Caminho do arquivo CSV de entrada. Padrão: arquivo.csv'
    )
    
    parser.add_argument(
        '--saida',
        type=str,
        default='relatorios_analise',
        help='Nome da pasta para salvar os relatórios. Padrão: relatorios_analise'
    )

    parser.add_argument(
        '--arquivo_final',
        type=str,
        default='dados_enriquecidos.csv',
        help='Nome do arquivo CSV de saída com dados enriquecidos. Padrão: dados_enriquecidos.csv'
    )

    return parser.parse_args()

# --- ETAPA 1: CARGA E LIMPEZA DOS DADOS (sem alterações) ---
def carregar_e_limpar_dados(caminho_arquivo: str) -> pd.DataFrame:
    """
    Carrega os dados de um arquivo CSV, converte colunas de data e
    preenche valores numéricos ausentes com zero.
    """
    logging.info(f"Iniciando a carga do arquivo: {caminho_arquivo}")
    try:
        df = pd.read_csv(caminho_arquivo)
        
        if 'date_start' in df.columns:
            df['date_start'] = pd.to_datetime(df['date_start'])
        if 'date_stop' in df.columns:
            df['date_stop'] = pd.to_datetime(df['date_stop'])
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        logging.info("DataFrame carregado e limpo com sucesso.")
        return df
    except FileNotFoundError:
        logging.error(f"Erro: O arquivo {caminho_arquivo} não foi encontrado.")
        return None
    except Exception as e:
        logging.error(f"Erro ao carregar ou limpar os dados: {e}")
        return None

# --- ETAPA 2: ENGENHARIA DE FEATURES (sem alterações) ---
def engenharia_de_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria novas features a partir dos dados existentes, como métricas
    calculadas e features de data.
    """
    logging.info("Iniciando a engenharia de features.")
    
    df['cpc_calculado'] = df.apply(
        lambda row: row['spend'] / row['inline_link_clicks'] if row['inline_link_clicks'] > 0 else 0,
        axis=1
    )
    df['ctr_calculado'] = df.apply(
        lambda row: (row['inline_link_clicks'] / row['impressions']) * 100 if row['impressions'] > 0 else 0,
        axis=1
    )
    
    df['dia_da_semana'] = df['date_start'].dt.day_name()
    df['dia_do_mes'] = df['date_start'].dt.day
    df['mes'] = df['date_start'].dt.month
    df['semana_do_ano'] = df['date_start'].dt.isocalendar().week
    df['fim_de_semana'] = df['dia_da_semana'].isin(['Saturday', 'Sunday'])

    cpc_bins = [0, 0.5, 1.0, 3.0, df['cpc_calculado'].max() + 1]
    cpc_labels = ['Muito Baixo', 'Baixo', 'Médio', 'Alto']
    df['cpc_categoria'] = pd.cut(df['cpc_calculado'], bins=cpc_bins, labels=cpc_labels, right=False, include_lowest=True)
    
    logging.info("Engenharia de features concluída.")
    return df

# --- ETAPA 3: ANÁLISE E GERAÇÃO DE RELATÓRIOS (sem alterações) ---
def analisar_e_gerar_relatorios(df: pd.DataFrame, pasta_saida: str):
    """
    Realiza análises descritivas e gera visualizações (relatórios),
    salvando os resultados em uma pasta.
    """
    logging.info("Iniciando análise e geração de relatórios.")
    
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    # Análise de Métricas Chave
    logging.info(f"Gasto médio diário: R$ {df['spend'].mean():.2f}")
    logging.info(f"CPC médio: R$ {df['cpc_calculado'].mean():.2f}")

    # Geração de Gráficos
    plt.figure()
    sns.histplot(df['spend'], bins=20, kde=True)
    plt.title('Distribuição do Gasto Diário')
    plt.savefig(os.path.join(pasta_saida, 'distribuicao_gasto.png'))
    plt.close()

    plt.figure()
    sns.countplot(y=df['dia_da_semana'], order=df['dia_da_semana'].value_counts().index)
    plt.title('Número de Anúncios por Dia da Semana')
    plt.savefig(os.path.join(pasta_saida, 'anuncios_por_dia.png'))
    plt.close()

    plt.figure()
    df['publisher_platform'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title('Proporção de Anúncios por Plataforma')
    plt.ylabel('')
    plt.savefig(os.path.join(pasta_saida, 'proporcao_plataforma.png'))
    plt.close()
    
    logging.info(f"Relatórios salvos em: {pasta_saida}")

# --- FUNÇÃO PRINCIPAL ATUALIZADA ---
def main():
    """
    Orquestra a execução de todas as etapas do pipeline.
    """
    # Utiliza a função para obter os argumentos da linha de comando
    args = parse_argumentos()

    # Execução das etapas usando os argumentos
    df_limpo = carregar_e_limpar_dados(args.entrada)
    
    if df_limpo is not None:
        df_features = engenharia_de_features(df_limpo)
        analisar_e_gerar_relatorios(df_features, args.saida)
        
        # Salva o DataFrame final com nome e caminho parametrizados
        caminho_arquivo_saida = os.path.join(args.saida, args.arquivo_final)
        df_features.to_csv(caminho_arquivo_saida, index=False)
        
        logging.info(f"Dados enriquecidos salvos em: {caminho_arquivo_saida}")
        logging.info("Pipeline executado com sucesso!")


if __name__ == "__main__":
    main()