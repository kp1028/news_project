from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver


@receiver(post_migrate)
def create_groups_and_permissions(sender, **kwargs):
    try:
        news_config = apps.get_app_config("news")
    except Exception:
        return

    create_permissions(news_config, verbosity=0)

    reader_group, _ = Group.objects.get_or_create(name="Reader")
    editor_group, _ = Group.objects.get_or_create(name="Editor")
    journalist_group, _ = Group.objects.get_or_create(name="Journalist")

    perms = Permission.objects.filter(content_type__app_label="news")

    def add_perms(group, codenames):
        group.permissions.set(list(perms.filter(codename__in=codenames)))

    reader_codenames = [
        "view_article",
        "view_newsletter",
    ]

    editor_codenames = [
        "view_article",
        "change_article",
        "delete_article",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ]

    journalist_codenames = [
        "add_article",
        "view_article",
        "change_article",
        "delete_article",
        "add_newsletter",
        "view_newsletter",
        "change_newsletter",
        "delete_newsletter",
    ]

    add_perms(reader_group, reader_codenames)
    add_perms(editor_group, editor_codenames)
    add_perms(journalist_group, journalist_codenames)


@receiver(post_save)
def assign_group_by_role(sender, instance, created=False, **kwargs):
    if sender._meta.label_lower != "news.customuser":
        return

    role = (instance.role or "").lower()
    instance.groups.clear()

    if role == "reader":
        group = Group.objects.filter(name="Reader").first()
        if group:
            instance.groups.add(group)
        instance.published_articles.clear()
        instance.published_newsletters.clear()

    elif role == "editor":
        group = Group.objects.filter(name="Editor").first()
        if group:
            instance.groups.add(group)
        instance.subscribed_publishers.clear()
        instance.subscribed_journalists.clear()
        instance.published_articles.clear()
        instance.published_newsletters.clear()

    elif role == "journalist":
        group = Group.objects.filter(name="Journalist").first()
        if group:
            instance.groups.add(group)
        instance.subscribed_publishers.clear()
        instance.subscribed_journalists.clear()
