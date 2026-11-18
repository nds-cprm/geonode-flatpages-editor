"""
Regras do editor de flatpages: tags permitidas, sanitização do HTML, configuração do TinyMCE
e armazenamento das imagens enviadas.

O editor (TinyMCE 5, embutido no django-tinymce que acompanha o GeoNode) só oferece as tags de
ALLOWED_TAGS, mas a garantia é feita no servidor: o conteúdo é sanitizado ao salvar (admin) e de
novo ao exibir (templates/flatpages/default.html, filtro sanitize_flatpage).
"""
import logging
import os
import re
from datetime import timedelta

import bleach
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from . import conf

logger = logging.getLogger(__name__)

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "sub", "sup", "blockquote",
    "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "img",
    "table", "caption", "thead", "tbody", "tr", "th", "td",
}
# tabelas: só a estrutura (mesclagem de células e escopo dos cabeçalhos); bordas, larguras e
# alinhamento ficam no CSS do projeto
TABLE_CELL_SPAN = re.compile(r"^[1-9][0-9]?$")
TABLE_HEADER_SCOPES = {"row", "col", "rowgroup", "colgroup"}
# vale para href e src: endereços data:, javascript: etc. são removidos; tel: para telefones
# clicáveis no celular
ALLOWED_PROTOCOLS = {"http", "https", "mailto", "tel"}

# nome da função JS de upload (static/geonode_flatpages_editor/js/image_upload.js)
UPLOAD_HANDLER = "flatpagesEditorImageUpload"
UPLOAD_URL_NAME = "admin:flatpages_flatpage_upload_image"


def upload_dir() -> str:
    return conf.get("UPLOAD_DIR").strip("/")


def page_dir(page_id) -> str:
    """Pasta (no storage) das imagens de uma página: <UPLOAD_DIR>/<id>."""
    return f"{upload_dir()}/{page_id}"


def temp_dir() -> str:
    return f"{upload_dir()}/{conf.TEMP_DIR}"


def _image_src_allowed(value: str) -> bool:
    """Imagens enviadas pelo editor (MEDIA_URL/<UPLOAD_DIR>/...) ou externas (http/https)."""
    return value.startswith((f"{settings.MEDIA_URL}{upload_dir()}/", "https://", "http://"))


# esquema no início de um endereço (ex.: "javascript:", "tel:")
URL_SCHEME = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9+.-]*):")


def _href_allowed(value: str) -> bool:
    """
    Recusa endereços com esquema fora de ALLOWED_PROTOCOLS. O bleach já filtra os protocolos, mas
    trata "esquema:só-dígitos" (ex.: "javascript:1", "sms:40199") como "host:porta" relativo e os
    mantém; esta checagem fecha essa brecha. Endereços relativos (/pages/x/, #ancora) passam.
    """
    match = URL_SCHEME.match(value or "")
    return not match or match.group(1).lower() in ALLOWED_PROTOCOLS


def _allowed_attribute(tag: str, name: str, value: str) -> bool:
    if tag == "a":
        if name == "href":
            return _href_allowed(value)
        return name == "title" or (name == "target" and value == "_blank")
    if tag == "img":
        return name in ("alt", "width", "height") or (name == "src" and _image_src_allowed(value))
    if tag in ("td", "th") and name in ("colspan", "rowspan"):
        return bool(TABLE_CELL_SPAN.match(value or ""))
    if tag == "th" and name == "scope":
        return value in TABLE_HEADER_SCOPES
    return False


def sanitize_html(html: str) -> str:
    """Remove tudo o que não estiver na lista de tags e atributos permitidos."""
    return bleach.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes=_allowed_attribute,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


def tinymce_config(page_id=None) -> dict:
    """
    Configuração do TinyMCE só para o campo de conteúdo das flatpages (não altera o padrão
    global do django-tinymce). Montada a cada formulário, no idioma ativo; o idioma do próprio
    editor é escolhido pelo django-tinymce a partir do idioma do Django.
    Com page_id (página já salva), as imagens vão direto para a pasta da página.
    """
    upload_url = reverse(UPLOAD_URL_NAME)
    if page_id:
        upload_url += f"?page={page_id}"
    config = {
        "height": 500,
        "menubar": False,
        "branding": False,
        "plugins": "lists link image paste autolink table",
        "toolbar": "undo redo | formatselect | bold italic underline strikethrough | subscript superscript | "
                   "bullist numlist blockquote | link image table | removeformat",
        "block_formats": "; ".join(
            f"{label}={tag}" for label, tag in (
                (_("Paragraph"), "p"), (_("Heading 2"), "h2"), (_("Heading 3"), "h3"), (_("Heading 4"), "h4"),
                (_("Heading 5"), "h5"), (_("Heading 6"), "h6"),
            )
        ),
        # o editor descarta, ao digitar e ao colar, o que estiver fora desta lista (ALLOWED_TAGS)
        "valid_elements": "p,br,strong/b,em/i,u,s,sub,sup,blockquote,h2,h3,h4,h5,h6,ul,ol,li,"
                          "a[href|title|target<_blank],img[src|alt|width|height],"
                          "table,caption,thead,tbody,tr,th[colspan|rowspan|scope],td[colspan|rowspan]",
        # tabelas só com estrutura: sem border/width/style padrão, sem abas avançadas (cores, bordas,
        # alinhamento), sem redimensionar com o mouse (gravaria larguras) e sem colgroup; cabeçalho em
        # <thead>. O visual fica no CSS do projeto
        "table_default_attributes": {},
        "table_default_styles": {},
        "table_appearance_options": False,
        "table_advtab": False,
        "table_cell_advtab": False,
        "table_row_advtab": False,
        "table_resize_bars": False,
        "table_use_colgroups": False,
        "table_header_type": "section",
        "object_resizing": "img",
        "paste_as_text": True,
        "link_target_list": [{"title": _("Same window"), "value": ""}, {"title": _("New window"), "value": "_blank"}],
        # upload de imagens: a função JS envia o token CSRF do formulário do admin
        "images_upload_url": upload_url,
        "images_upload_handler": UPLOAD_HANDLER,
        "automatic_uploads": True,
        "images_file_types": "png,jpg,jpeg,gif,webp",
        "image_dimensions": True,
        "relative_urls": False,
        "remove_script_host": True,
    }
    config.update(conf.get("TINYMCE_CONFIG"))
    return config


