import pandas as pd
import numpy as np 
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
import logging
import time
from typing import Dict, Optional

# Configuração básica de logging para melhor feedback do processo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Bloco para carregar credenciais com segurança
try:
    import my_credentials as credential
except ImportError:
    logging.error("Arquivo de credenciais 'my_credentials.py' não encontrado.")
    exit()

# --- ETAPA 1: CONFIGURAÇÃO (Otimizada) ---

def inicializar_api():
    """Inicializa a API do Facebook. Encerra o script em caso de falha."""
    try:
        FacebookAdsApi.init(
            app_id=credential.APP_ID,
            app_secret=credential.APP_SECRET,
            access_token=credential.ACCESS_TOKEN
        )
        logging.info("API do Meta Ads inicializada com sucesso!")
        return True
    except Exception as e:
        logging.critical(f"Erro fatal ao inicializar a API: {e}")
        return False

# Definição dos campos e parâmetros (constantes)
INSIGHT_FIELDS = [
    'campaign_name', 'campaign_id',
    'adset_name', 'adset_id',
    'ad_name', 'ad_id',
    'spend', 'inline_link_clicks',
    'reach', 'impressions',
    'ctr', 'cpc',
    'actions'
]

INSIGHT_PARAMS = {
    'level': 'adset',
    'date_preset': 'last_7d',
    'time_increment': 'all_days',
    'limit': 2000
}

# --- ETAPA 2: EXTRAÇÃO ASSÍNCRONA (Melhoria de Performance) ---

def extrair_insights_de_multiplas_contas(mapa_clientes: Dict[str, str]) -> Optional[pd.DataFrame]:
    """
    Inicia requisições assíncronas para buscar insights de múltiplas contas,
    aguarda a conclusão e consolida os resultados em um único DataFrame.
    """
    jobs = []
    logging.info(f"Iniciando {len(mapa_clientes)} jobs de extração assíncrona.")

    for nome_cliente, ad_account_id in mapa_clientes.items():
        try:
            account = AdAccount(fbid=ad_account_id)
            async_job = account.get_insights(fields=INSIGHT_FIELDS, params=INSIGHT_PARAMS, is_async=True)
            jobs.append({'job': async_job, 'nome_cliente': nome_cliente})
            logging.info(f"--> Job para '{nome_cliente}' (ID: {ad_account_id}) iniciado.")
        except FacebookRequestError as e:
            logging.error(f"Erro ao iniciar job para '{nome_cliente}': {e.api_error_message()}")

    insights_por_cliente = []
    active_jobs = list(jobs)
    while active_jobs:
        time.sleep(5) # Aguarda para não sobrecarregar a API com verificações
        remaining_jobs = []
        for job_info in active_jobs:
            job = job_info['job']
            nome_cliente = job_info['nome_cliente']
            
            try:
                job.api_get() 
                status = job['async_status']
                
                if status == 'Job Completed':
                    insights_cursor = job.get_result()
                    insights_list = [dict(insight) for insight in insights_cursor]
                    
                    if insights_list:
                        df_cliente = pd.DataFrame(insights_list)
                        df_cliente['nome_cliente'] = nome_cliente
                        insights_por_cliente.append(df_cliente)
                        logging.info(f"  [SUCESSO] Job para '{nome_cliente}' concluído. {len(df_cliente)} registros obtidos.")
                    else:
                        logging.warning(f"  [AVISO] Job para '{nome_cliente}' concluído, mas sem dados.")
                
                elif status in ['Job Failed', 'Job Skipped']:
                    logging.error(f"  [FALHA] Job para '{nome_cliente}' falhou com status: {status}. Causa: {job.get('async_percent_completion', 'N/A')}")
                
                else: 
                    remaining_jobs.append(job_info) # Job ainda não terminou, verifica novamente
                    
            except FacebookRequestError as e:
                logging.error(f"  [ERRO API] Erro ao verificar status do job para '{nome_cliente}': {e.api_error_message()}")
            except Exception as e:
                logging.error(f"  [ERRO INESPERADO] Ocorreu um erro com o job de '{nome_cliente}': {e}")
        
        active_jobs = remaining_jobs
            
    if not insights_por_cliente:
        logging.warning("Nenhum dado foi extraído de nenhuma conta.")
        return None

    df_consolidado = pd.concat(insights_por_cliente, ignore_index=True)
    logging.info("Todos os dados dos clientes foram consolidados com sucesso.")
    return df_consolidado


