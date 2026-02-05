from django.contrib.auth.models import AbstractUser
from django.db import models


class Publisher(models.Model):
    """
    Stores publisher information.
    """
    name = models.CharField(max_length=255, unique=True)

    editors = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publishers_as_editor",
        limit_choices_to={"role": "editor"},
    )

    journalists = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publishers_as_journalist",
        limit_choices_to={"role": "journalist"},
    )

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """
    Stores information about a user.
    """
    READER = "reader"
    JOURNALIST = "journalist"
    EDITOR = "editor"

    ROLE_CHOICES = [
        (READER, "Reader"),
        (JOURNALIST, "Journalist"),
        (EDITOR, "Editor"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=READER)

    subscribed_publishers = models.ManyToManyField(
        Publisher,
        blank=True,
        related_name="subscribers",
    )

    subscribed_journalists = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="journalist_subscribers",
        limit_choices_to={"role": JOURNALIST},
    )

    published_articles = models.ManyToManyField(
        "Article",
        blank=True,
        related_name="independent_publishers",
    )

    published_newsletters = models.ManyToManyField(
        "Newsletter",
        blank=True,
        related_name="independent_publishers",
    )

    def __str__(self):
        return self.username


class Article(models.Model):
    """
    Stores information about a news article.
    """
    title = models.CharField(max_length=255)
    content = models.TextField()

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="articles",
    )

    journalist = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles_written",
        limit_choices_to={"role": CustomUser.JOURNALIST},
    )

    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Newsletter(models.Model):
    """
    Stores newsletter subscriptions.
    """
    title = models.CharField(max_length=255)
    content = models.TextField()

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="newsletters",
    )

    journalist = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="newsletters_written",
        limit_choices_to={"role": CustomUser.JOURNALIST},
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
