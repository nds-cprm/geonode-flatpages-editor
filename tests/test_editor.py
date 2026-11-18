import io
import json
import os
import shutil
from unittest import mock

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from geonode_flatpages_editor.admin import TinyMCEFlatpageForm
from geonode_flatpages_editor.apps import check_app_order
from geonode_flatpages_editor.editor import move_temp_images, sanitize_html, tinymce_config

UPLOAD_URL = "/admin/flatpages/flatpage/upload-image/"


def image_file(name="Foto Bonita.png", fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue())


class MediaTestCase(TestCase):
    def tearDown(self):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "flatpages"), ignore_errors=True)
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "paginas"), ignore_errors=True)

    def make_page(self, content="<p>x</p>", url="/sobre/"):
        page = FlatPage.objects.create(url=url, title="Sobre", content=content)
        page.sites.add(Site.objects.get_current())
        return page


class SanitizeTests(TestCase):
    def test_remove_script_and_handlers(self):
        html = '<p onclick="x()">oi<script>alert(1)</script></p><iframe src="https://x"></iframe>'
        self.assertEqual(sanitize_html(html), "<p>oialert(1)</p>")

    def test_links(self):
        self.assertEqual(
            sanitize_html('<a href="javascript:alert(1)" target="_top">a</a><a href="https://x" target="_blank">b</a>'),
            '<a>a</a><a href="https://x" target="_blank">b</a>',
        )

    def test_images(self):
        self.assertEqual(sanitize_html('<img src="data:image/png;base64,AAA">'), "<img>")
        self.assertEqual(sanitize_html('<img src="/outro/a.png">'), "<img>")
        ok = '<img src="/uploaded/flatpages/1/a.png" alt="a">'
        self.assertEqual(sanitize_html(ok), ok)

    @override_settings(FLATPAGES_EDITOR={"UPLOAD_DIR": "paginas"})
    def test_images_custom_upload_dir(self):
        self.assertEqual(sanitize_html('<img src="/uploaded/flatpages/1/a.png">'), "<img>")
        ok = '<img src="/uploaded/paginas/1/a.png">'
        self.assertEqual(sanitize_html(ok), ok)

    def test_none(self):
        self.assertEqual(sanitize_html(None), "")


class ConfigTests(TestCase):
    def test_upload_url(self):
        self.assertEqual(tinymce_config()["images_upload_url"], UPLOAD_URL)
        self.assertEqual(tinymce_config(7)["images_upload_url"], UPLOAD_URL + "?page=7")

    def test_translated_labels(self):
        with translation.override("pt-br"):
            config = tinymce_config()
        self.assertIn("Parágrafo=p", config["block_formats"])
        self.assertEqual(config["link_target_list"][1]["title"], "Nova janela")

    @override_settings(FLATPAGES_EDITOR={"TINYMCE_CONFIG": {"height": 900}})
    def test_override(self):
        self.assertEqual(tinymce_config()["height"], 900)

    def test_form_sanitizes(self):
        form = TinyMCEFlatpageForm(
            data={"url": "/a/", "title": "A", "content": "<p>ok</p><script>x</script>", "sites": [Site.objects.get_current().pk]}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["content"], "<p>ok</p>x")


class UploadTests(MediaTestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "a@a.test", "x")
        self.client.force_login(self.admin)

    def post(self, data, query=""):
        return self.client.post(UPLOAD_URL + query, data)

    def test_reverse(self):
        self.assertEqual(reverse("admin:flatpages_flatpage_upload_image"), UPLOAD_URL)

    def test_new_page_goes_to_tmp(self):
        response = self.post({"file": image_file()})
        self.assertEqual(response.status_code, 200)
        location = response.json()["location"]
        self.assertRegex(location, r"^/uploaded/flatpages/tmp/[0-9a-f]{32}/foto-bonita\.png$")
        self.assertTrue(default_storage.exists(location[len(settings.MEDIA_URL):]))

    def test_existing_page(self):
        page = self.make_page()
        response = self.post({"file": image_file("x.jpeg", "JPEG")}, f"?page={page.pk}")
        self.assertEqual(response.json()["location"], f"/uploaded/flatpages/{page.pk}/x.jpg")

    def test_unknown_page(self):
        self.assertEqual(self.post({"file": image_file()}, "?page=999").status_code, 400)
        self.assertEqual(self.post({"file": image_file()}, "?page=../1").status_code, 400)

    def test_invalid_files(self):
        self.assertEqual(self.post({}).status_code, 400)
        response = self.post({"file": SimpleUploadedFile("a.png", b"not an image")})
        self.assertEqual(response.status_code, 400)
        response = self.post({"file": image_file("a.bmp", "BMP")})
        self.assertIn("not allowed", response.json()["error"])

    @override_settings(FLATPAGES_EDITOR={"MAX_IMAGE_SIZE": 10})
    def test_too_big(self):
        response = self.post({"file": image_file()})
        self.assertEqual(response.status_code, 400)
        self.assertIn("limit", response.json()["error"])

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(UPLOAD_URL).status_code, 405)

    def test_requires_staff(self):
        self.client.force_login(User.objects.create_user("comum", password="x"))
        response = self.post({"file": image_file()})
        self.assertEqual(response.status_code, 302)  # redireciona para o login do admin

    def test_requires_permission(self):
        staff = User.objects.create_user("equipe", password="x", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.post({"file": image_file()}).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="change_flatpage"))
        self.assertEqual(self.post({"file": image_file()}).status_code, 200)

    def test_requires_csrf(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(UPLOAD_URL, {"file": image_file()}).status_code, 403)


