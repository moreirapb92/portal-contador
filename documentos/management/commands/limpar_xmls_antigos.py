# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from empresas.models import Empresa
from documentos.limpeza_xml import limpar_xmls_antigos_empresa


class Command(BaseCommand):
    help = "Apaga XMLs antigos da nuvem/banco mantendo os registros fiscais."

    def handle(self, *args, **options):
        empresas = Empresa.objects.filter(ativo=True)

        total_geral = 0

        for empresa in empresas:
            resultado = limpar_xmls_antigos_empresa(empresa)

            total_geral += resultado["apagados"]

            self.stdout.write(
                f"{resultado['empresa']}: "
                f"{resultado['apagados']} XML(s) apagado(s), "
                f"{resultado['ignorados']} ignorado(s)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Limpeza finalizada. Total apagado da nuvem/banco: {total_geral} XML(s)."
            )
        )