# --- ETAPA 3: PÓS-PROCESSAMENTO AVANÇADO ---

def processar_e_salvar(df: pd.DataFrame, caminho_saida: str):
    """
    Realiza a limpeza, transforma a coluna 'actions' e salva o DataFrame final.
    """
    if df is None or df.empty:
        logging.warning("DataFrame vazio. Nada para processar ou salvar.")
        return

    logging.info("Iniciando pós-processamento do DataFrame consolidado...")

    # 1. Transformação da coluna 'actions' (de dicionário para colunas)
    if 'actions' in df.columns:
        df_actions = df.dropna(subset=['actions']).copy()
        if not df_actions.empty:
            df_actions = df_actions.explode('actions')
            df_actions['action_type'] = df_actions['actions'].apply(lambda x: x.get('action_type'))
            df_actions['value'] = pd.to_numeric(df_actions['actions'].apply(lambda x: x.get('value')), errors='coerce')
            
            actions_pivot = df_actions.pivot_table(
                index=df_actions.index, 
                columns='action_type', 
                values='value',
                aggfunc='sum'
            ).add_prefix('action_')
            
            df = df.join(actions_pivot)
            df = df.drop(columns=['actions'])
            logging.info("Coluna 'actions' transformada em colunas individuais.")

    # 2. Conversão de tipos de dados
    cols_to_numeric = [
        'spend', 'inline_link_clicks', 'impressions', 
        'ctr', 'cpc', 'reach'
    ]
    action_cols = [col for col in df.columns if col.startswith('action_')]
    cols_to_numeric.extend(action_cols)

    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    logging.info("Colunas métricas convertidas para formato numérico.")

    # 3. Tratamento de Valores Nulos (NOVA SEÇÃO)
    # Para colunas numéricas, preenche nulos com 0
    numeric_cols = df.select_dtypes(include=np.number).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    logging.info("Valores nulos em colunas numéricas preenchidos com 0.")

    # Para colunas de texto (object), preenche nulos com string vazia
    string_cols = df.select_dtypes(include='object').columns
    df[string_cols] = df[string_cols].fillna('')
    logging.info("Valores nulos em colunas de texto preenchidos com ''.")

    # 4. Reordenação de colunas para melhor visualização
    primeiras_colunas = [
        'nome_cliente', 'date_start', 'date_stop', 'campaign_name', 
        'adset_name', 'ad_name'
    ]
    primeiras_colunas_existentes = [col for col in primeiras_colunas if col in df.columns]
    outras_colunas = [col for col in df.columns if col not in primeiras_colunas_existentes]
    df = df[primeiras_colunas_existentes + outras_colunas]

    # 5. Salvar o arquivo final
    try:
        df.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
        logging.info(f"Relatório consolidado e processado salvo em: {caminho_saida}")
    except Exception as e:
        logging.error(f"Não foi possível salvar o arquivo CSV: {e}")

# --- FUNÇÃO PRINCIPAL ---

def main():
    """Função principal que orquestra todo o pipeline."""
    if not inicializar_api():
        return

    ARQUIVO_SAIDA = "relatorio_consolidado_clientes.csv"
    try:
        MAPA_DE_CLIENTES = credential.MAPA_DE_CLIENTES
    except AttributeError:
        logging.error("A variável 'MAPA_DE_CLIENTES' não foi encontrada no seu arquivo 'my_credentials.py'.")
        return

    df_final = extrair_insights_de_multiplas_contas(MAPA_DE_CLIENTES)
    processar_e_salvar(df_final, ARQUIVO_SAIDA)

    logging.info("Pipeline concluído!")

if __name__ == "__main__":
    main()