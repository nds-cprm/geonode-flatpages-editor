from django.apps import AppConfig
from django.core import checks
from django.utils.translation import gettext_lazy as _


class FlatpagesEditorConfig(AppConfig):
    """
    Edição de flatpages com TinyMCE, conteúdo sanitizado e upload de imagens por página.
    Deve vir depois de django.contrib.flatpages no INSTALLED_APPS (substitui o admin dele).
    """

    name = "geonode_flatpages_editor"
    label = "flatpages_editor"  # "flatpages" já é o rótulo do app do Django
    verbose_name = _("Flatpages editor")
    default = True

    def ready(self):
        from django.contrib.flatpages.models import FlatPage
        from django.db.models.signals import post_delete

        from .signals import flatpage_deleted

        # ao apagar uma flatpage, apaga a pasta de imagens dela (<UPLOAD_DIR>/<id>/)
        post_delete.connect(flatpage_deleted, sender=FlatPage, dispatch_uid="flatpages_editor_flatpage_deleted")
        checks.register(check_app_order)


def check_app_order(app_configs, **kwargs):
    """O admin só é substituído se este app vier depois de django.contrib.flatpages."""
    from django.apps import apps as registry

    # pelo registro de apps, não pelo setting: o GeoNode acrescenta objetos Celery ao INSTALLED_APPS
    # (geonode/apps.py), e um app pode vir pelo caminho do AppConfig ("pacote.apps.Config")
    apps = [config.name for config in registry.get_app_configs()]
    if "django.contrib.flatpages" not in apps:
        return [checks.Error("django.contrib.flatpages must be in INSTALLED_APPS.", id="flatpages_editor.E001")]
    if apps.index("geonode_flatpages_editor") < apps.index("django.contrib.flatpages"):
        return [
            checks.Error(
                "geonode_flatpages_editor must come after django.contrib.flatpages in INSTALLED_APPS.",
                id="flatpages_editor.E002",
            )
        ]
    return []
