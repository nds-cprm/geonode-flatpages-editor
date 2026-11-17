# geonode-flatpages-editor

App Django que troca o editor das *flatpages* (`django.contrib.flatpages`) no admin do GeoNode por um TinyMCE com conteúdo restrito e upload de imagens.

- **Conteúdo restrito.** O editor só oferece texto, títulos (h2 a h4), listas, citação, links e imagens. O HTML é sanitizado com `bleach` ao salvar e de novo ao exibir (filtro `sanitize_flatpage`), então o conteúdo carregado por fixture ou direto no banco também é filtrado.
- **Upload de imagens.** As imagens são validadas com o Pillow (PNG, JPEG, GIF ou WebP, até 5 MB por padrão) e gravadas por página em `MEDIA_ROOT/flatpages/<id>/`. As imagens de uma página nova ficam em `flatpages/tmp/<uuid>/` e são movidas para a pasta da página quando ela é salva. Quando a página é apagada, a pasta dela é apagada junto.
- **Template de exibição.** `flatpages/default.html` estende `geonode_base.html`.

Ele usa o TinyMCE 5 do `django-tinymce`, que já vem com o GeoNode. O idioma do editor acompanha o idioma ativo do Django, e há tradução pt-BR.

Foi extraído do app `opengeosgb.flatpages_editor` do [OpenGeoSGB](https://github.com/nds-cprm/opengeosgb).

## Instalação num projeto GeoNode

1. No `requirements.txt`:

   ```text
   geonode-flatpages-editor @ git+https://github.com/nds-cprm/geonode-flatpages-editor@v0.1.0
   ```

2. Nos settings, o app entra **depois** de `django.contrib.flatpages`, porque substitui o admin dele. Um check do Django (`flatpages_editor.E002`) acusa a ordem errada.

   ```python
   if "django.contrib.flatpages" not in INSTALLED_APPS:
       INSTALLED_APPS += ("django.contrib.flatpages",)
   INSTALLED_APPS += ("geonode_flatpages_editor",)

   # opcional: só para servir as páginas sem rota própria
   # MIDDLEWARE += ("django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",)
   ```

   O `django.contrib.sites` e o `SITE_ID` já vêm configurados pelo GeoNode.

3. No `urls.py`, publique as páginas, por exemplo em `/pages/`:

   ```python
   from django.urls import include, path

   urlpatterns += [path("pages/", include("django.contrib.flatpages.urls"))]
   ```

   O upload de imagens não precisa de rota no projeto, porque fica no próprio admin: `/admin/flatpages/flatpage/upload-image/`, com o nome de rota `admin:flatpages_flatpage_upload_image`.

4. Rode `migrate`, que cria as tabelas de `django.contrib.flatpages` se ainda não existirem. O app não tem modelos próprios.

## Configuração

Todas as chaves são opcionais:

```python
FLATPAGES_EDITOR = {
    "UPLOAD_DIR": "flatpages",          # pasta das imagens dentro do MEDIA_ROOT
    "MAX_IMAGE_SIZE": 5 * 1024 * 1024,  # tamanho máximo da imagem, em bytes
    "TINYMCE_CONFIG": {"height": 600},  # mesclado sobre a configuração padrão do editor
}
```

Se você trocar `UPLOAD_DIR` com páginas já publicadas, as imagens antigas saem do HTML exibido, porque o sanitizador só aceita imagens em `MEDIA_URL/<UPLOAD_DIR>/` ou com endereço `http(s)://`.

O `TINYMCE_CONFIG` pode ampliar o editor, mas as tags fora da lista de `editor.ALLOWED_TAGS` continuam sendo removidas no servidor.

Para mudar a página de exibição, crie `templates/flatpages/default.html` no projeto. Os templates do projeto têm prioridade. Mantenha `{{ flatpage.content|sanitize_flatpage }}` (com `{% load flatpages_editor %}`).

## Permissões

O upload só aceita membros da equipe que tenham permissão de adicionar ou alterar flatpages, e exige o token CSRF. A função JavaScript `flatpagesEditorImageUpload` envia o token automaticamente.

## Containers somente leitura

As imagens são gravadas pelo `default_storage`. Com `read_only: true`, o `MEDIA_ROOT` precisa estar num volume gravável. No GeoNode Docker ele já está: `/mnt/volumes/statics/uploaded`, servido pelo nginx em `/uploaded/`.

## Migração a partir do `opengeosgb.flatpages_editor`

- As imagens continuam em `flatpages/<id>/`, então páginas e arquivos existentes servem sem mudança.
- No `INSTALLED_APPS`, troque `opengeosgb.flatpages_editor.apps.FlatpagesEditorConfig` por `geonode_flatpages_editor`.
- Remova a rota `opengeosgb/flatpages/` do `urls.py`. O upload passou para o admin.
- O rótulo do app mudou de `opengeosgb_flatpages` para `flatpages_editor`. Como não há modelos, não há migração a fazer.

## Desenvolvimento

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e . flake8 polib
python runtests.py            # aceita as opções do "manage.py test", ex.: -v 2
flake8
python scripts/compilemessages.py   # depois de editar locale/*/LC_MESSAGES/django.po
```

Os testes rodam sem o GeoNode: `tests/templates/geonode_base.html` substitui o template base.

## Pendências

- **Imagens órfãs.** Ficam sem uso as imagens enviadas para uma página nova que acabou não sendo salva (em `flatpages/tmp/`) e as que foram removidas do conteúdo de uma página. Falta um comando de limpeza, que pode ser agendado no Celery beat.

## Licença

GPL-3.0-or-later.
