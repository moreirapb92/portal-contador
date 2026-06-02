# -*- coding: utf-8 -*-

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou atualiza o usuário administrador no Render."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "Admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "tdvctoin@gmail.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not password:
            self.stdout.write(self.style.ERROR("DJANGO_SUPERUSER_PASSWORD não definida."))
            return

        user, criado = User.objects.get_or_create(username=username)

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        if criado:
            self.stdout.write(self.style.SUCCESS(f"Admin criado: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Admin atualizado e senha redefinida: {username}"))