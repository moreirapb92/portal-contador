# -*- coding: utf-8 -*-

import json
import os
import traceback
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def alerta_backup(request):
    try:
        if request.method != "POST":
            return JsonResponse({
                "ok": False,
                "erro": "Metodo nao permitido."
            }, status=405)

        try:
            dados = json.loads(request.body.decode("utf-8"))
        except Exception as erro_json:
            return JsonResponse({
                "ok": False,
                "erro": "JSON invalido.",
                "detalhe": str(erro_json)
            }, status=400)

        token_recebido = dados.get("token", "")
        token_correto = os.getenv("BACKUP_ALERT_TOKEN", "")

        if not token_correto:
            return JsonResponse({
                "ok": False,
                "erro": "BACKUP_ALERT_TOKEN nao configurado no servidor."
            }, status=500)

        if token_recebido != token_correto:
            return JsonResponse({
                "ok": False,
                "erro": "Token invalido."
            }, status=403)

        cliente = dados.get("cliente", "Cliente nao informado")
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
            return JsonResponse({
                "ok": False,
                "erro": "E-mail destino nao informado."
            }, status=400)

        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if status_backup == "sucesso":
            assunto = f"Backup concluido - {cliente}"
            corpo = f"""Backup concluido com sucesso.

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
            assunto = f"ERRO no backup - {cliente}"
            corpo = f"""ERRO NO BACKUP.

Cliente: {cliente}
Data/hora: {agora}
Banco: {banco}
Etapa: {etapa}
Erro: {erro}

Acao necessaria: verificar o computador do cliente, internet, rclone ou banco Firebird.

{mensagem_extra}
"""

        destinos = [email_destino]

        copia = os.getenv("BACKUP_ALERT_CC", "").strip()
        if copia and copia not in destinos:
            destinos.append(copia)

        from_email = os.getenv("DEFAULT_FROM_EMAIL") or getattr(settings, "DEFAULT_FROM_EMAIL", "")

        if not from_email:
            return JsonResponse({
                "ok": False,
                "erro": "DEFAULT_FROM_EMAIL nao configurado."
            }, status=500)

        try:
            send_mail(
                subject=assunto,
                message=corpo,
                from_email=from_email,
                recipient_list=destinos,
                fail_silently=False,
            )

            return JsonResponse({
                "ok": True,
                "mensagem": "Alerta enviado por e-mail.",
                "destinos": destinos,
                "from_email": from_email
            })

        except Exception as erro_email:
            return JsonResponse({
                "ok": False,
                "erro": "Falha ao enviar e-mail.",
                "detalhe": str(erro_email),
                "email_host": os.getenv("EMAIL_HOST", ""),
                "email_port": os.getenv("EMAIL_PORT", ""),
                "email_user": os.getenv("EMAIL_HOST_USER", ""),
                "from_email": from_email
            }, status=500)

    except Exception as erro_geral:
        return JsonResponse({
            "ok": False,
            "erro": "Erro geral na API alerta-backup.",
            "detalhe": str(erro_geral),
            "traceback": traceback.format_exc()
        }, status=500)
