# -*- coding: utf-8 -*-

from django.db import models

from empresas.models import Empresa


def caminho_xml(instance, filename):
    empresa_id = instance.empresa_id or "sem_empresa"
    ano = instance.ano or "sem_ano"
    mes = instance.mes or "sem_mes"
    return f"xmls/empresa_{empresa_id}/{ano}/{mes}/{filename}"


class DocumentoFiscal(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ("NFE_SAIDA", "NF-e Saída"),
        ("NFE_ENTRADA", "NF-e Entrada"),
        ("NFCE", "NFC-e"),
        ("NFSE", "NFS-e"),
        ("CTE", "CT-e"),
        ("MDFE", "MDF-e"),
    ]

    SITUACAO_CHOICES = [
        ("CONCLUIDO", "Concluído"),
        ("CANCELADO", "Cancelado"),
        ("INUTILIZADO", "Inutilizado"),
        ("PENDENTE", "Pendente"),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="documentos_fiscais"
    )

    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES
    )

    chave_acesso = models.CharField(
        max_length=60,
        unique=True
    )

    numero = models.CharField(
        max_length=30,
        blank=True
    )

    serie = models.CharField(
        max_length=20,
        blank=True
    )

    natureza = models.CharField(
        max_length=255,
        blank=True
    )

    data_emissao = models.DateField(
        null=True,
        blank=True
    )

    valor_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    situacao = models.CharField(
        max_length=20,
        choices=SITUACAO_CHOICES,
        default="CONCLUIDO"
    )

    emitente_cnpj = models.CharField(
        max_length=14,
        blank=True
    )

    destinatario_cnpj = models.CharField(
        max_length=14,
        blank=True
    )

    mes = models.PositiveSmallIntegerField(
        default=1
    )

    ano = models.PositiveSmallIntegerField(
        default=2026
    )

    arquivo_xml = models.FileField(
        upload_to=caminho_xml,
        blank=True,
        null=True
    )

    xml_conteudo = models.TextField(
        blank=True,
        default="",
        verbose_name="Conteúdo XML"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Documento fiscal"
        verbose_name_plural = "Documentos fiscais"
        ordering = ["-data_emissao", "-numero"]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} Nº {self.numero} - {self.empresa}"