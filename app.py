from flask import Flask, request, jsonify
import sys
import os # Importar para acessar variáveis de ambiente
import json # Importar para decodificar o JSON das credenciais
from datetime import datetime, timedelta # Para lidar com datas e horas

# Importações para Google Calendar API
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# --- Inicialização do Google Calendar Service (fora da rota) ---
# Isso será executado uma vez quando a aplicação iniciar
try:
    # Carrega as credenciais da variável de ambiente
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not creds_json:
        print("ERRO: Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS_JSON não encontrada!", file=sys.stderr)
        calendar_service = None # Define como None se as credenciais não estiverem presentes
    else:
        # Decodifica a string JSON para um dicionário
        info = json.loads(creds_json)
        
        # Cria as credenciais de serviço
        credentials = service_account.Credentials.from_service_account_info(info)
        
        # Constrói o serviço da API do Google Calendar
        calendar_service = build('calendar', 'v3', credentials=credentials)
        print("Serviço do Google Calendar inicializado com sucesso.", file=sys.stderr)

except Exception as e:
    print(f"ERRO ao inicializar o serviço do Google Calendar: {e}", file=sys.stderr)
    calendar_service = None # Define como None em caso de erro na inicialização
# --- Fim da Inicialização ---


@app.route('/')
def home():
    return "API do Whatsauto rodando! Ponto de entrada padrão."

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Iniciando processamento do webhook para formato customizado...", file=sys.stderr)
    print("Content-Type da requisição:", request.headers.get('Content-Type'), file=sys.stderr)

    try:
        raw_data = request.data.decode('utf-8', 'ignore')
        print("Dados brutos da requisição (decodificado):", raw_data, file=sys.stderr)

        data = {}
        pairs = raw_data.split(',')

        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                data[key] = value

        print("Dados parseados manualmente:", data, file=sys.stderr)

        app_name = data.get("app", "Desconhecido")
        sender = data.get("sender", "Desconhecido")
        message_content = data.get("message", "Sem mensagem")
        group_name = data.get("group_name", "Não em grupo")
        phone = data.get("phone", "Desconhecido")

        print(f"Mensagem recebida de {sender} ({phone}) no app {app_name} (Grupo: {group_name}): {message_content}", file=sys.stderr)

        reply_text = "" # Inicializa a resposta

        # --- Lógica para Agendamento de Eventos ---
        # Exemplo Simples: Se a mensagem contiver "agendar" e "reunião"
        if "agendar" in message_content.lower() and "reunião" in message_content.lower():
            if calendar_service:
                try:
                    # Definir um fuso horário para o evento (importante!)
                    TIME_ZONE = 'America/Sao_Paulo' # Ajuste conforme sua região

                    # Exemplo: Agendar para daqui a 1 hora e durar 30 minutos
                    start_time = datetime.now() + timedelta(hours=1)
                    end_time = start_time + timedelta(minutes=30)
                    
                    event = {
                        'summary': f'Reunião agendada via WhatsAuto com {sender}',
                        'description': message_content,
                        'start': {
                            'dateTime': start_time.isoformat(),
                            'timeZone': TIME_ZONE,
                        },
                        'end': {
                            'dateTime': end_time.isoformat(),
                            'timeZone': TIME_ZONE,
                        },
                        'attendees': [
                            # Adicione convidados se necessário, ex: {'email': 'marcosviniciusdvincistudios@gmail.com'},
                            # Se você quer que a conta de serviço se adicione
                            {'email': 'we-calendar-sa@whatsauto-46281.iam.gserviceaccount.com'} # O email da sua conta de serviço
                        ],
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 24 * 60}, # 24 horas antes
                                {'method': 'popup', 'minutes': 10},    # 10 minutos antes
                            ],
                        },
                    }
                    
                    # ID do calendário onde o evento será criado
                    # Você pode obter isso nas configurações do seu Google Calendar,
                    # geralmente é o seu próprio e-mail (para o calendário principal)
                    calendar_id = 'marcosviniciusdvincistudios@gmail.com' # SEU E-MAIL DO GOOGLE

                    created_event = calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
                    print(f"Evento criado: {created_event.get('htmlLink')}", file=sys.stderr)
                    reply_text = f"Reunião agendada com sucesso! Veja aqui: {created_event.get('htmlLink')}"
                    
                except Exception as calendar_e:
                    print(f"ERRO ao agendar no Google Calendar: {calendar_e}", file=sys.stderr)
                    reply_text = f"Ocorreu um erro ao agendar a reunião: {calendar_e}"
            else:
                reply_text = "Não foi possível agendar. Serviço do Google Calendar não inicializado."
        # --- Fim da Lógica de Agendamento ---
        
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