from flask import Flask, request, jsonify
import sys
# import json # Não precisamos mais importar json para decodificar, mas vamos manter por enquanto

app = Flask(__name__)

@app.route('/')
def home():
    return "API do Whatsauto rodando! Ponto de entrada padrão."

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Iniciando processamento do webhook (nova versão)...", file=sys.stderr)
    print("Content-Type da requisição:", request.headers.get('Content-Type'), file=sys.stderr)

    try:
        # AQUI É A MUDANÇA PRINCIPAL: Usamos request.form para acessar dados de formulário
        # O Watsauto está enviando como form-data, não JSON, apesar do Content-Type
        data = {}
        # As chaves parecem vir separadas por vírgula no log, vamos precisar parsear manualmente
        # pois request.form espera 'key=value&key=value' e o Watsauto envia 'key=value, key=value'
        
        raw_string = request.data.decode('utf-8', 'ignore')
        print("Dados brutos (formato Watsauto):", raw_string, file=sys.stderr)
        
        # Vamos tentar parsear a string manualmente, dividindo por ', '
        parts = raw_string.split(', ')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                data[key.strip()] = value.strip()
        
        print("Dados PARSEADOS (dicionário):", data, file=sys.stderr)

        # Se 'data' ainda estiver vazio após a tentativa de parsing, algo está errado
        if not data:
            print("ERRO: Nenhum dado válido foi parseado da requisição.", file=sys.stderr)
            return jsonify({"error": "Nenhum dado válido enviado pelo Watsauto"}), 400

        # Extrai informações importantes do corpo da solicitação
        # Agora usando .get no dicionário 'data'
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

        print(f"Respondendo com: {reply_text}", file=sys.stderr)
        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"ERRO CRÍTICO NO WEBHOOK (exceção geral): {e}", file=sys.stderr)
        return jsonify({"error": "Erro interno do servidor", "details": str(e)}), 500
    # Isso é um comentário para forçar um novo deploy