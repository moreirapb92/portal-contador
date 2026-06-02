# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date

from django.utils import timezone

from documentos.models import DocumentoFiscal


def subtrair_meses(data_base, meses):
    ano = data_base.year
    mes = data_base.month - meses

    while mes <= 0:
        mes += 12
        ano -= 1

    ultimo_dia = monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia)

    return date(ano, mes, dia)


def limpar_xmls_antigos_empresa(empresa):
    if not getattr(empresa, "limpar_xml_nuvem", True):
        return {
            "empresa": empresa.razao_social,
            "apagados": 0,
            "ignorados": 0,
        }

    meses = int(getattr(empresa, "meses_retencao_xml", 3) or 3)

    hoje = timezone.localdate()
    data_limite = subtrair_meses(hoje, meses)

    documentos = DocumentoFiscal.objects.filter(
        empresa=empresa,
        data_emissao__lt=data_limite,
    )

    apagados = 0
    ignorados = 0

    for documento in documentos:
        tinha_algo_para_apagar = False

        try:
            if documento.arquivo_xml:
                documento.arquivo_xml.delete(save=False)
                documento.arquivo_xml = None
                tinha_algo_para_apagar = True
        except Exception:
            pass

        if getattr(documento, "xml_conteudo", ""):
            documento.xml_conteudo = ""
            tinha_algo_para_apagar = True

        if tinha_algo_para_apagar:
            documento.save(update_fields=["arquivo_xml", "xml_conteudo"])
            apagados += 1
        else:
            ignorados += 1

    return {
        "empresa": empresa.razao_social,
        "apagados": apagados,
        "ignorados": ignorados,
    }