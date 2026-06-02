# -*- coding: utf-8 -*-

from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from empresas.models import Empresa
from documentos.models import DocumentoFiscal
from documentos.leitor_xml import ler_xml_nfe


def somente_numeros(valor):
    return "".join(filter(str.isdigit, valor or ""))


@csrf_exempt
@require_POST
def upload_xml_api(request):
    cnpj = somente_numeros(request.POST.get("cnpj", ""))
    token = request.POST.get("token", "").strip()

    arquivo = request.FILES.get("arquivo")

    if not cnpj:
        return JsonResponse({
            "sucesso": False,
            "erro": "CNPJ não informado."
        }, status=400)

    if not token:
        return JsonResponse({
            "sucesso": False,
            "erro": "Token não informado."
        }, status=400)

    if not arquivo:
        return JsonResponse({
            "sucesso": False,
            "erro": "Arquivo XML não enviado."
        }, status=400)

    try:
        empresa = Empresa.objects.get(
            cnpj=cnpj,
            token_api=token,
            ativo=True
        )
    except Empresa.DoesNotExist:
        return JsonResponse({
            "sucesso": False,
            "erro": "CNPJ ou token inválido."
        }, status=403)

    try:
        conteudo = arquivo.read()
        xml_texto = conteudo.decode("utf-8", errors="replace")

        dados = ler_xml_nfe(
            conteudo_xml=conteudo,
            cnpj_empresa=empresa.cnpj
        )

        documento, criado = DocumentoFiscal.objects.update_or_create(
            chave_acesso=dados["chave_acesso"],
            defaults={
                "empresa": empresa,
                "tipo_documento": dados["tipo_documento"],
                "numero": dados["numero"],
                "serie": dados["serie"],
                "natureza": dados["natureza"],
                "data_emissao": dados["data_emissao"],
                "valor_total": dados["valor_total"],
                "situacao": dados["situacao"],
                "emitente_cnpj": dados["emitente_cnpj"],
                "destinatario_cnpj": dados["destinatario_cnpj"],
                "mes": dados["mes"],
                "ano": dados["ano"],
                "xml_conteudo": xml_texto,
            }
        )

        # Mantém também o arquivo físico quando o ambiente permitir.
        # Mas o download principal vai usar xml_conteudo salvo no banco.
        try:
            documento.arquivo_xml.save(
                arquivo.name,
                ContentFile(conteudo),
                save=True
            )
        except Exception:
            pass

        return JsonResponse({
            "sucesso": True,
            "criado": criado,
            "mensagem": "XML importado com sucesso." if criado else "XML já existia e foi atualizado.",
            "empresa": empresa.razao_social,
            "cnpj": empresa.cnpj,
            "tipo_documento": dados["tipo_documento"],
            "numero": dados["numero"],
            "serie": dados["serie"],
            "chave_acesso": dados["chave_acesso"],
            "mes": dados["mes"],
            "ano": dados["ano"],
            "valor_total": str(dados["valor_total"]),
        })

    except Exception as erro:
        return JsonResponse({
            "sucesso": False,
            "erro": str(erro),
            "arquivo": arquivo.name,
        }, status=400)