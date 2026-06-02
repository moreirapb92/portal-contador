# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import Empresa, UsuarioEmpresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("razao_social", "nome_fantasia", "cnpj", "ativo", "criado_em")
    search_fields = ("razao_social", "nome_fantasia", "cnpj")
    list_filter = ("ativo",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("token_api", "criado_em")
        return ()


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "perfil", "ativo")
    search_fields = ("usuario__email", "usuario__username", "empresa__razao_social", "empresa__cnpj")
    list_filter = ("perfil", "ativo")