import pandas as pd
import numpy as np
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError
import logging
import time
from typing import Dict, Optional, List

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Carregamento seguro de credenciais
try:
    import my_credentials as credential
except ImportError:
    logging.error("Arquivo de credenciais 'my_credentials.py' não encontrado.")
    exit()

# --- ETAPA 1: CONFIGURAÇÃO ---

def inicializar_api() -> bool:
    """Inicializa a API do Facebook."""
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

# Definir parâmetros
INSIGHT_FIELDS = [
    'date_start',
    'campaign_name', 'campaign_id',
    'adset_name', 'adset_id',
    'spend',
    'reach',
    'impressions',
    'inline_link_clicks', 
    'ctr',
    'cpc',
    'cost_per_action_type',
    'actions',
    'action_values'
]

INSIGHT_PARAMS = {
    'level': 'adset',
    'date_preset': 'last_7d',
    'time_increment': '1', 
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

# --- ETAPA 3: PÓS-PROCESSAMENTO UNIFICADO ---

def processar_e_salvar(df: pd.DataFrame, caminho_saida: str):
    """
    Processa o DataFrame para extrair, calcular, formatar e selecionar
    apenas as colunas finais desejadas para o relatório.
    """
    if df is None or df.empty:
        logging.warning("DataFrame vazio. Nada para processar ou salvar.")
        return

    logging.info("Iniciando pós-processamento unificado...")

    def extrair_valor_de_acao(lista_acoes: list, tipo_acao_desejado: str, campo_valor: str = 'value') -> float:
        if not isinstance(lista_acoes, list):
            return 0.0
        for acao in lista_acoes:
            if acao.get('action_type') == tipo_acao_desejado:
                return float(acao.get(campo_valor, 0.0))
        return 0.0
    
    logging.info("Extraindo métricas de custo, compras e receita...")
    df['custo_por_visita'] = df['cost_per_action_type'].apply(lambda x: extrair_valor_de_acao(x, 'landing_page_view'))
    df['custo_por_mensagem'] = df['cost_per_action_type'].apply(lambda x: extrair_valor_de_acao(x, 'onsite_conversion.messaging_conversation_started_7d'))
    
    purchase_types = ['purchase', 'offsite_conversion.fb_pixel_purchase', 'omni_purchase']
    for p_type in purchase_types:
        df[f'compras_{p_type}'] = df['actions'].apply(lambda x: extrair_valor_de_acao(x, p_type))
        df[f'receita_{p_type}'] = df['action_values'].apply(lambda x: extrair_valor_de_acao(x, p_type))

    df['compras'] = df[[f'compras_{p_type}' for p_type in purchase_types]].sum(axis=1)
    df['receita_compras'] = df[[f'receita_{p_type}' for p_type in purchase_types]].sum(axis=1)

    logging.info("Calculando ROAS, Resultado (Lucro) e CPA...")
    df['spend'] = pd.to_numeric(df['spend'], errors='coerce').fillna(0)
    
    df['roas'] = np.where(df['spend'] > 0, df['receita_compras'] / df['spend'], 0)
    df['resultado_lucro'] = df['receita_compras'] - df['spend']
    df['cpa'] = np.where(df['compras'] > 0, df['spend'] / df['compras'], 0)

    logging.info("Formatando e selecionando as colunas finais para o relatório...")

    # Mapa de novas colunas à renomear
    colunas_finais_mapa = {
        'nome_cliente': 'Cliente',
        'date_start': 'Data',
        'campaign_name': 'Campanha',
        'adset_name': 'Conjunto de Anúncios',
        'spend': 'Gasto (R$)',
        'receita_compras': 'Receita (R$)',
        'resultado_lucro': 'Resultado (R$)',
        'roas': 'ROAS',
        'impressions': 'Impressões',
        'reach': 'Alcance',
        'inline_link_clicks': 'Cliques no Link',
        'ctr': 'CTR (%)',
        'cpc': 'CPC (R$)',
        'compras': 'Compras',
        'cpa': 'CPA (R$)',
        'custo_por_visita': 'Custo por Visita (R$)',
        'custo_por_mensagem': 'Custo por Mensagem (R$)'
    }
    
    df_final = df[list(colunas_finais_mapa.keys())].copy()
    df_final.rename(columns=colunas_finais_mapa, inplace=True)

    df_final['Data'] = pd.to_datetime(df_final['Data'])
    mapa_dias = {0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira', 3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'}
    df_final['Dia da Semana'] = df_final['Data'].dt.dayofweek.map(mapa_dias)
    
    for col in df_final.columns:
        if '(R$)' in col or 'ROAS' in col or 'CPA' in col or 'CTR' in col or 'Cliques' in col:
             df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
    
    # Reordenação das colunas
    ordem_colunas = [
        'Cliente', 'Data', 'Dia da Semana', 'Campanha', 'Conjunto de Anúncios',
        'Gasto (R$)', 'Receita (R$)', 'Resultado (R$)', 
        'Compras', 'CPA (R$)',
        'Impressões', 'Alcance', 'CTR (%)', 'CPC (R$)',
        'Custo por Mensagem (R$)', 'Custo por Visita (R$)', 'ROAS', 'Cliques no Link'
    ]
    df_final = df_final[ordem_colunas]
    df_final.drop(columns=['Resultado (R$)', 'Receita (R$)', 'ROAS'], inplace=True)
    
    try:
        df_final.to_csv(caminho_saida, index=False, encoding='utf-8-sig', decimal=',', sep=';')
        logging.info(f"Relatório final e limpo salvo em: {caminho_saida}")
    except Exception as e:
        logging.error(f"Não foi possível salvar o arquivo CSV: {e}")

# --- FUNÇÃO PRINCIPAL ---
def main():
    """Função principal que orquestra todo o pipeline."""
    if not inicializar_api():
        return
        
    MAPA_DE_CLIENTES = getattr(credential, 'MAPA_DE_CLIENTES', None)
    if not MAPA_DE_CLIENTES:
        logging.error("A variável 'MAPA_DE_CLIENTES' não foi encontrada em 'my_credentials.py'.")
        return

    df_bruto = extrair_insights_de_multiplas_contas(MAPA_DE_CLIENTES)
    processar_e_salvar(df_bruto, "relatorio_consolidado_clientes.csv")
    logging.info("Pipeline concluído!")

if __name__ == "__main__":
    main()
