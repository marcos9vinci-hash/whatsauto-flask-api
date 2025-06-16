# app.py
# Atualizado para forçar redeploy no Vercel e garantir leitura de variável de ambiente.

import os
from flask import Flask, request, jsonify
import logging
from urllib.parse import parse_qs
import json
import pytz
from datetime import datetime, timedelta

# Importações para o Google Calendar API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Variáveis Globais para o Google Calendar (serão inicializadas uma vez)
# Usaremos None e inicializaremos no primeiro uso bem-sucedido ou na primeira tentativa
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'marcosvinicius.hash@gmail.com' # ID do calendário principal ou o que você quer agendar
service = None # O objeto de serviço do Google Calendar

def initialize_google_calendar_service():
    """
    Inicializa o serviço da API do Google Calendar usando as credenciais da variável de ambiente.
    Esta função tenta ler o JSON da variável de ambiente e construir o serviço.
    """
    global service
    if service:
        return service # Já inicializado

    try:
        creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if not creds_json_str:
            logging.error("ERRO: Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS_JSON NÃO ENCONTRADA no Vercel! Agendamento desativado.")
            return None

        logging.info("Variável GOOGLE_APPLICATION_CREDENTIALS_JSON foi lida do ambiente. Tentando carregar JSON e inicializar serviço...")
        
        # O JSON que vem da variável de ambiente Vercel pode precisar de aspas internas escapadas
        # ou ser um JSON direto, então tentamos carregar
        
        # Substituir '\n' por '\n' real para chaves privadas
        creds_json_str = creds_json_str.replace('\\n', '\n')
        
        creds_info = json.loads(creds_json_str)

        # Usar as informações para criar as credenciais do Service Account
        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=creds)
        logging.info("Serviço do Google Calendar inicializado com sucesso.")
        return service

    except json.JSONDecodeError as e:
        logging.error(f"ERRO: Variável GOOGLE_APPLICATION_CREDENTIALS_JSON NÃO É UM JSON VÁLIDO: {e}")
        return None
    except HttpError as e:
        logging.error(f"ERRO: Falha ao criar credenciais ou construir serviço do Google Calendar (HttpError): {e}")
        # Detalhes específicos de HttpError
        if e.resp.status == 403:
            logging.error("VERIFIQUE: Permissões insuficientes para a conta de serviço no Google Calendar.")
        return None
    except Exception as e:
        logging.error(f"ERRO INESPERADO ao inicializar Google Calendar: {e}")
        return None

def extract_message_content(request_data):
    """
    Extrai o conteúdo da mensagem da requisição, priorizando 'message' no payload de formulário.
    """
    if request_data.content_type == 'application/json':
        try:
            data = request_data.json
            return data.get('message', '').strip()
        except Exception:
            # Se request.json falhar, tenta parsear como form-urlencoded
            pass
            
    # Tenta parsear como x-www-form-urlencoded
    # Isso é comum para webhooks de WhatsApp Business API, Twilio, etc.
    raw_data = request_data.get_data(as_text=True)
    logging.info(f"Corpo da requisição (RAW): {raw_data}")
    
    # parse_qs retorna um dicionário de listas, pegamos o primeiro item
    data_dict = parse_qs(raw_data)
    logging.info(f"Dicionário 'data' APÓS parsing FINAL com parse_qs: {data_dict}")

    message_content_list = data_dict.get('message')
    if message_content_list:
        return message_content_list[0].strip()
    
    return ""


