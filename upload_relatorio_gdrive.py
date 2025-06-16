import pandas as pd
import gspread
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- CONFIGURAÇÕES ---
ARQUIVO_CSV_LOCAL = "relatorio_consolidado_clientes.csv"
ARQUIVO_CREDENCIAL_GCP = "gcp_credentials.json"
NOME_PLANILHA_GOOGLE = "Relatório Consolidado de Anúncios Meta"
NOME_DA_ABA = "Dados Gerais"

# Colunas que serão usadas para verificar duplicatas
COLUNAS_CHAVE_UNICA = ['Cliente', 'Data']


def autenticar_e_obter_cliente() -> gspread.Client:
    """Autentica na API do Google usando a conta de serviço e retorna o cliente."""
    try:
        logging.info("Autenticando com a API do Google...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        client = gspread.service_account(filename=ARQUIVO_CREDENCIAL_GCP, scopes=scopes)
        logging.info("Autenticação bem-sucedida!")
        return client
    except FileNotFoundError:
        logging.critical(f"ERRO: Arquivo de credenciais '{ARQUIVO_CREDENCIAL_GCP}' não encontrado.")
        return None
    except Exception as e:
        logging.critical(f"Falha na autenticação: {e}")
        return None

def obter_ou_criar_planilha(client: gspread.Client, nome_planilha: str) -> gspread.Spreadsheet:
    """Tenta abrir uma planilha pelo nome. Se não existir, cria e compartilha."""
    try:
        logging.info(f"Abrindo a planilha '{nome_planilha}'...")
        spreadsheet = client.open(nome_planilha)
        logging.info("Planilha encontrada.")
        return spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        logging.warning(f"Planilha '{nome_planilha}' não encontrada. Criando uma nova...")
        spreadsheet = client.create(nome_planilha)
        spreadsheet.share('thiagoassis.escritorio@gmail.com', perm_type='user', role='writer')
        logging.info(f"Planilha '{nome_planilha}' criada e compartilhada com você com sucesso.")
        return spreadsheet

def obter_ou_criar_aba(spreadsheet: gspread.Spreadsheet, nome_aba: str) -> gspread.Worksheet:
    """Tenta selecionar uma aba pelo nome. Se não existir, cria uma nova."""
    try:
        worksheet = spreadsheet.worksheet(nome_aba)
        logging.info(f"Aba '{nome_aba}' selecionada.")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        logging.warning(f"Aba '{nome_aba}' não encontrada. Criando uma nova...")
        worksheet = spreadsheet.add_worksheet(title=nome_aba, rows="1", cols="1")
        try:
            default_sheet = spreadsheet.worksheet('Página1')
            if default_sheet.id != worksheet.id:
                spreadsheet.del_worksheet(default_sheet)
        except gspread.exceptions.WorksheetNotFound:
            pass
        return worksheet

def main():
    """
    Orquestra o processo de leitura do CSV, verificação de duplicatas e
    adição apenas de dados novos ao Google Sheets.
    """
    logging.info("--- Iniciando pipeline de upload para o Google Drive (Modo: Adicionar Novos Dados) ---")
    
    if not os.path.exists(ARQUIVO_CSV_LOCAL):
        logging.error(f"O arquivo de relatório '{ARQUIVO_CSV_LOCAL}' não foi encontrado.")
        return

    logging.info(f"Lendo dados de '{ARQUIVO_CSV_LOCAL}'...")
    df_novo = pd.read_csv(ARQUIVO_CSV_LOCAL)
    df_novo = df_novo.fillna('')
    logging.info(f"{len(df_novo)} linhas de dados carregadas do CSV.")

    if df_novo.empty:
        logging.warning("O arquivo CSV está vazio. Nenhum dado para adicionar.")
        return

    client = autenticar_e_obter_cliente()
    if not client:
        return

    spreadsheet = obter_ou_criar_planilha(client, NOME_PLANILHA_GOOGLE)
    worksheet = obter_ou_criar_aba(spreadsheet, NOME_DA_ABA)

    # --- LÓGICA DE VERIFICAÇÃO DE DUPLICATAS ---
    try:
        logging.info("Lendo dados existentes da planilha para evitar duplicatas...")
        dados_existentes = worksheet.get_all_records()
        header_presente = True if dados_existentes else False
    except gspread.exceptions.APIError as e:
        logging.warning(f"Não foi possível ler a planilha, assumindo que está vazia. Erro: {e}")
        dados_existentes = []
        header_presente = False

    if not header_presente:
        # Se vazia, preenche a planilha
        logging.info("Planilha vazia. Adicionando cabeçalho e os novos dados.")
        cabecalho = [df_novo.columns.tolist()]
        dados_para_adicionar = df_novo.values.tolist()
        worksheet.append_rows(cabecalho + dados_para_adicionar, value_input_option='USER_ENTERED')

    else:
        logging.info("Planilha já contém dados. Verificando por linhas duplicadas...")
        df_existente = pd.DataFrame(dados_existentes)

        # Garante que as colunas-chave existam em ambos os dataframes
        for col in COLUNAS_CHAVE_UNICA:
            if col not in df_novo.columns:
                logging.error(f"Erro: A coluna-chave '{col}' não foi encontrada no arquivo CSV.")
                return
            if col not in df_existente.columns:
                logging.error(f"Erro: A coluna-chave '{col}' não foi encontrada na planilha do Google Sheets.")
                return

        df_novo['chave_unica'] = df_novo[COLUNAS_CHAVE_UNICA].astype(str).agg('_'.join, axis=1)
        df_existente['chave_unica'] = df_existente[COLUNAS_CHAVE_UNICA].astype(str).agg('_'.join, axis=1)
        chaves_existentes = set(df_existente['chave_unica'])
        df_filtrado = df_novo[~df_novo['chave_unica'].isin(chaves_existentes)]
        df_para_adicionar = df_filtrado.drop(columns=['chave_unica'])
        if df_para_adicionar.empty:
            logging.info("Nenhuma linha nova para adicionar. Os dados já estão atualizados.")
            return

        logging.info(f"Encontradas {len(df_para_adicionar)} novas linhas para adicionar.")
        dados_para_adicionar = df_para_adicionar.values.tolist()
        worksheet.append_rows(dados_para_adicionar, value_input_option='USER_ENTERED')

    logging.info("=" * 50)
    logging.info("UPLOAD (MODO ADICIONAR NOVOS DADOS) CONCLUÍDO COM SUCESSO!")
    logging.info(f"{len(dados_para_adicionar)} novas linhas foram adicionadas.")
    logging.info(f"Planilha: {spreadsheet.url}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()