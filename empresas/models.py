# -*- coding: utf-8 -*-

import uuid

from django.contrib.auth.models import User
from django.db import models


def limpar_cnpj(cnpj):
    return "".join(filter(str.isdigit, cnpj or ""))


class Empresa(models.Model):
    cnpj = models.CharField(max_length=14, unique=True)
    razao_social = models.CharField(max_length=180)
    nome_fantasia = models.CharField(max_length=180, blank=True)
    token_api = models.CharField(max_length=80, unique=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["razao_social"]

    def save(self, *args, **kwargs):
        self.cnpj = limpar_cnpj(self.cnpj)

        if not self.token_api:
            self.token_api = str(uuid.uuid4())

        super().save(*args, **kwargs)

    def __str__(self):
        nome = self.nome_fantasia or self.razao_social
        return f"{nome} - {self.cnpj}"


class UsuarioEmpresa(models.Model):
    PERFIL_CHOICES = [
        ("contador", "Contador"),
        ("empresa", "Empresa"),
        ("admin", "Administrador"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default="contador")
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vínculo usuário/empresa"
        verbose_name_plural = "Vínculos usuários/empresas"
        unique_together = ("usuario", "empresa")

    def __str__(self):
        return f"{self.usuario.email or self.usuario.username} -> {self.empresa}"