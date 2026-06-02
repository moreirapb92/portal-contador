# -*- coding: utf-8 -*-

from django.contrib import admin
from django import forms

from .models import Empresa, UsuarioEmpresa


class EmpresaAdminForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = (
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "ativo",
        )


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form = EmpresaAdminForm

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