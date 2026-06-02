# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import Empresa, UsuarioEmpresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "ativo",
    )

    search_fields = (
        "razao_social",
        "nome_fantasia",
        "cnpj",
    )

    list_filter = (
        "ativo",
    )

    def get_fields(self, request, obj=None):
        if obj:
            return (
                "cnpj",
                "razao_social",
                "nome_fantasia",
                "ativo",
                "token_api",
                "criado_em",
            )

        return (
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "ativo",
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "token_api",
                "criado_em",
            )

        return ()


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "empresa",
        "perfil",
        "ativo",
    )

    search_fields = (
        "usuario__username",
        "usuario__email",
        "empresa__razao_social",
        "empresa__cnpj",
    )

    list_filter = (
        "perfil",
        "ativo",
    )