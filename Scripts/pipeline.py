import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ETAPA 1: CARGA E LIMPEZA DOS DADOS ---
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

# --- ETAPA 2: ENGENHARIA DE FEATURES ---
def engenharia_de_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria novas features a partir dos dados existentes, como métricas
    calculadas e features de data.
    """
    logging.info("Iniciando a engenharia de features.")
    
    # 2.1 Recalcular métricas para garantir consistência
    df['cpc_calculado'] = df.apply(
        lambda row: row['spend'] / row['inline_link_clicks'] if row['inline_link_clicks'] > 0 else 0,
        axis=1
    )
    df['ctr_calculado'] = df.apply(
        lambda row: (row['inline_link_clicks'] / row['impressions']) * 100 if row['impressions'] > 0 else 0,
        axis=1
    )
    
    # 2.2 Criar features de data
    df['dia_da_semana'] = df['date_start'].dt.day_name()
    df['dia_do_mes'] = df['date_start'].dt.day
    df['mes'] = df['date_start'].dt.month
    df['semana_do_ano'] = df['date_start'].dt.isocalendar().week
    df['fim_de_semana'] = df['dia_da_semana'].isin(['Saturday', 'Sunday'])

    # 2.3 Criar features de categoria (ex: categorizar CPC)
    cpc_bins = [0, 0.5, 1.0, 3.0, df['cpc_calculado'].max() + 1]
    cpc_labels = ['Muito Baixo', 'Baixo', 'Médio', 'Alto']
    df['cpc_categoria'] = pd.cut(df['cpc_calculado'], bins=cpc_bins, labels=cpc_labels, right=False, include_lowest=True)
    
    logging.info("Engenharia de features concluída.")
    return df

# --- ETAPA 3: ANÁLISE E GERAÇÃO DE RELATÓRIOS ---
def analisar_e_gerar_relatorios(df: pd.DataFrame, pasta_saida: str):
    """
    Realiza análises descritivas e gera visualizações (relatórios),
    salvando os resultados em uma pasta.
    """
    logging.info("Iniciando análise e geração de relatórios.")
    
    # Cria a pasta de saída se não existir
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    # 3.1 Análise de Métricas Chave (saída no console/log)
    media_gasto = df['spend'].mean()
    mediana_gasto = df['spend'].median()
    media_cpc = df['cpc_calculado'].mean()
    mediana_cpc = df['cpc_calculado'].median()

    logging.info(f"Gasto médio diário: R$ {media_gasto:.2f}")
    logging.info(f"Mediana do gasto diário: R$ {mediana_gasto:.2f}")
    logging.info(f"CPC médio: R$ {media_cpc:.2f}")
    logging.info(f"Mediana do CPC: R$ {mediana_cpc:.2f}")

    # 3.2 Geração de Gráficos (salvos em arquivo)
    
    # Distribuição do Gasto Diário
    plt.figure()
    sns.histplot(df['spend'], bins=20, kde=True)
    plt.title('Distribuição do Gasto Diário')
    plt.savefig(os.path.join(pasta_saida, 'distribuicao_gasto.png'))
    plt.close()

    # Anúncios por Dia da Semana
    plt.figure()
    sns.countplot(y=df['dia_da_semana'], order=df['dia_da_semana'].value_counts().index)
    plt.title('Número de Anúncios por Dia da Semana')
    plt.savefig(os.path.join(pasta_saida, 'anuncios_por_dia.png'))
    plt.close()

    # Proporção por Plataforma
    plt.figure()
    df['publisher_platform'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title('Proporção de Anúncios por Plataforma')
    plt.ylabel('')
    plt.savefig(os.path.join(pasta_saida, 'proporcao_plataforma.png'))
    plt.close()
    
    logging.info(f"Relatórios salvos em: {pasta_saida}")


# --- FUNÇÃO PRINCIPAL PARA ORQUESTRAR O PIPELINE ---
def main():
    """
    Orquestra a execução de todas as etapas do pipeline.
    """
    # Definição de caminhos
    ARQUIVO_ENTRADA = "arquivo.csv"
    PASTA_SAIDA = "relatorios_analise"

    # Execução das etapas
    df_limpo = carregar_e_limpar_dados(ARQUIVO_ENTRADA)
    
    if df_limpo is not None:
        df_features = engenharia_de_features(df_limpo)
        analisar_e_gerar_relatorios(df_features, PASTA_SAIDA)
        
        # Opcional: Salvar o DataFrame final para uso futuro
        df_features.to_csv(os.path.join(PASTA_SAIDA, "dados_enriquecidos.csv"), index=False)
        logging.info("Pipeline executado com sucesso!")


if __name__ == "__main__":
    main()