@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info("Iniciando processamento do webhook...")
    logging.info(f"Content-Type da requisição: {request.content_type}")

    message_content = extract_message_content(request)
    logging.info(f"message_content final (após strip): '{message_content}'")

    sender = "Cliente" # Valor padrão
    phone = "Não informado"
    app_name = "App Desconhecido"

    # Tentativa de extrair sender, phone, app a partir dos dados parseados
    # Se extract_message_content usou parse_qs, os dados estarão em request.form ou raw_data
    if request.content_type == 'application/json':
        try:
            data = request.json
            sender = data.get('sender', 'Cliente')
            phone = data.get('phone', 'Não informado')
            app_name = data.get('app', 'App Desconhecido')
        except Exception:
            logging.warning("Aviso: request.json falhou ao parsear JSON, mas os dados brutos foram processados.")
            # Fallback para dados de formulário se JSON falhar
            sender = request.form.get('sender', 'Cliente')
            phone = request.form.get('phone', 'Não informado')
            app_name = request.form.get('app', 'App Desconhecido')
    else: # Provavelmente x-www-form-urlencoded
        sender = request.form.get('sender', 'Cliente')
        phone = request.form.get('phone', 'Não informado')
        app_name = request.form.get('app', 'App Desconhecido')
    
    # Para o caso do webhook ter a informação de grupo
    group_info = "" # Por enquanto, assumimos que não está em grupo. Ajuste conforme seu webhook envia.

    logging.info(f"Mensagem recebida de {sender} ({phone}) no app {app_name} (Grupo: {group_info}): {message_content}")

    # Processamento da mensagem
    if message_content.lower() == 'olá':
        reply_text = f"Olá {sender}! Como posso ajudar?"
    elif message_content.lower() == 'tudo bem':
        reply_text = "Tudo ótimo, obrigado! E com você?"
    elif 'agendar reunião' in message_content.lower():
        reply_text = "Ok! Você pediu para agendar uma reunião. Posso fazer isso para 'amanhã' ou 'hoje'. Qual dia você prefere?"
        
        # Tentar agendar se a palavra "amanhã" ou "hoje" estiver presente
        if 'amanhã' in message_content.lower():
            return schedule_meeting(message_content, sender, phone, "amanha") # Passa o termo para o agendador
        elif 'hoje' in message_content.lower():
            return schedule_meeting(message_content, sender, phone, "hoje") # Passa o termo para o agendador
        else:
            reply_text = "Para agendar, por favor, especifique 'amanhã' ou 'hoje'."

    else:
        reply_text = f"Recebi sua mensagem: '{message_content}'. No momento, só respondo a 'olá', 'tudo bem' e posso tentar 'agendar reunião'."

    logging.info(f"Respondendo com: {reply_text}")
    return jsonify({"reply": reply_text})

def schedule_meeting(message_content, sender, phone, day_of_week):
    """
    Função para agendar reunião no Google Calendar.
    """
    global service
    service = initialize_google_calendar_service() # Tenta inicializar o serviço
    
    if not service:
        # Se o serviço não foi inicializado (por erro de credenciais, etc.)
        return jsonify({"reply": "Não foi possível agendar. O serviço do Google Calendar não foi inicializado corretamente."})

    try:
        # Definir fuso horário para São Paulo
        tz = pytz.timezone('America/Sao_Paulo')
        
        now = datetime.now(tz)
        
        if day_of_week == "amanha":
            start_time = now + timedelta(days=1)
            # Definir um horário padrão para a reunião de amanhã, por exemplo, 10:00 da manhã
            start_time = tz.localize(datetime(start_time.year, start_time.month, start_time.day, 10, 0, 0))
        elif day_of_week == "hoje":
            # Definir um horário padrão para a reunião de hoje, por exemplo, 2 horas a partir de agora
            start_time = now + timedelta(hours=2)
            # Arredondar para o próximo bloco de 30 minutos
            start_time = start_time.replace(minute=(start_time.minute // 30) * 30, second=0, microsecond=0)
        else:
            return jsonify({"reply": "Não entendi a data do agendamento. Por favor, diga 'hoje' ou 'amanhã'."})


        end_time = start_time + timedelta(minutes=30) # Reunião de 30 minutos

        event = {
            'summary': f'Reunião com {sender} ({phone})',
            'description': f'Agendado via Watsauto-Flask-API. Mensagem original: "{message_content}"',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'attendees': [
                {'email': 'marcos9vinciestudos@gmail.com'}, # Email do participante da reunião
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60}, # 24 horas antes
                    {'method': 'popup', 'minutes': 10}, # 10 minutos antes
                ],
            },
        }

        # Insere o evento no calendário
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logging.info(f"Evento criado: {event.get('htmlLink')}")
        
        formatted_start_time = start_time.strftime('%d/%m/%Y às %H:%M')
        return jsonify({"reply": f"Reunião agendada com sucesso para {formatted_start_time}. Veja aqui: {event.get('htmlLink')}"})

    except HttpError as error:
        logging.error(f'Ocorreu um erro na API do Google Calendar: {error}')
        # Verifique erros específicos, como 403 (permissões), 404 (calendário não encontrado)
        if error.resp.status == 403:
            return jsonify({"reply": "Não foi possível agendar. Verifique as permissões da conta de serviço no Google Calendar."})
        elif error.resp.status == 404:
            return jsonify({"reply": "Não foi possível agendar. O ID do calendário especificado não foi encontrado."})
        else:
            return jsonify({"reply": "Não foi possível agendar a reunião devido a um erro no serviço de calendário."})
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado ao agendar a reunião: {e}")
        return jsonify({"reply": "Não foi possível agendar a reunião devido a um erro inesperado."})


if __name__ == '__main__':
    # Em ambiente de produção Vercel, o Gunicorn ou equivalente inicia a aplicação
    # Esta parte é mais para testar localmente
    app.run(debug=True)