# -*- coding: utf-8 -*-

import os
import zipfile
from datetime import date
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from empresas.models import Empresa, UsuarioEmpresa
from documentos.models import DocumentoFiscal
from documentos.leitor_xml import ler_xml_nfe


def empresas_do_usuario(usuario):
    if usuario.is_superuser or usuario.is_staff:
        return Empresa.objects.filter(ativo=True)

    vinculos = UsuarioEmpresa.objects.filter(
        usuario=usuario,
        ativo=True,
        empresa__ativo=True
    ).select_related("empresa")

    return Empresa.objects.filter(
        id__in=[v.empresa_id for v in vinculos]
    )


@login_required
def home(request):
    empresas = empresas_do_usuario(request.user)

    if empresas.count() == 1:
        return redirect("portal:dashboard_empresa", empresa_id=empresas.first().id)

    return render(request, "portal/home.html", {
        "empresas": empresas,
    })


def paginar_documentos(request, queryset, parametro):
    paginator = Paginator(queryset.order_by("numero"), 50)
    numero_pagina = request.GET.get(parametro)
    return paginator.get_page(numero_pagina)


@login_required
def dashboard_empresa(request, empresa_id):
    empresas_permitidas = empresas_do_usuario(request.user)

    empresa = get_object_or_404(
        empresas_permitidas,
        id=empresa_id
    )

    hoje = date.today()

    try:
        ano = int(request.GET.get("ano", hoje.year))
    except Exception:
        ano = hoje.year

    try:
        mes = int(request.GET.get("mes", hoje.month))
    except Exception:
        mes = hoje.month

    busca = request.GET.get("q", "").strip()

    documentos = DocumentoFiscal.objects.filter(
        empresa=empresa,
        ano=ano,
        mes=mes
    )

    if busca:
        documentos = documentos.filter(
            Q(chave_acesso__icontains=busca) |
            Q(numero__icontains=busca)
        )

    nfe_saida = documentos.filter(tipo_documento="NFE_SAIDA")
    nfe_entrada = documentos.filter(tipo_documento="NFE_ENTRADA")
    nfce = documentos.filter(tipo_documento="NFCE")

    total_nfe_saida = sum([d.valor_total for d in nfe_saida])
    total_nfe_entrada = sum([d.valor_total for d in nfe_entrada])
    total_nfce = sum([d.valor_total for d in nfce])

    nfe_saida_pagina = paginar_documentos(request, nfe_saida, "page_saida")
    nfe_entrada_pagina = paginar_documentos(request, nfe_entrada, "page_entrada")
    nfce_pagina = paginar_documentos(request, nfce, "page_nfce")

    return render(request, "portal/dashboard_empresa.html", {
        "empresa": empresa,
        "ano": ano,
        "mes": mes,
        "busca": busca,
        "nfe_saida": nfe_saida_pagina,
        "nfe_entrada": nfe_entrada_pagina,
        "nfce": nfce_pagina,
        "total_nfe_saida": total_nfe_saida,
        "total_nfe_entrada": total_nfe_entrada,
        "total_nfce": total_nfce,
    })


@login_required
def upload_xml_empresa(request, empresa_id):
    empresas_permitidas = empresas_do_usuario(request.user)

    empresa = get_object_or_404(
        empresas_permitidas,
        id=empresa_id
    )

    resultados = []

    if request.method == "POST":
        arquivos = request.FILES.getlist("arquivos")

        if not arquivos:
            resultados.append({
                "status": "erro",
                "mensagem": "Nenhum arquivo selecionado."
            })

        for arquivo in arquivos:
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
                        "arquivo_xml": ContentFile(conteudo, name=arquivo.name),
                    }
                )

                resultados.append({
                    "status": "ok",
                    "mensagem": "XML importado com sucesso." if criado else "XML já existia e foi atualizado.",
                    "arquivo": arquivo.name,
                    "chave": dados["chave_acesso"],
                    "numero": dados["numero"],
                    "tipo": dados["tipo_documento"],
                })

            except Exception as erro:
                resultados.append({
                    "status": "erro",
                    "arquivo": arquivo.name,
                    "mensagem": str(erro),
                })

    return render(request, "portal/upload_xml.html", {
        "empresa": empresa,
        "resultados": resultados,
    })


@login_required
def download_xmls_empresa(request, empresa_id, tipo_documento):
    empresas_permitidas = empresas_do_usuario(request.user)

    empresa = get_object_or_404(
        empresas_permitidas,
        id=empresa_id,
        ativo=True
    )

    mes = request.GET.get("mes")
    ano = request.GET.get("ano")

    documentos = DocumentoFiscal.objects.filter(
        empresa=empresa,
        tipo_documento=tipo_documento
    )

    if mes:
        documentos = documentos.filter(mes=int(mes))

    if ano:
        documentos = documentos.filter(ano=int(ano))

    documentos = documentos.order_by("numero")

    if not documentos.exists():
        return HttpResponse(
            "Nenhum XML disponível para download neste filtro.",
            content_type="text/plain; charset=utf-8"
        )

    memoria = BytesIO()
    total = 0

    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc in documentos:
            try:
                nome_xml = f"{doc.chave_acesso or doc.numero}.xml"

                xml_conteudo = getattr(doc, "xml_conteudo", "")

                if xml_conteudo:
                    zip_file.writestr(nome_xml, xml_conteudo.encode("utf-8"))
                    total += 1
                    continue

                if doc.arquivo_xml:
                    caminho = doc.arquivo_xml.path

                    if os.path.exists(caminho):
                        zip_file.write(caminho, nome_xml)
                        total += 1

            except Exception:
                continue

    if total == 0:
        return HttpResponse(
            "Os registros existem, mas os XMLs ainda não foram reenviados para o banco novo.",
            content_type="text/plain; charset=utf-8"
        )

    memoria.seek(0)

    nome_zip = f"{empresa.cnpj}_{tipo_documento}_{mes or 'todos'}_{ano or 'todos'}.zip"

    resposta = HttpResponse(memoria.getvalue(), content_type="application/zip")
    resposta["Content-Disposition"] = f'attachment; filename="{nome_zip}"'

    return resposta