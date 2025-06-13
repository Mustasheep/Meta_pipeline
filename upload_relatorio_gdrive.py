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
    Orquestra o processo de LEITURA do CSV e ADIÇÃO dos dados ao final
    da planilha no Google Sheets.
    """
    logging.info("--- Iniciando pipeline de upload para o Google Drive (Modo: Adicionar Dados) ---")
    
    if not os.path.exists(ARQUIVO_CSV_LOCAL):
        logging.error(f"O arquivo de relatório '{ARQUIVO_CSV_LOCAL}' não foi encontrado.")
        return

    logging.info(f"Lendo dados de '{ARQUIVO_CSV_LOCAL}'...")
    df = pd.read_csv(ARQUIVO_CSV_LOCAL)
    df = df.fillna('')
    logging.info(f"{len(df)} novas linhas de dados carregadas.")

    if df.empty:
        logging.warning("O arquivo CSV está vazio. Nenhum dado para adicionar.")
        return

    client = autenticar_e_obter_cliente()
    if not client:
        return

    spreadsheet = obter_ou_criar_planilha(client, NOME_PLANILHA_GOOGLE)
    worksheet = obter_ou_criar_aba(spreadsheet, NOME_DA_ABA)

    # --- LÓGICA DE ADIÇÃO DE DADOS ---
    try:
        # 1. Verifica se a planilha já tem um cabeçalho
        header_existente = worksheet.row_values(1)
    except gspread.exceptions.APIError as e:
        logging.warning(f"Não foi possível ler a primeira linha, assumindo que a planilha está vazia. Erro: {e}")
        header_existente = None
        
    # 2. Converte o DataFrame para uma lista de listas
    dados_para_adicionar = df.values.tolist()

    if not header_existente:
        # 3. Se a planilha está vazia, adiciona o cabeçalho + os dados
        logging.info("Planilha vazia. Adicionando cabeçalho e os novos dados.")
        cabecalho = [df.columns.tolist()]
        worksheet.append_rows(cabecalho + dados_para_adicionar, value_input_option='USER_ENTERED')
    else:
        # 4. Se a planilha já tem dados, adiciona apenas as novas linhas (sem o cabeçalho)
        logging.info("Planilha já contém dados. Adicionando apenas as novas linhas.")
        worksheet.append_rows(dados_para_adicionar, value_input_option='USER_ENTERED')
    
    worksheet.resize(rows=worksheet.row_count)

    logging.info("=" * 50)
    logging.info("UPLOAD (MODO ADICIONAR) CONCLUÍDO COM SUCESSO!")
    logging.info(f"{len(dados_para_adicionar)} linhas foram adicionadas.")
    logging.info(f"Planilha: {spreadsheet.url}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
