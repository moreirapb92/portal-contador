# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def alerta_backup(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido."}, status=405)

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)

    token_recebido = dados.get("token", "")
    token_correto = os.getenv("BACKUP_ALERT_TOKEN", "")

    if not token_correto or token_recebido != token_correto:
        return JsonResponse({"ok": False, "erro": "Token inválido."}, status=403)

    cliente = dados.get("cliente", "Cliente não informado")
    email_destino = dados.get("email_destino", "").strip()
    status_backup = dados.get("status", "info")
    banco = dados.get("banco", "")
    arquivo = dados.get("arquivo", "")
    tamanho = dados.get("tamanho", "")
    nuvem = dados.get("nuvem", "")
    etapa = dados.get("etapa", "")
    erro = dados.get("erro", "")
    mensagem_extra = dados.get("mensagem", "")

    if not email_destino:
        return JsonResponse({"ok": False, "erro": "E-mail destino não informado."}, status=400)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if status_backup == "sucesso":
        assunto = f"✅ Backup concluído - {cliente}"
        corpo = f"""Backup concluído com sucesso.

Cliente: {cliente}
Data/hora: {agora}
Banco: {banco}
Arquivo: {arquivo}
Tamanho: {tamanho}
Nuvem: {nuvem}

Status: OK

{mensagem_extra}
"""
    else:
        assunto = f"🚨 ERRO no backup - {cliente}"
        corpo = f"""ERRO NO BACKUP.

Cliente: {cliente}
Data/hora: {agora}
Banco: {banco}
Etapa: {etapa}
Erro: {erro}

Ação necessária: verificar o computador do cliente, internet, rclone ou banco Firebird.

{mensagem_extra}
"""

    destinos = [email_destino]

    copia = os.getenv("BACKUP_ALERT_CC", "").strip()
    if copia:
        destinos.append(copia)

    try:
        send_mail(
            subject=assunto,
            message=corpo,
            from_email=os.getenv("DEFAULT_FROM_EMAIL"),
            recipient_list=destinos,
            fail_silently=False,
        )

        return JsonResponse({
            "ok": True,
            "mensagem": "Alerta enviado por e-mail.",
            "destinos": destinos,
        })

    except Exception as erro_envio:
        return JsonResponse({
            "ok": False,
            "erro": str(erro_envio),
        }, status=500)