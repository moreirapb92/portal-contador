import os
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden


APPS_PROTEGIDOS = {
    "auth",
    "admin",
    "contenttypes",
    "sessions",
    "staticfiles",
}


def limpeza_segura(request):
    token_recebido = request.GET.get("token", "")
    token_correto = os.getenv("CLEANUP_TOKEN", "")

    if not token_correto or token_recebido != token_correto:
        return HttpResponseForbidden("Token inválido.")

    if os.getenv("ENABLE_CLEANUP", "false").lower() != "true":
        return HttpResponseForbidden("Limpeza desativada.")

    confirmar = request.GET.get("confirmar", "").upper() == "SIM"

    UserModel = get_user_model()
    modelos_para_limpar = []

    for model in apps.get_models():
        app_label = model._meta.app_label

        if app_label in APPS_PROTEGIDOS:
            continue

        if model == UserModel:
            continue

        modelos_para_limpar.append(model)

    resultado = []

    if not confirmar:
        for model in modelos_para_limpar:
            try:
                qtd = model.objects.count()
            except Exception as erro:
                qtd = f"erro ao contar: {erro}"

            resultado.append({
                "app": model._meta.app_label,
                "modelo": model.__name__,
                "registros": qtd,
                "acao": "preview"
            })

        return JsonResponse({
            "modo": "PREVIEW",
            "mensagem": "Nada foi apagado ainda. Para apagar, adicione &confirmar=SIM na URL.",
            "modelos": resultado
        }, json_dumps_params={"indent": 2, "ensure_ascii": False})

    with transaction.atomic():
        for model in reversed(modelos_para_limpar):
            try:
                qtd = model.objects.count()
                model.objects.all().delete()

                resultado.append({
                    "app": model._meta.app_label,
                    "modelo": model.__name__,
                    "apagados": qtd,
                    "status": "ok"
                })

            except Exception as erro:
                resultado.append({
                    "app": model._meta.app_label,
                    "modelo": model.__name__,
                    "status": "erro",
                    "erro": str(erro)
                })

    return JsonResponse({
        "modo": "LIMPEZA_EXECUTADA",
        "mensagem": "Limpeza concluída. Agora desative ENABLE_CLEANUP no Render.",
        "resultado": resultado
    }, json_dumps_params={"indent": 2, "ensure_ascii": False})
