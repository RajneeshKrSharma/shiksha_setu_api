from django.core.management.base import BaseCommand, CommandError

from apps.core.domain.errors import DomainError
from config.container import container


class Command(BaseCommand):
    help = "Creates the school's Principal account (not an admin-portal user)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **o):
        try:
            container.bootstrap_principal().call(
                name=o["name"], email=o["email"], password=o["password"]
            )
        except DomainError as error:
            raise CommandError(error.message)
        self.stdout.write(self.style.SUCCESS("Principal created."))
