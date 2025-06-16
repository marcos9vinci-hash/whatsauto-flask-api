from flask import Flask, request, jsonify

# Importante: A instância da sua aplicação Flask DEVE ser chamada 'app'
app = Flask(__name__)

# Rota de teste simples para verificar se a API está online
@app.route('/')
def home():
    return "API do Whatsauto rodando! Ponto de entrada padrão."

# Rota para receber as requisições POST do Watsauto
# O Watsauto enviará para esta URL (por exemplo, sua_url_vercel.vercel.app/webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    # Captura os dados JSON enviados pelo Watsauto
    data = request.get_json()

    # Extrai informações importantes do corpo da solicitação (como mostrado na imagem do Watsauto)
    app_name = data.get("app", "Desconhecido")
    sender = data.get("sender", "Desconhecido")
    message_content = data.get("message", "Sem mensagem")
    group_name = data.get("group_name", "Não em grupo")
    phone = data.get("phone", "Desconhecido")

    print(f"Mensagem recebida de {sender} ({phone}) no app {app_name} (Grupo: {group_name}): {message_content}")

    # Lógica para gerar uma resposta
    # Aqui é onde você colocará a inteligência do seu bot
    if "olá" in message_content.lower():
        reply_text = "Olá! Como posso ajudar você hoje?"
    elif "tudo bem" in message_content.lower():
        reply_text = "Estou bem, obrigado! E você?"
    else:
        reply_text = f"Recebi sua mensagem: '{message_content}'. No momento, só respondo a 'olá' e 'tudo bem'."

    # Retorna a resposta no formato JSON esperado pelo Watsauto
    return jsonify({"reply": reply_text})

# IMPORTANTE: Remova ou comente a linha abaixo se ela estiver no seu app.py.
# O Vercel irá gerenciar como sua aplicação é iniciada.
# if __name__ == '__main__':
#     app.run(debug=True)