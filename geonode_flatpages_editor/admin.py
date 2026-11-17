from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.urls import path
from tinymce.widgets import TinyMCE

from .editor import move_temp_images, sanitize_html, tinymce_config
from .views import image_upload


class TinyMCEFlatpageForm(FlatpageForm):
    """Conteúdo editado com TinyMCE e sanitizado ao salvar (ver editor.py)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = TinyMCE(mce_attrs=tinymce_config(self.instance.pk))

    def clean_content(self):
        return sanitize_html(self.cleaned_data.get("content", ""))


class TinyMCEFlatPageAdmin(FlatPageAdmin):
    form = TinyMCEFlatpageForm

    class Media:
        # o nome do arquivo não pode terminar em "tinymce.js": o TinyMCE usaria a pasta dele
        # como base para carregar temas, ícones e traduções
        js = ("geonode_flatpages_editor/js/image_upload.js",)

    def get_urls(self):
        # admin_view: exige usuário da equipe e aplica a proteção CSRF
        return [
            path(
                "upload-image/",
                self.admin_site.admin_view(self.image_upload_view),
                name="flatpages_flatpage_upload_image",
            ),
        ] + super().get_urls()

    def image_upload_view(self, request):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not (self.has_add_permission(request) or self.has_change_permission(request)):
            raise PermissionDenied
        return image_upload(request)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # imagens enviadas antes de a página existir: mover para <UPLOAD_DIR>/<id>/
        if move_temp_images(obj):
            FlatPage.objects.filter(pk=obj.pk).update(content=obj.content)


# substitui o admin de django.contrib.flatpages (este app é carregado depois dele)
if admin.site.is_registered(FlatPage):
    admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)
