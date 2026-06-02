# -*- coding: utf-8 -*-

from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q
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


@login_required
def dashboard_empresa(request, empresa_id):
    empresas_permitidas = empresas_do_usuario(request.user)

    empresa = get_object_or_404(
        empresas_permitidas,
        id=empresa_id
    )

    hoje = date.today()
    ano = int(request.GET.get("ano", hoje.year))
    mes = int(request.GET.get("mes", hoje.month))
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

    return render(request, "portal/dashboard_empresa.html", {
        "empresa": empresa,
        "ano": ano,
        "mes": mes,
        "busca": busca,
        "nfe_saida": nfe_saida[:10],
        "nfe_entrada": nfe_entrada[:10],
        "nfce": nfce[:10],
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
                    }
                )

                arquivo.seek(0)
                documento.arquivo_xml.save(arquivo.name, arquivo, save=True)

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