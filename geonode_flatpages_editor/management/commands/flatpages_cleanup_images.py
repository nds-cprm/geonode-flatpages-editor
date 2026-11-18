from django.core.management.base import BaseCommand

from geonode_flatpages_editor import conf
from geonode_flatpages_editor.editor import cleanup_orphan_images


class Command(BaseCommand):
    help = (
        "Apaga as imagens das flatpages que nenhuma página usa (enviadas numa página nova que não foi "
        "salva, removidas do conteúdo ou de páginas excluídas), com mais de --min-age horas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age",
            type=float,
            default=None,
            help=f"idade mínima, em horas (padrão: ORPHAN_MIN_AGE_HOURS, {conf.DEFAULTS['ORPHAN_MIN_AGE_HOURS']})",
        )
        parser.add_argument("--dry-run", action="store_true", help="só lista, sem apagar")

    def handle(self, *args, min_age=None, dry_run=False, **options):
        orphans = cleanup_orphan_images(min_age_hours=min_age, dry_run=dry_run)
        for name in orphans:
            self.stdout.write(name)
        verb = "seriam apagadas" if dry_run else "apagadas"
        self.stdout.write(self.style.SUCCESS(f"{len(orphans)} imagem(ns) órfã(s) {verb}."))
