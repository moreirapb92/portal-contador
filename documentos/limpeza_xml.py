# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date, timedelta

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
    """
    Limpa apenas XMLs antigos da nuvem/banco.

    Regra correta:
    - Não usa data_emissao da nota.
    - Usa criado_em, que é a data em que o XML foi importado para o portal.
    - Assim, cliente novo que enviar XML antigo não perde o XML imediatamente.
    """

    if not getattr(empresa, "limpar_xml_nuvem", True):
        return {
            "empresa": empresa.razao_social,
            "apagados": 0,
            "ignorados": 0,
            "data_limite": None,
        }

    meses = int(getattr(empresa, "meses_retencao_xml", 3) or 3)

    hoje = timezone.localdate()
    data_limite = subtrair_meses(hoje, meses)

    documentos = DocumentoFiscal.objects.filter(
        empresa=empresa,
        criado_em__date__lt=data_limite,
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
        "data_limite": data_limite,
    }


def empresa_precisa_limpeza(empresa, intervalo_dias=7):
    if not getattr(empresa, "limpar_xml_nuvem", True):
        return False

    ultima_limpeza = getattr(empresa, "ultima_limpeza_xml", None)

    if not ultima_limpeza:
        return True

    agora = timezone.now()
    proxima_limpeza = ultima_limpeza + timedelta(days=intervalo_dias)

    return agora >= proxima_limpeza


def executar_limpeza_automatica_empresa(empresa, intervalo_dias=7):
    """
    Executa limpeza automática no máximo 1 vez a cada X dias por empresa.
    Isso evita Cron pago no Render.
    """

    if not empresa_precisa_limpeza(empresa, intervalo_dias=intervalo_dias):
        return {
            "executou": False,
            "empresa": empresa.razao_social,
            "apagados": 0,
            "ignorados": 0,
        }

    resultado = limpar_xmls_antigos_empresa(empresa)

    empresa.ultima_limpeza_xml = timezone.now()
    empresa.save(update_fields=["ultima_limpeza_xml"])

    resultado["executou"] = True
    return resultado