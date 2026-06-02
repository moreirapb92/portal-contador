# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import DocumentoFiscal


@admin.register(DocumentoFiscal)
class DocumentoFiscalAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "tipo_documento",
        "numero",
        "serie",
        "chave_acesso",
        "situacao",
        "data_emissao",
        "valor_total",
    )
    search_fields = (
        "empresa__razao_social",
        "empresa__cnpj",
        "chave_acesso",
        "numero",
    )
    list_filter = ("tipo_documento", "situacao", "ano", "mes")