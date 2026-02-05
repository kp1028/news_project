from django.test import TestCase
from django.urls import reverse

from .models import Article, CustomUser, Publisher


class ApiArticlesTests(TestCase):
    def setUp(self):
        self.pub1 = Publisher.objects.create(name="pub1")
        self.pub2 = Publisher.objects.create(name="pub2")

        self.j1 = CustomUser.objects.create_user(username="journalist1", password="pass", role="journalist")
        self.j2 = CustomUser.objects.create_user(username="journalist2", password="pass", role="journalist")

        self.r1 = CustomUser.objects.create_user(username="reader1", password="pass", role="reader")
        self.r2 = CustomUser.objects.create_user(username="reader2", password="pass", role="reader")

        self.a1 = Article.objects.create(
            title="A1",
            content="C1",
            publisher=self.pub1,
            journalist=self.j1,
            approved=True,
        )
        self.a2 = Article.objects.create(
            title="A2",
            content="C2",
            publisher=self.pub2,
            journalist=self.j2,
            approved=True,
        )
        self.a3 = Article.objects.create(
            title="A3",
            content="C3",
            publisher=self.pub2,
            journalist=self.j1,
            approved=False,
        )

    def test_reader_gets_only_subscribed_articles(self):
        self.r1.subscribed_publishers.add(self.pub1)
        self.r1.subscribed_journalists.add(self.j2)

        self.client.login(username="reader1", password="pass")
        url = reverse("get_articles")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        titles = sorted([a["title"] for a in data["articles"]])

        self.assertEqual(titles, ["A1", "A2"])

    def test_unapproved_articles_not_returned(self):
        self.r2.subscribed_publishers.add(self.pub2)
        self.r2.subscribed_journalists.add(self.j1)

        self.client.login(username="reader2", password="pass")
        url = reverse("get_articles")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        titles = [a["title"] for a in data["articles"]]

        self.assertIn("A2", titles)
        self.assertNotIn("A3", titles)

    def test_non_reader_forbidden(self):
        self.client.login(username="journalist1", password="pass")
        url = reverse("get_articles")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 403)

    def test_xml_format(self):
        self.r1.subscribed_publishers.add(self.pub1)
        self.client.login(username="reader1", password="pass")

        url = reverse("get_articles") + "?format=xml"
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertIn("application/xml", res["Content-Type"])
        self.assertIn(b"<articles>", res.content)

    def test_no_subscriptions_returns_empty_list(self):
        self.client.login(username="reader1", password="pass")
        url = reverse("get_articles")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["articles"], [])
