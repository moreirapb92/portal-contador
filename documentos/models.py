# -*- coding: utf-8 -*-

from django.db import models

from empresas.models import Empresa


def caminho_xml(instance, filename):
    return f"documentos/{instance.empresa.cnpj}/{instance.ano}/{instance.mes:02d}/{filename}"


class DocumentoFiscal(models.Model):
    TIPO_CHOICES = [
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
        ("PENDENTE", "Pendente"),
        ("ERRO", "Erro"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_CHOICES)
    chave_acesso = models.CharField(max_length=80, unique=True)
    numero = models.CharField(max_length=30, blank=True)
    serie = models.CharField(max_length=10, blank=True)
    natureza = models.CharField(max_length=120, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default="CONCLUIDO")
    emitente_cnpj = models.CharField(max_length=14, blank=True)
    destinatario_cnpj = models.CharField(max_length=14, blank=True)
    mes = models.IntegerField(default=1)
    ano = models.IntegerField(default=2026)
    arquivo_xml = models.FileField(upload_to=caminho_xml, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento fiscal"
        verbose_name_plural = "Documentos fiscais"
        ordering = ["-data_emissao", "-id"]
        indexes = [
            models.Index(fields=["empresa", "ano", "mes"]),
            models.Index(fields=["tipo_documento"]),
            models.Index(fields=["chave_acesso"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} {self.numero} - {self.empresa}"