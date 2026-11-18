import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Credenciais essenciais via Variáveis de Ambiente
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Validação rápida para garantir que as variáveis críticas foram configuradas
if not all([VERIFY_TOKEN, META_ACCESS_TOKEN, TELEGRAM_TOKEN, CHAT_ID]):
  print(
      "⚠️ ATENÇÃO: Alguma variável de ambiente essencial (VERIFY_TOKEN,"
      " META_ACCESS_TOKEN, TELEGRAM_TOKEN, CHAT_ID) não foi definida!"
  )


@app.route("/webhook", methods=["GET"])
def verify_webhook():
  """Etapa 1: Validação do Webhook exigida pela Meta."""
  mode = request.args.get("hub.mode")
  token = request.args.get("hub.verify_token")
  challenge = request.args.get("hub.challenge")

  if mode and token:
    if mode == "subscribe" and token == VERIFY_TOKEN:
      print("WEBHOOK_VERIFIED")
      return challenge, 200
    else:
      return "Verification failed", 403
  return "Bad request", 400


@app.route("/webhook", methods=["POST"])
def receive_lead():
  """Etapa 2: Recebimento do evento de Lead Ads."""
  data = request.json
  print("Payload recebido:", data)

  try:
    if data.get("object") == "page":
      for entry in data.get("entry", []):
        for change in entry.get("changes", []):
          if change.get("field") == "leadgen":
            lead_data = change.get("value", {})
            lead_id = lead_data.get("leadgen_id")

            # Busca os dados reais do lead na Graph API da Meta
            lead_info = fetch_lead_details(lead_id)

            # Envia a notificação via Telegram
            send_telegram_notification(lead_info)

      return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 404
  except Exception as e:
    print(f"Erro ao processar webhook: {e}")
    return jsonify({"status": "error", "message": str(e)}), 500


def fetch_lead_details(lead_id):
  """Busca os dados preenchidos no formulário através da Graph API da Meta."""
  # Interceptador opcional para testes manuais no painel do Meta Ads
  if str(lead_id) == "444444444444":
    return {
        "form_id": "form_teste_mock",
        "field_data": [
            {"name": "full_name", "values": ["Cliente Teste Webhook"]},
            {"name": "phone_number", "values": ["+5511999999999"]},
            {"name": "email", "values": ["teste@exemplo.com"]},
        ],
    }

  url = f"https://graph.facebook.com/v21.0/{lead_id}"
  headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  return response.json()


def send_telegram_notification(lead_info):
  """Dispara a notificação formatada via Bot do Telegram."""
  field_data = {
      item["name"]: item["values"][0] for item in lead_info.get("field_data", [])
  }
  nome = field_data.get("full_name", "Não informado")
  telefone = field_data.get("phone_number", "Não informado")
  email = field_data.get("email", "Não informado")

  mensagem = (
      f"🚨 *Novo Lead Capturado!*\n\n"
      f"👤 *Nome:* {nome}\n"
      f"📞 *Telefone:* {telefone}\n"
      f"✉️ *E-mail:* {email}\n"
      f"🔗 *Form ID:* {lead_info.get('form_id')}"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}

  response = requests.post(url, json=payload)
  response.raise_for_status()
  print("Notificação enviada com sucesso no Telegram!")


if __name__ == "__main__":
  app.run(port=5000, debug=True)