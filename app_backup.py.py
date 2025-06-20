from flask import Flask, request, jsonify
import sys
import os
import json
from datetime import datetime, timedelta

# Importações para Google Calendar API
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# --- Configurações do Google Calendar ---
# ID do seu calendário principal (geralmente seu e-mail do Google)
CALENDAR_ID = 'marcos9vinciestudos@gmail.com' 
# E-mail da sua conta de serviço (o "client_email" do seu arquivo JSON de credenciais)
SERVICE_ACCOUNT_EMAIL = 'we-calendar-sa@whatsauto-46281.iam.gserviceaccount.com' 
# Fuso horário para os eventos do calendário (São Paulo, Brasil)
TIME_ZONE = 'America/Sao_Paulo' 

# --- Inicialização do Google Calendar Service (executado uma vez ao iniciar a aplicação) ---
calendar_service = None
try:
    # Carrega as credenciais da variável de ambiente GOOGLE_APPLICATION_CREDENTIALS_JSON
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not creds_json:
        print("ERRO: Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS_JSON não encontrada! Agendamento desativado.", file=sys.stderr)
    else:
        # Decodifica a string JSON para um dicionário Python
        info = json.loads(creds_json)
        
        # Cria as credenciais de serviço a partir do dicionário
        credentials = service_account.Credentials.from_service_account_info(info)
        
        # Constrói o serviço da API do Google Calendar
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("Serviço do Google Calendar inicializado com sucesso.", file=sys.stderr)

except Exception as e:
    print(f"ERRO CRÍTICO ao inicializar o serviço do Google Calendar: {e}", file=sys.stderr)
    calendar_service = None 

# --- Rota Padrão da API ---
@app.route('/')
def home():
    return "API do Whatsauto rodando! Ponto de entrada padrão."

# --- Webhook para receber mensagens do Watsauto ---
@app.route('/webhook', methods=['POST'])
def webhook():
    print("Iniciando processamento do webhook...", file=sys.stderr)
    
    try:
        content_type = request.headers.get('Content-Type')
        print("Content-Type da requisição:", content_type, file=sys.stderr)

        data = {}
        if content_type and content_type.startswith('application/json'): # Verifica se começa com, para pegar application/json; charset=UTF-8 também
            # --- Adicionado para depuração ---
            raw_json_data = request.data.decode('utf-8', 'ignore')
            print("Corpo da requisição JSON (RAW):", raw_json_data, file=sys.stderr)
            # --- Fim da depuração ---

            try:
                data = request.json # Tenta parsear como JSON
                if data is None:
                    print("ERRO: request.json retornou None. JSON pode estar vazio ou malformado.", file=sys.stderr)
                    # Se request.json for None, o corpo não era um JSON válido
                    return jsonify({"error": "Corpo da requisição JSON inválido ou vazio"}), 400
                print("Dados parseados como JSON (via request.json):", data, file=sys.stderr)
            except Exception as json_e:
                print(f"ERRO ao parsear JSON com request.json: {json_e}", file=sys.stderr)
                # Tenta parsear manualmente se request.json falhar, como fallback extremo
                try:
                    data = json.loads(raw_json_data)
                    print("Dados parseados manualmente via json.loads (fallback):", data, file=sys.stderr)
                except Exception as fallback_e:
                    print(f"ERRO CRÍTICO: Falha no parseamento JSON automático e manual: {fallback_e}", file=sys.stderr)
                    return jsonify({"error": "Corpo da requisição JSON inválido"}), 400
        else:
            # Caso contrário (ex: application/x-www-form-urlencoded), tenta o parseamento manual de key=value,key=value
            raw_data = request.data.decode('utf-8', 'ignore')
            print("Dados brutos da requisição (decodificado, não-JSON):", raw_data, file=sys.stderr)
            pairs = raw_data.split(',')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    data[key] = value
            print("Dados parseados manualmente (não-JSON):", data, file=sys.stderr)

        # Extrai informações dos dados parseados
        app_name = data.get("app", "Desconhecido")
        sender = data.get("sender", "Desconhecido")
        message_content = data.get("message", data.get("Message", "Sem mensagem")) # Tenta 'message' ou 'Message'
        group_name = data.get("group_name", "Não em grupo")
        phone = data.get("phone", "Desconhecido")

        print(f"Mensagem recebida de {sender} ({phone}) no app {app_name} (Grupo: {group_name}): {message_content}", file=sys.stderr)

        reply_text = "" 

        # --- Lógica de Resposta e Agendamento ---
        if "agendar" in message_content.lower() and "reuniao" in message_content.lower():
            if calendar_service:
                try:
                    start_time = datetime.now() + timedelta(hours=1)
                    end_time = start_time + timedelta(minutes=30)
                    
                    event = {
                        'summary': f'Reunião agendada via WhatsAuto com {sender}',
                        'description': f'Mensagem original: {message_content}',
                        'start': {
                            'dateTime': start_time.isoformat(),
                            'timeZone': TIME_ZONE,
                        },
                        'end': {
                            'dateTime': end_time.isoformat(),
                            'timeZone': TIME_ZONE,
                        },
                        'attendees': [
                            {'email': SERVICE_ACCOUNT_EMAIL}
                        ],
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 24 * 60},
                                {'method': 'popup', 'minutes': 10},
                            ],
                        },
                    }
                    
                    created_event = calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
                    print(f"Evento criado: {created_event.get('htmlLink')}", file=sys.stderr)
                    reply_text = f"Reunião agendada com sucesso! Veja aqui: {created_event.get('htmlLink')}"
                    
                except Exception as calendar_e:
                    print(f"ERRO ao agendar no Google Calendar: {calendar_e}", file=sys.stderr)
                    reply_text = f"Ocorreu um erro ao agendar a reunião: {calendar_e}. Por favor, verifique as permissões do calendário e o ID."
            else:
                reply_text = "Não foi possível agendar. O serviço do Google Calendar não foi inicializado corretamente."
        
        elif "olá" in message_content.lower():
            reply_text = "Olá! Como posso ajudar você hoje?"
        elif "tudo bem" in message_content.lower():
            reply_text = "Estou bem, obrigado! E você?"
        else:
            reply_text = f"Recebi sua mensagem: '{message_content}'. No momento, só respondo a 'olá', 'tudo bem' e posso tentar 'agendar reunião'."

        print(f"Respondendo com: {reply_text}", file=sys.stderr)
        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"ERRO CRÍTICO NO WEBHOOK (exceção geral): {e}", file=sys.stderr)
        error_details = str(e)
        return jsonify({"error": "Erro interno do servidor ao processar mensagem", "details": error_details}), 500

if __name__ == '__main__':
    app.run(debug=True)