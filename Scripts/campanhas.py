# Bibliotecas necessárias
import os
import pandas as pd
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError

# Importando credenciais
import my_credentials as credential

# --- Bloco de Configuração de Credenciais ---
try:
    my_app_id = credential.APP_ID
    my_app_secret = credential.APP_SECRET
    my_access_token = credential.ACCESS_TOKEN
    my_ad_account_id = credential.AD_ACCOUNT_ID

    # Verifica se todas as credenciais foram carregadas
    if not all([my_app_id, my_app_secret, my_access_token, my_ad_account_id]):
        print("Erro: Verifique se todas as credenciais (APP_ID, APP_SECRET, ACCESS_TOKEN, AD_ACCOUNT_ID) estão definidas corretamente no arquivo my_credentials.py.")
        exit()
except AttributeError:
    print("Erro: Uma ou mais constantes de credenciais (APP_ID, APP_SECRET, ACCESS_TOKEN, AD_ACCOUNT_ID) não foram encontradas no arquivo my_credentials.py.")
    exit()
except Exception as e:
    print(f"Erro ao carregar credenciais do arquivo my_credentials.py: {e}")
    exit()

# --- Inicialização da API ---
try:
    FacebookAdsApi.init(app_id=my_app_id, app_secret=my_app_secret, access_token=my_access_token)
    print("API Inicializada com sucesso!")
except FacebookRequestError as e:
    print(f"Erro ao inicializar a API: {e}")
    exit()

# --- Buscando Campanhas ---
try:
    account = AdAccount(fbid=my_ad_account_id)
    
    campaign_fields = [
        'id', 'name', 'status', 'effective_status', 'objective',
        'created_time', 'start_time', 'stop_time', 'spend_cap',
        'daily_budget', 'lifetime_budget'
    ]
    
    print(f"\nBuscando campanhas para a conta: {my_ad_account_id}...")
    campaigns_data = account.get_campaigns(fields=campaign_fields)

    campaigns_list = []
    for campaign in campaigns_data:
        campaign_dict = {field: campaign.get(field) for field in campaign_fields}
        campaigns_list.append(campaign_dict)

    if campaigns_list:
        df_campaigns = pd.DataFrame(campaigns_list)
        print("\nCampanhas encontradas com sucesso. DataFrame em 'df_campaigns'.")
    else:
        print("Nenhuma campanha encontrada.")

except FacebookRequestError as e:
    print(f"Erro ao buscar campanhas: {e}")
    print(f"Detalhes do erro: Código: {e.api_error_code()}, Mensagem: {e.api_error_message()}")
except Exception as e:
    print(f"Um erro inesperado ocorreu: {e}")

# --- Buscando Insights ---
try:
    account = AdAccount(fbid=my_ad_account_id)
    
    insight_fields = [
        'campaign_name',
        'campaign_id',
        'spend',
        'inline_link_clicks',
        'impressions',
        'ctr', 
        'cpc' 
    ]
    
    insight_params = {
        'level': 'campaign',
        'date_preset': 'last_7d',
        'time_increment': 1,
        'breakdowns': ['publisher_platform'],
        'filtering': [{'field': 'campaign.effective_status', 'operator': 'IN', 'value': ['ACTIVE']}]
    }

    print(f"\nBuscando insights para a conta: {my_ad_account_id}...")
    insights_cursor = account.get_insights(fields=insight_fields, params=insight_params)
    
    insights_list = []
    for insight in insights_cursor:
        insights_list.append(dict(insight)) 

    if insights_list:
        df_insights = pd.DataFrame(insights_list)
        print("\nInsights encontrados. DataFrame em 'df_insights'.")
        
        cols_to_numeric = ['spend', 'inline_link_clicks', 'impressions', 'ctr', 'cpc']
        for col in cols_to_numeric:
            if col in df_insights.columns:
                df_insights[col] = pd.to_numeric(df_insights[col], errors='coerce')

        # df_insights.to_csv('insights_campanhas_por_plataforma.csv', index=False)
        # print("\nDados de insights salvos em 'insights_campanhas_por_plataforma.csv'")
    else:
        print("Nenhum insight encontrado com os critérios especificados.")

except FacebookRequestError as e:
    print(f"Erro ao buscar insights: {e}")
    print(f"Detalhes do erro: Código: {e.api_error_code()}, Mensagem: {e.api_error_message()}")
except Exception as e:
    print(f"Um erro inesperado ocorreu: {e}")
