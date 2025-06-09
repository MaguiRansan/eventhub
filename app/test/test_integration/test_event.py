import datetime
from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from app.models import Event, User, Category, Venue


class BaseEventTestCase(TestCase):

    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )

        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )

        self.category1 = Category.objects.create(
            name="Música",
            description="Eventos musicales",
            is_active=True
        )
        self.category2 = Category.objects.create(
            name="Arte",
            description="Eventos artísticos",
            is_active=True
        )

        self.venue = Venue.objects.create(
            name="Teatro Principal",
            address="Calle Principal 123",
            city="Buenos Aires",
            capacity=1000,
            contact="info@teatro.com",
            organizer=self.organizer
        )

        self.event1 = Event.objects.create(
            title="Concierto de Rock",
            description="Descripción del concierto",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal('100.00'),
            vip_price=Decimal('200.00'),
            general_tickets_total=500,
            general_tickets_available=500,
            vip_tickets_total=100,
            vip_tickets_available=100,
        )
        self.event1.categories.add(self.category1)

        self.event2 = Event.objects.create(
            title="Exposición de Arte",
            description="Descripción de la exposición",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal('50.00'),
            vip_price=Decimal('100.00'),
            general_tickets_total=200,
            general_tickets_available=200,
            vip_tickets_total=50,
            vip_tickets_available=50,
        )
        self.event2.categories.add(self.category2)

        self.client = Client()


class EventsListViewTest(BaseEventTestCase):

    def test_events_view_with_login(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/events.html")
        events = response.context["events"]
        self.assertEqual(len(events), 2)
        self.assertFalse(response.context["user_is_organizer"])
        self.assertContains(response, "Concierto de Rock")

    def test_events_view_with_organizer_login(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_is_organizer"])
        self.assertContains(response, "Crear Evento")

    def test_events_view_without_login(self):
        response = self.client.get(reverse("events"))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('events')}")

    def test_events_view_filtering(self):
        self.client.login(username="regular", password="password123")

        with self.subTest("Filtrar por categoría"):
            response = self.client.get(reverse("events") + f"?categoria={self.category1.pk}")
            self.assertEqual(len(response.context["events"]), 1)
            self.assertEqual(response.context["events"][0].id, self.event1.pk)

        with self.subTest("Filtrar por venue"):
            response = self.client.get(reverse("events") + f"?venue={self.venue.pk}")
            self.assertEqual(len(response.context["events"]), 2)

        with self.subTest("Filtrar eventos pasados"):
            past_event = Event.objects.create(
                title="Evento Pasado",
                description="Evento que ya ocurrió",
                scheduled_at=timezone.now() - datetime.timedelta(days=1),
                organizer=self.organizer,
                venue=self.venue,
                general_price=Decimal('75.00'),
                vip_price=Decimal('150.00'),
                general_tickets_total=100,
                general_tickets_available=100,
                vip_tickets_total=25,
                vip_tickets_available=25,
            )
            response = self.client.get(reverse("events") + "?mostrar_pasados=true")
            self.assertEqual(len(response.context["events"]), 1)
            self.assertEqual(response.context["events"][0].id, past_event.pk)


class EventDetailViewTest(BaseEventTestCase):

    def test_event_detail_view_with_login(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_detail.html")
        self.assertEqual(response.context["event"].id, self.event1.pk)
        self.assertContains(response, "Concierto de Rock")

    def test_event_detail_view_with_organizer(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_edit"])
        self.assertContains(response, "Editar")

    def test_event_detail_view_rating_form(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))

        self.assertIn("form", response.context)
        self.assertIn("rating_to_edit", response.context)

    def test_event_detail_view_without_login(self):
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('event_detail', args=[self.event1.pk])}")

    def test_event_detail_view_with_invalid_id(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[999]))
        self.assertEqual(response.status_code, 404)