import pandas as pd
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
import logging
import time
from typing import Dict, Optional, List

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

def inicializar_api() -> bool:
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
    'date_start',
    'campaign_name', 'campaign_id',
    'adset_name', 'adset_id',
    'spend',
    'reach',
    'impressions',
    'ctr',
    'cpc',
    'cost_per_action_type'
]

INSIGHT_PARAMS = {
    'level': 'adset',
    'date_preset': 'last_7d',
    'time_increment': 1,
    'limit': 2000
}

# --- ETAPA 2: EXTRAÇÃO ASSÍNCRONA ---

def extrair_insights_de_multiplas_contas(mapa_clientes: Dict[str, str]) -> Optional[pd.DataFrame]:
    """
    Inicia requisições assíncronas para buscar insights de múltiplas contas,
    aguarda a conclusão e consolida os resultados em um único DataFrame.
    """
    jobs = []
    logging.info(f"Iniciando {len(mapa_clientes)} jobs de extração assíncrona no nível de Conjunto de Anúncios.")

    for nome_cliente, ad_account_id in mapa_clientes.items():
        try:
            account = AdAccount(fbid=f'{ad_account_id}')
            async_job = account.get_insights(fields=INSIGHT_FIELDS, params=INSIGHT_PARAMS, is_async=True)
            jobs.append({'job': async_job, 'nome_cliente': nome_cliente, 'ad_account_id': ad_account_id})
            logging.info(f"--> Job para '{nome_cliente}' (ID da Conta: {ad_account_id}) iniciado.")
        except FacebookRequestError as e:
            logging.error(f"Erro ao iniciar job para '{nome_cliente}': {e.api_error_message()}")

    insights_por_cliente: List[pd.DataFrame] = []
    active_jobs = list(jobs)
    
    while active_jobs:
        time.sleep(5)
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
                    remaining_jobs.append(job_info)
                    
            except FacebookRequestError as e:
                logging.error(f"  [ERRO API] Erro ao verificar status do job para '{nome_cliente}': {e.api_error_message()}")
                if not e.api_transient():
                    logging.error(f"  --> Erro permanente para '{nome_cliente}'. O job será descartado.")
                else:
                    remaining_jobs.append(job_info)
            except Exception as e:
                logging.error(f"  [ERRO INESPERADO] Ocorreu um erro com o job de '{nome_cliente}': {e}")
        
        active_jobs = remaining_jobs
            
    if not insights_por_cliente:
        logging.warning("Nenhum dado foi extraído de nenhuma conta.")
        return None

    df_consolidado = pd.concat(insights_por_cliente, ignore_index=True)
    logging.info("Todos os dados dos clientes foram consolidados com sucesso.")
    return df_consolidado

# --- ETAPA 3: PÓS-PROCESSAMENTO ---

def extrair_custos(row: pd.Series) -> pd.Series:
    """
    Função para extrair CUSTOS específicos da coluna 'cost_per_action_type'.
    """
    custo_por_visita = 0.0
    custo_por_mensagem = 0.0

    if isinstance(row.get('cost_per_action_type'), list):
        for cost_action in row['cost_per_action_type']:
            action_type = cost_action.get('action_type')
            value = float(cost_action.get('value', 0.0))
            
            if action_type == 'landing_page_view':
                custo_por_visita = value
            elif action_type == 'onsite_conversion.messaging_conversation_started_7d':
                custo_por_mensagem = value
    
    return pd.Series([custo_por_visita, custo_por_mensagem])


def processar_e_salvar(df: pd.DataFrame, caminho_saida: str):
    """
    Realiza a limpeza, renomeia colunas, cria features de data e extrai métricas.
    """
    if df is None or df.empty:
        logging.warning("DataFrame vazio. Nada para processar ou salvar.")
        return

    logging.info("Iniciando pós-processamento...")

    # 1. Extração das métricas de custo
    logging.info("Extraindo métricas de custo...")
    metricas_custo = df.apply(extrair_custos, axis=1)
    metricas_custo.columns = ['custo_por_visita_pagina', 'custo_por_mensagem']
    df = pd.concat([df, metricas_custo], axis=1)
    df = df.drop(columns=['cost_per_action_type'])
    
    # 2. Renomeação de todas as colunas para Português
    logging.info("Renomeando colunas para português...")
    mapa_colunas = {
        'date_start': 'Data',
        'campaign_name': 'Campanha',
        'campaign_id': 'ID da Campanha',
        'adset_name': 'Conjunto de Anúncios',
        'adset_id': 'ID do Conjunto de Anúncios',
        'spend': 'Gasto (R$)',
        'reach': 'Alcance',
        'impressions': 'Impressões',
        'ctr': 'CTR (%)',
        'cpc': 'CPC (R$)',
        'nome_cliente': 'Cliente',
        'custo_por_visita_pagina': 'Custo por Visita (R$)',
        'custo_por_mensagem': 'Custo por Mensagem (R$)'
    }
    df.rename(columns=mapa_colunas, inplace=True)

    # 3. Conversão de tipos para colunas numéricas
    cols_numericas = [
        'Gasto (R$)', 'Alcance', 'Impressões', 'CTR (%)', 'CPC (R$)', 
        'Custo por Visita (R$)', 'Custo por Mensagem (R$)'
    ]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 4. Feature Engineering de Data
    logging.info("Criando features de data com mapeamento manual...")
    df['Data'] = pd.to_datetime(df['Data'])
    
    df['dia_semana_num'] = df['Data'].dt.dayofweek

    mapa_dias = {
        0: 'Segunda-feira',
        1: 'Terça-feira',
        2: 'Quarta-feira',
        3: 'Quinta-feira',
        4: 'Sexta-feira',
        5: 'Sábado',
        6: 'Domingo'
    }
    
    df['Dia da Semana'] = df['dia_semana_num'].map(mapa_dias)
    df.drop(columns=['dia_semana_num'], inplace=True)
    df.fillna(0, inplace=True)

    # 6. Reordenação e seleção final de colunas
    colunas_finais = [
        'Cliente',
        'Data',
        'Dia da Semana',
        'Campanha',
        'ID da Campanha',
        'Conjunto de Anúncios',
        'ID do Conjunto de Anúncios',
        'Gasto (R$)',
        'Impressões',
        'Alcance',
        'CTR (%)',
        'CPC (R$)',
        'Custo por Visita (R$)',
        'Custo por Mensagem (R$)'
    ]
    colunas_finais = [col for col in colunas_finais if col in df.columns]
    df = df[colunas_finais]

    # 7. Salvar o arquivo final
    df.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
    logging.info(f"Relatório consolidado e processado salvo em: {caminho_saida}")


# --- FUNÇÃO PRINCIPAL ---

def main():
    """Função principal que orquestra todo o pipeline."""
    if not inicializar_api():
        return
        
    MAPA_DE_CLIENTES = getattr(credential, 'MAPA_DE_CLIENTES', None)
    if not MAPA_DE_CLIENTES:
        logging.error("A variável 'MAPA_DE_CLIENTES' não foi encontrada em 'my_credentials.py'.")
        return

    df_final = extrair_insights_de_multiplas_contas(MAPA_DE_CLIENTES)
    processar_e_salvar(df_final, "relatorio_consolidado_clientes.csv")
    logging.info("Pipeline concluído!")

if __name__ == "__main__":
    main()