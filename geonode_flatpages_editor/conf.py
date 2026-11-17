"""
Configuração do app, lida do setting FLATPAGES_EDITOR (dicionário opcional):

    FLATPAGES_EDITOR = {
        "UPLOAD_DIR": "flatpages",          # pasta das imagens dentro do MEDIA_ROOT
        "MAX_IMAGE_SIZE": 5 * 1024 * 1024,  # bytes
        "TINYMCE_CONFIG": {"height": 600},  # mesclado sobre a configuração padrão do editor
    }

Os valores são lidos a cada uso, para respeitar override_settings nos testes.
"""
from django.conf import settings

DEFAULTS = {
    "UPLOAD_DIR": "flatpages",
    "MAX_IMAGE_SIZE": 5 * 1024 * 1024,
    "TINYMCE_CONFIG": {},
}

# subpasta de UPLOAD_DIR para imagens de páginas ainda não salvas
TEMP_DIR = "tmp"

# formatos aceitos no upload (formato detectado pelo Pillow -> extensão gravada)
IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}


def get(name):
    return getattr(settings, "FLATPAGES_EDITOR", {}).get(name, DEFAULTS[name])
