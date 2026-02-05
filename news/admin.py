from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Article, CustomUser, Newsletter, Publisher


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role", "subscribed_publishers", "subscribed_journalists", "published_articles", "published_newsletters")}),
    )


admin.site.register(Publisher)
admin.site.register(Article)
admin.site.register(Newsletter)