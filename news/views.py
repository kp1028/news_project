import os
import requests

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Article, CustomUser, Newsletter, Publisher
from .serializers import serialize_article, serialize_articles_to_xml


def home(request):
    """
    Displays home page.
    """
    return render(request, "news/home.html")


def register(request):
    """
    Creates new user accounts.
    """
    if request.user.is_authenticated:
        return redirect("home")

    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        role = (request.POST.get("role", "") or "").strip().lower()

        allowed_roles = [CustomUser.READER, CustomUser.JOURNALIST, CustomUser.EDITOR]

        if not username:
            error = "Username is required."
        elif not password1:
            error = "Password is required."
        elif password1 != password2:
            error = "Passwords do not match."
        elif role not in allowed_roles:
            error = "Please choose a role."
        elif CustomUser.objects.filter(username=username).exists():
            error = "That username is already taken."
        else:
            CustomUser.objects.create_user(
                username=username,
                password=password1,
                role=role,
            )
            return redirect("login")

    return render(request, "news/register.html", {"error": error})


def is_editor_user(user):
    """
    Checks if user is editor.
    """
    return user.is_authenticated and str(getattr(user, "role", "")).lower() == CustomUser.EDITOR


def is_journalist_user(user):
    """
    Checks if user is journalist.
    """
    return user.is_authenticated and str(getattr(user, "role", "")).lower() == CustomUser.JOURNALIST


def is_reader_user(user):
    """
    Checks if user is reader/
    """
    return user.is_authenticated and str(getattr(user, "role", "")).lower() == CustomUser.READER


def post_to_x(article):
    """
    Posts article to X.
    """
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        return False

    url = "https://api.twitter.com/2/tweets"
    headers = {"Authorization": f"Bearer {token}"}

    text = f"{article.title}\n\n{article.content}"
    payload = {"text": text[:270]}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        return r.status_code in (200, 201)
    except Exception:
        return False


def email_subscribers(article):
    """
    Sends email about new article.
    """
    subscribers = CustomUser.objects.filter(role=CustomUser.READER).filter(
        Q(subscribed_publishers=article.publisher)
        | Q(subscribed_journalists=article.journalist)
    ).distinct()

    emails = [u.email for u in subscribers if u.email]
    if not emails:
        return

    subject = f"New Article Approved: {article.title}"
    message = f"{article.title}\n\n{article.content}"

    from_email = os.environ.get("DEFAULT_FROM_EMAIL") or "webmaster@localhost"
    send_mail(subject, message, from_email, emails, fail_silently=True)


@login_required(login_url="/login/")
def review_articles(request):
    """
    Lets editor review articles.
    """
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    articles = Article.objects.filter(approved=False).order_by("-created_at")
    return render(request, "news/editor_article_list.html", {"articles": articles})


@login_required(login_url="/login/")
def approve_article(request, pk):
    """
    Approves an article so it can be published
    """
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        article.approved = True
        article.save()

        email_subscribers(article)
        post_to_x(article)

        return redirect("review_articles")

    return render(request, "news/editor_article_approve.html", {"article": article})


@login_required(login_url="/login/")
def create_article(request):
    """
    Lets journalist create a new article.
    """
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    publishers = Publisher.objects.all().order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        error = None
        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        elif not publisher:
            error = "Publisher is required."

        if error:
            return render(
                request,
                "news/journalist_article_create.html",
                {
                    "publishers": publishers,
                    "error": error,
                    "title": title,
                    "content": content,
                    "publisher_id": publisher_id,
                },
            )

        Article.objects.create(
            title=title,
            content=content,
            publisher=publisher,
            journalist=request.user,
            approved=False,
        )

        return redirect("journalist_articles")

    return render(request, "news/journalist_article_create.html", {"publishers": publishers})


@login_required(login_url="/login/")
def articles(request):
    qs = Article.objects.filter(approved=True).order_by("-created_at")
    return render(request, "news/article_list.html", {"articles": qs})


@login_required(login_url="/login/")
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk, approved=True)
    return render(request, "news/article_detail.html", {"article": article})


@login_required(login_url="/login/")
def get_articles(request):
    user = request.user

    if not is_reader_user(user):
        return HttpResponseForbidden("Forbidden")

    publisher_ids = list(user.subscribed_publishers.values_list("id", flat=True))
    journalist_ids = list(user.subscribed_journalists.values_list("id", flat=True))

    qs = (
        Article.objects.filter(approved=True)
        .filter(Q(publisher_id__in=publisher_ids) | Q(journalist_id__in=journalist_ids))
        .distinct()
        .order_by("-created_at")
    )

    fmt = request.GET.get("format", "json").lower()

    if fmt == "xml":
        xml = serialize_articles_to_xml(qs)
        return HttpResponse(xml, content_type="application/xml")

    data = [serialize_article(a) for a in qs]
    return JsonResponse({"articles": data})


@login_required(login_url="/login/")
def journalist_articles(request):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    qs = Article.objects.filter(journalist=request.user).order_by("-created_at")
    return render(request, "news/journalist_article_list.html", {"articles": qs})


