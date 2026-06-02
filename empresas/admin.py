# -*- coding: utf-8 -*-

import secrets
import string

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User

from .models import Empresa, UsuarioEmpresa


def gerar_senha_segura(tamanho=10):
    letras = string.ascii_letters
    numeros = string.digits
    especiais = "@#$%"

    caracteres = letras + numeros + especiais

    senha = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(numeros),
        secrets.choice(especiais),
    ]

    senha += [secrets.choice(caracteres) for _ in range(tamanho - len(senha))]

    secrets.SystemRandom().shuffle(senha)

    return "".join(senha)


class EmpresaAdminForm(forms.ModelForm):
    email_contador = forms.EmailField(
        label="E-mail do contador",
        required=False,
        help_text="Informe o e-mail do contador que terá acesso a esta empresa."
    )

    senha_contador = forms.CharField(
        label="Senha manual do contador",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Opcional. Se preencher, essa será a senha do contador."
    )

    gerar_senha_automatica = forms.BooleanField(
        label="Gerar senha automática se a senha manual estiver vazia",
        required=False,
        initial=True,
        help_text="Se marcado, o sistema gera uma senha para contador novo quando você não informar senha manual."
    )

    class Meta:
        model = Empresa
        fields = (
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "ativo",
            "limpar_xml_nuvem",
            "meses_retencao_xml",
        )

    def clean_email_contador(self):
        email = self.cleaned_data.get("email_contador", "")
        return email.strip().lower()

    def clean(self):
        cleaned = super().clean()

        email = cleaned.get("email_contador")
        senha = cleaned.get("senha_contador")
        gerar_senha = cleaned.get("gerar_senha_automatica")

        if email:
            usuario_existe = User.objects.filter(username=email).exists()

            if not usuario_existe and not senha and not gerar_senha:
                raise forms.ValidationError(
                    "Esse contador ainda não existe. Informe uma senha manual ou marque gerar senha automática."
                )

        return cleaned


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form = EmpresaAdminForm

    list_display = (
        "id",
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "ativo",
        "meses_retencao_xml",
    )

    search_fields = (
        "razao_social",
        "nome_fantasia",
        "cnpj",
    )

    list_filter = (
        "ativo",
        "meses_retencao_xml",
    )

    def get_fields(self, request, obj=None):
        campos = (
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "ativo",
            "email_contador",
            "senha_contador",
            "gerar_senha_automatica",
            "limpar_xml_nuvem",
            "meses_retencao_xml",
        )

        if obj:
            return campos + (
                "token_api",
                "criado_em",
            )

        return campos

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "token_api",
                "criado_em",
            )

        return ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        email = form.cleaned_data.get("email_contador")
        senha_manual = form.cleaned_data.get("senha_contador")
        gerar_automatica = form.cleaned_data.get("gerar_senha_automatica")

        if not email:
            return

        usuario, criado = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "is_active": True,
            }
        )

        usuario.email = email
        usuario.is_active = True

        senha_final = None

        if senha_manual:
            senha_final = senha_manual
        elif criado and gerar_automatica:
            senha_final = gerar_senha_segura()

        if senha_final:
            usuario.set_password(senha_final)

        usuario.save()

        UsuarioEmpresa.objects.update_or_create(
            usuario=usuario,
            empresa=obj,
            defaults={
                "perfil": "contador",
                "ativo": True,
            }
        )

        if senha_final:
            messages.success(
                request,
                f"Contador vinculado com sucesso. E-mail: {email} | Senha temporária: {senha_final}"
            )
        else:
            messages.success(
                request,
                f"Contador {email} vinculado com sucesso. A senha existente não foi alterada."
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