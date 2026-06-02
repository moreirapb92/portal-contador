# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal


def somente_numeros(valor):
    return "".join(filter(str.isdigit, valor or ""))


def texto_no(elemento, caminho, padrao=""):
    encontrado = elemento.find(caminho)

    if encontrado is not None and encontrado.text:
        return encontrado.text.strip()

    return padrao


def buscar_texto_por_tag(raiz, tag):
    for elemento in raiz.iter():
        if elemento.tag.endswith(tag):
            return elemento.text.strip() if elemento.text else ""

    return ""


def buscar_elemento_por_tag(raiz, tag):
    for elemento in raiz.iter():
        if elemento.tag.endswith(tag):
            return elemento

    return None


def parse_data_nfe(valor):
    if not valor:
        return None

    try:
        return datetime.fromisoformat(valor[:10]).date()
    except Exception:
        return None


def ler_xml_nfe(conteudo_xml, cnpj_empresa):
    cnpj_empresa = somente_numeros(cnpj_empresa)

    raiz = ET.fromstring(conteudo_xml)

    inf_nfe = None

    for elemento in raiz.iter():
        if elemento.tag.endswith("infNFe"):
            inf_nfe = elemento
            break

    if inf_nfe is None:
        raise ValueError("Não encontrei a tag infNFe no XML.")

    chave = inf_nfe.attrib.get("Id", "")
    chave = chave.replace("NFe", "").strip()

    if not chave:
        raise ValueError("Não foi possível identificar a chave de acesso.")

    modelo = chave[20:22] if len(chave) >= 22 else ""

    ide = buscar_elemento_por_tag(inf_nfe, "ide")
    emit = buscar_elemento_por_tag(inf_nfe, "emit")
    dest = buscar_elemento_por_tag(inf_nfe, "dest")
    total = buscar_elemento_por_tag(inf_nfe, "ICMSTot")

    numero = buscar_texto_por_tag(ide, "nNF") if ide is not None else ""
    serie = buscar_texto_por_tag(ide, "serie") if ide is not None else ""
    natureza = buscar_texto_por_tag(ide, "natOp") if ide is not None else ""
    data_emissao_raw = buscar_texto_por_tag(ide, "dhEmi") if ide is not None else ""

    emitente_cnpj = buscar_texto_por_tag(emit, "CNPJ") if emit is not None else ""
    destinatario_cnpj = buscar_texto_por_tag(dest, "CNPJ") if dest is not None else ""

    valor_total_raw = buscar_texto_por_tag(total, "vNF") if total is not None else "0"

    try:
        valor_total = Decimal(valor_total_raw)
    except Exception:
        valor_total = Decimal("0.00")

    data_emissao = parse_data_nfe(data_emissao_raw)

    if modelo == "65":
        tipo_documento = "NFCE"
    elif modelo == "55":
        if somente_numeros(emitente_cnpj) == cnpj_empresa:
            tipo_documento = "NFE_SAIDA"
        else:
            tipo_documento = "NFE_ENTRADA"
    else:
        tipo_documento = "NFE_SAIDA"

    mes = data_emissao.month if data_emissao else 1
    ano = data_emissao.year if data_emissao else datetime.now().year

    return {
        "tipo_documento": tipo_documento,
        "chave_acesso": chave,
        "numero": numero,
        "serie": serie,
        "natureza": natureza,
        "data_emissao": data_emissao,
        "valor_total": valor_total,
        "situacao": "CONCLUIDO",
        "emitente_cnpj": somente_numeros(emitente_cnpj),
        "destinatario_cnpj": somente_numeros(destinatario_cnpj),
        "mes": mes,
        "ano": ano,
    }