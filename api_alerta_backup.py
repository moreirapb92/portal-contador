# -*- coding: utf-8 -*-

import json
import os
import traceback
import urllib.request
import urllib.error
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def enviar_email_resend(para, assunto, corpo):
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    remetente = os.getenv("RESEND_FROM", "JMSolucoes Backup <onboarding@resend.dev>").strip()

    if not api_key:
        return False, {
            "erro": "RESEND_API_KEY nao configurado no servidor."
        }

    payload = {
        "from": remetente,
        "to": para,
        "subject": assunto,
        "text": corpo,
    }

    dados = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=dados,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resposta = resp.read().decode("utf-8", errors="ignore")
            return True, json.loads(resposta) if resposta else {}

    except urllib.error.HTTPError as erro_http:
        detalhe = erro_http.read().decode("utf-8", errors="ignore")
        return False, {
            "erro": f"HTTP {erro_http.code}",
            "detalhe": detalhe,
        }

    except Exception as erro:
        return False, {
            "erro": str(erro),
        }


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

        ok, resposta = enviar_email_resend(destinos, assunto, corpo)

        if not ok:
            return JsonResponse({
                "ok": False,
                "erro": "Falha ao enviar e-mail pelo Resend.",
                "resposta": resposta,
                "destinos": destinos,
                "from": os.getenv("RESEND_FROM", "")
            }, status=500)

        return JsonResponse({
            "ok": True,
            "mensagem": "Alerta enviado por e-mail pelo Resend.",
            "destinos": destinos,
            "resposta": resposta,
        })

    except Exception as erro_geral:
        return JsonResponse({
            "ok": False,
            "erro": "Erro geral na API alerta-backup.",
            "detalhe": str(erro_geral),
            "traceback": traceback.format_exc()
        }, status=500)
