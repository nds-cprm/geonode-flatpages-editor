import os
import uuid

from PIL import Image
from django.contrib.flatpages.models import FlatPage
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils.text import slugify
from django.utils.translation import gettext as _

from . import conf
from .editor import page_dir, temp_dir


def image_upload(request):
    """
    Recebe uma imagem do editor de flatpages e devolve {"location": url} (formato do TinyMCE).
    Com ?page=<id>, grava na pasta da página; sem ele (página nova), numa pasta temporária.

    Servida pelo admin (TinyMCEFlatPageAdmin.get_urls), que já exige usuário da equipe e CSRF;
    método e permissões são verificados no admin.
    """
    page_id = request.GET.get("page")
    if page_id:
        if not page_id.isdigit() or not FlatPage.objects.filter(pk=page_id).exists():
            return JsonResponse({"error": _("Page not found.")}, status=400)
        directory = page_dir(page_id)
    else:
        directory = f"{temp_dir()}/{uuid.uuid4().hex}"

    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"error": _("No file was sent.")}, status=400)
    max_size = conf.get("MAX_IMAGE_SIZE")
    if upload.size > max_size:
        return JsonResponse(
            {"error": _("The image exceeds the %(size)s MB limit.") % {"size": f"{max_size / 1024 / 1024:g}"}},
            status=400,
        )
    try:
        with Image.open(upload) as image:
            image_format = image.format
            image.verify()
    except Exception:
        return JsonResponse({"error": _("The file is not a valid image.")}, status=400)
    if image_format not in conf.IMAGE_FORMATS:
        return JsonResponse({"error": _("Image format not allowed (use PNG, JPEG, GIF or WebP).")}, status=400)

    upload.seek(0)
    # nome original normalizado; a extensão vem do formato validado, não do nome enviado
    base = slugify(os.path.splitext(upload.name or "")[0]) or "image"
    name = default_storage.save(f"{directory}/{base}.{conf.IMAGE_FORMATS[image_format]}", upload)
    return JsonResponse({"location": default_storage.url(name)})