def _remove_empty_dir(name: str):
    """Remove uma pasta vazia (o FileSystemStorage não apaga diretórios)."""
    try:
        os.rmdir(default_storage.path(name))
    except (NotImplementedError, OSError):
        pass


def delete_page_images(page_id):
    """Apaga a pasta de imagens da página (<UPLOAD_DIR>/<id>/) e tudo o que estiver nela."""
    directory = page_dir(page_id)
    try:
        _subdirs, files = default_storage.listdir(directory)
    except (FileNotFoundError, NotImplementedError):
        return
    for name in files:
        default_storage.delete(f"{directory}/{name}")
    _remove_empty_dir(directory)


def move_temp_images(page: FlatPage) -> bool:
    """
    Move para <UPLOAD_DIR>/<id_da_página>/ as imagens de <UPLOAD_DIR>/tmp/ usadas no conteúdo da
    página (enviadas antes de a página existir) e corrige os endereços no conteúdo.
    Retorna True se o conteúdo foi alterado.
    """
    temp_url = re.escape(f"{settings.MEDIA_URL}{temp_dir()}/")
    content = page.content
    for url in set(re.findall(temp_url + r"[0-9a-f]{32}/[^\"'\s<>]+", content)):
        old_name = url[len(settings.MEDIA_URL):]
        if not default_storage.exists(old_name):
            continue
        with default_storage.open(old_name) as image:
            new_name = default_storage.save(f"{page_dir(page.pk)}/{os.path.basename(old_name)}", image)
        default_storage.delete(old_name)
        _remove_empty_dir(os.path.dirname(old_name))
        content = content.replace(url, default_storage.url(new_name))
    if content == page.content:
        return False
    page.content = content
    return True


def _listdir(directory: str):
    """(subpastas, arquivos) de uma pasta do storage; vazio se ela não existir."""
    try:
        return default_storage.listdir(directory)
    except (FileNotFoundError, NotADirectoryError):
        return [], []


def _older_than(name: str, cutoff) -> bool:
    """True se o arquivo foi modificado antes de cutoff; sem a data (storage sem suporte), False."""
    try:
        return default_storage.get_modified_time(name) < cutoff
    except (NotImplementedError, OSError):
        return False


def cleanup_orphan_images(min_age_hours=None, dry_run=False) -> list:
    """
    Apaga as imagens enviadas pelo editor que nenhuma página usa e devolve os nomes (no storage).
    São órfãs, se tiverem mais de min_age_hours (padrão: ORPHAN_MIN_AGE_HOURS):
    - as de <UPLOAD_DIR>/tmp/<uuid>/, enviadas numa página nova que não foi salva;
    - as de <UPLOAD_DIR>/<id>/ que saíram do conteúdo ou cuja página não existe mais.
    Uma imagem só fica se aparecer no conteúdo de alguma página (não só da dona da pasta: um trecho
    copiado de uma página para outra leva o endereço junto). A idade mínima protege quem acabou de
    enviar uma imagem e ainda não salvou a página. Pastas fora desse padrão não são tocadas.
    Com dry_run, só lista. Pastas que ficam vazias são removidas.
    """
    if min_age_hours is None:
        min_age_hours = conf.get("ORPHAN_MIN_AGE_HOURS")
    cutoff = timezone.now() - timedelta(hours=min_age_hours)
    content = "\n".join(FlatPage.objects.values_list("content", flat=True))
    base = upload_dir()
    orphans = []
    for sub in sorted(_listdir(base)[0]):
        if sub == conf.TEMP_DIR:
            folders = [f"{base}/{sub}/{name}" for name in sorted(_listdir(f"{base}/{sub}")[0])]
        elif sub.isdigit():
            folders = [f"{base}/{sub}"]
        else:
            continue
        for folder in folders:
            for filename in sorted(_listdir(folder)[1]):
                name = f"{folder}/{filename}"
                if default_storage.url(name) in content or not _older_than(name, cutoff):
                    continue
                orphans.append(name)
                if not dry_run:
                    default_storage.delete(name)
                    logger.info("Imagem órfã de flatpage apagada: %s", name)
            if not dry_run:
                _remove_empty_dir(folder)
    return orphans
