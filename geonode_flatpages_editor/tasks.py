"""
Tarefa do Celery para a limpeza das imagens órfãs (editor.cleanup_orphan_images). O pacote não
depende do Celery: sem ele, este módulo não define a tarefa. Em projetos GeoNode, o Celery descobre
a tarefa sozinho (autodiscover_tasks) nos apps do INSTALLED_APPS; o agendamento fica no projeto
(CELERY_BEAT_SCHEDULE, ver o README).
"""
try:
    from celery import shared_task
except ImportError:  # pragma: no cover - sem Celery instalado
    shared_task = None

from .editor import cleanup_orphan_images

TASK_NAME = "geonode_flatpages_editor.cleanup_orphan_images"

if shared_task is not None:

    @shared_task(name=TASK_NAME, ignore_result=True)
    def cleanup_orphan_images_task(min_age_hours=None):
        """Apaga as imagens órfãs e devolve quantas foram apagadas."""
        return len(cleanup_orphan_images(min_age_hours=min_age_hours))
