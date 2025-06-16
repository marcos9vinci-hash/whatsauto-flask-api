from flask import Flask, request, jsonify
import sys # Adicione esta linha

app = Flask(__name__)

@app.route('/')
def home():
    return "API do Whatsauto rodando! Ponto de entrada padrão."

@app.route('/webhook', methods=['POST'])
def webhook():
    # Adicione este log para ver o Content-Type real antes de tentar get_json()
    print("Content-Type da requisição:", request.headers.get('Content-Type'), file=sys.stderr)
    print("Dados brutos da requisição:", request.data.decode('utf-8', 'ignore'), file=sys.stderr)

    try:
        data = request.get_json(silent=True) # Use silent=True para evitar erro se não for JSON válido
        if data is None:
            print("ERRO: request.get_json() retornou None. Provavelmente JSON inválido ou vazio.", file=sys.stderr)
            # Tente decodificar manualmente se get_json falhou
            try:
                import json
                raw_data = request.data.decode('utf-8')
                data = json.loads(raw_data)
                print("JSON decodificado manualmente com sucesso:", data, file=sys.stderr)
            except Exception as json_err:
                print(f"ERRO: Não foi possível decodificar JSON manualmente: {json_err}", file=sys.stderr)
                return jsonify({"error": "Dados JSON inválidos ou não fornecidos", "details": str(json_err)}), 400

        # Se chegamos aqui, 'data' deveria ser um dicionário (mesmo que vazio)
        print("Dados JSON processados (get_json ou manual):", data, file=sys.stderr)

        # Extrai informações importantes do corpo da solicitação
        app_name = data.get("app", "Desconhecido")
        sender = data.get("sender", "Desconhecido")
        message_content = data.get("message", "Sem mensagem")
        group_name = data.get("group_name", "Não em grupo")
        phone = data.get("phone", "Desconhecido")

        print(f"Mensagem recebida de {sender} ({phone}) no app {app_name} (Grupo: {group_name}): {message_content}", file=sys.stderr)

        # Lógica para gerar uma resposta
        if "olá" in message_content.lower():
            reply_text = "Olá! Como posso ajudar você hoje?"
        elif "tudo bem" in message_content.lower():
            reply_text = "Estou bem, obrigado! E você?"
        else:
            reply_text = f"Recebi sua mensagem: '{message_content}'. No momento, só respondo a 'olá' e 'tudo bem'."

        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"ERRO CRÍTICO no webhook (exceção geral): {e}", file=sys.stderr)
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500