@login_required(login_url="/login/")
def journalist_article_edit(request, pk):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    article = get_object_or_404(Article, pk=pk, journalist=request.user)
    publishers = Publisher.objects.all().order_by("name")
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        else:
            article.title = title
            article.content = content
            article.publisher = publisher
            article.approved = False
            article.save()
            return redirect("journalist_articles")

    return render(
        request,
        "news/journalist_article_edit.html",
        {"article": article, "publishers": publishers, "error": error},
    )


@login_required(login_url="/login/")
def journalist_article_delete(request, pk):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    article = get_object_or_404(Article, pk=pk, journalist=request.user)

    if request.method == "POST":
        article.delete()
        return redirect("journalist_articles")

    return render(request, "news/journalist_article_delete.html", {"article": article})


@login_required(login_url="/login/")
def editor_articles(request):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    qs = Article.objects.all().order_by("-created_at")
    return render(request, "news/editor_article_manage_list.html", {"articles": qs})


@login_required(login_url="/login/")
def editor_article_edit(request, pk):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    article = get_object_or_404(Article, pk=pk)
    publishers = Publisher.objects.all().order_by("name")
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")
        approved = request.POST.get("approved") == "on"

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        else:
            article.title = title
            article.content = content
            article.publisher = publisher
            article.approved = approved
            article.save()
            return redirect("editor_articles")

    return render(
        request,
        "news/editor_article_edit.html",
        {"article": article, "publishers": publishers, "error": error},
    )


@login_required(login_url="/login/")
def editor_article_delete(request, pk):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        article.delete()
        return redirect("editor_articles")

    return render(request, "news/editor_article_delete.html", {"article": article})


@login_required(login_url="/login/")
def journalist_newsletters(request):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    qs = Newsletter.objects.filter(journalist=request.user).order_by("-created_at")
    return render(request, "news/journalist_newsletter_list.html", {"newsletters": qs})


@login_required(login_url="/login/")
def create_newsletter(request):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    publishers = Publisher.objects.all().order_by("name")
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        else:
            Newsletter.objects.create(
                title=title,
                content=content,
                publisher=publisher,
                journalist=request.user,
            )
            return redirect("journalist_newsletters")

    return render(
        request,
        "news/journalist_newsletter_create.html",
        {"publishers": publishers, "error": error},
    )


@login_required(login_url="/login/")
def journalist_newsletter_edit(request, pk):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    newsletter = get_object_or_404(Newsletter, pk=pk, journalist=request.user)
    publishers = Publisher.objects.all().order_by("name")
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        else:
            newsletter.title = title
            newsletter.content = content
            newsletter.publisher = publisher
            newsletter.save()
            return redirect("journalist_newsletters")

    return render(
        request,
        "news/journalist_newsletter_edit.html",
        {"newsletter": newsletter, "publishers": publishers, "error": error},
    )


@login_required(login_url="/login/")
def journalist_newsletter_delete(request, pk):
    if not is_journalist_user(request.user):
        return HttpResponseForbidden("Forbidden")

    newsletter = get_object_or_404(Newsletter, pk=pk, journalist=request.user)

    if request.method == "POST":
        newsletter.delete()
        return redirect("journalist_newsletters")

    return render(
        request,
        "news/journalist_newsletter_delete.html",
        {"newsletter": newsletter},
    )


@login_required(login_url="/login/")
def editor_newsletters(request):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    qs = Newsletter.objects.all().order_by("-created_at")
    return render(request, "news/editor_newsletter_manage_list.html", {"newsletters": qs})


@login_required(login_url="/login/")
def editor_newsletter_edit(request, pk):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    newsletter = get_object_or_404(Newsletter, pk=pk)
    publishers = Publisher.objects.all().order_by("name")
    error = None

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        publisher_id = request.POST.get("publisher")

        publisher = None
        if publisher_id:
            publisher = get_object_or_404(Publisher, pk=publisher_id)

        if not title:
            error = "Title is required."
        elif not content:
            error = "Content is required."
        else:
            newsletter.title = title
            newsletter.content = content
            newsletter.publisher = publisher
            newsletter.save()
            return redirect("editor_newsletters")

    return render(
        request,
        "news/editor_newsletter_edit.html",
        {"newsletter": newsletter, "publishers": publishers, "error": error},
    )


@login_required(login_url="/login/")
def editor_newsletter_delete(request, pk):
    if not is_editor_user(request.user):
        return HttpResponseForbidden("Forbidden")

    newsletter = get_object_or_404(Newsletter, pk=pk)

    if request.method == "POST":
        newsletter.delete()
        return redirect("editor_newsletters")

    return render(
        request,
        "news/editor_newsletter_delete.html",
        {"newsletter": newsletter},
    )


@login_required(login_url="/login/")
def publisher_list(request):
    publishers = Publisher.objects.all().order_by("name")
    return render(request, "news/publisher_list.html", {"publishers": publishers})


@login_required(login_url="/login/")
@user_passes_test(is_editor_user)
def publisher_create(request):
    error = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        if not name:
            error = "Name is required."
        elif Publisher.objects.filter(name=name).exists():
            error = "That publisher already exists."
        else:
            Publisher.objects.create(name=name)
            return redirect("publisher_list")

    return render(request, "news/publisher_create.html", {"error": error})