class ImageLifecycleTests(MediaTestCase):
    def test_move_temp_images(self):
        name = default_storage.save("flatpages/tmp/" + "a" * 32 + "/foto.png", ContentFile(b"x"))
        page = self.make_page(content=f'<p><img src="/uploaded/{name}"></p>')
        self.assertTrue(move_temp_images(page))
        self.assertEqual(page.content, f'<p><img src="/uploaded/flatpages/{page.pk}/foto.png"></p>')
        self.assertFalse(default_storage.exists(name))
        self.assertFalse(os.path.isdir(os.path.dirname(default_storage.path(name))))
        self.assertFalse(move_temp_images(page))

    def test_admin_save_moves_images(self):
        admin = User.objects.create_superuser("admin", "a@a.test", "x")
        self.client.force_login(admin)
        location = self.client.post(UPLOAD_URL, {"file": image_file()}).json()["location"]
        response = self.client.post(
            "/admin/flatpages/flatpage/add/",
            {
                "url": "/nova/", "title": "Nova", "content": f'<p><img src="{location}"></p>',
                "sites": [Site.objects.get_current().pk], "template_name": "", "registration_required": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        page = FlatPage.objects.get(url="/nova/")
        self.assertIn(f"/uploaded/flatpages/{page.pk}/foto-bonita.png", page.content)

    def test_delete_removes_folder(self):
        page = self.make_page()
        name = default_storage.save(f"flatpages/{page.pk}/a.png", ContentFile(b"x"))
        with self.captureOnCommitCallbacks(execute=True):
            page.delete()
        self.assertFalse(default_storage.exists(name))
        self.assertFalse(os.path.isdir(os.path.dirname(default_storage.path(name))))


class RenderTests(MediaTestCase):
    def test_page_is_sanitized(self):
        # conteúdo gravado sem passar pelo admin (ex.: fixture) também é sanitizado na exibição
        self.make_page(content='<p>oi</p><script>alert(1)</script>')
        response = self.client.get("/pages/sobre/")
        self.assertContains(response, "<p>oi</p>alert(1)")
        self.assertNotContains(response, "<script>")


class AdminPageTests(TestCase):
    def test_add_page_uses_editor(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@a.test", "x"))
        response = self.client.get("/admin/flatpages/flatpage/add/")
        self.assertContains(response, "geonode_flatpages_editor/js/image_upload.js")
        self.assertContains(response, "flatpagesEditorImageUpload")
        # a configuração do widget é serializada em JSON no atributo data-mce-conf
        self.assertIn(json.dumps(UPLOAD_URL)[1:-1], response.content.decode())


class AppOrderCheckTests(TestCase):
    def test_ok(self):
        self.assertEqual(check_app_order(None), [])

    def test_ignores_non_string_installed_apps(self):
        # o GeoNode acrescenta objetos Celery ao INSTALLED_APPS (geonode/apps.py) depois de carregar os apps;
        # mock.patch troca o setting sem repovoar o registro de apps, como acontece no GeoNode
        with mock.patch.object(settings, "INSTALLED_APPS", tuple(settings.INSTALLED_APPS) + (object(),)):
            self.assertEqual(check_app_order(None), [])

    def test_wrong_order(self):
        installed = [a for a in settings.INSTALLED_APPS if a != "geonode_flatpages_editor"]
        installed.insert(installed.index("django.contrib.flatpages"), "geonode_flatpages_editor")
        with self.settings(INSTALLED_APPS=installed):
            self.assertEqual([e.id for e in check_app_order(None)], ["flatpages_editor.E002"])
