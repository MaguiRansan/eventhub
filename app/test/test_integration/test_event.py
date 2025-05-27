import datetime
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, User
from app.models import Event, User, Venue



class BaseEventTestCase(TestCase):
    """Clase base con la configuración común para todos los tests de eventos"""

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

        self.event1 = Event.objects.create(
            title="Evento 1",
            description="Descripción del evento 1",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        self.event2 = Event.objects.create(
            title="Evento 2",
            description="Descripción del evento 2",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
        )

        self.client = Client()

class EventsListViewTest(BaseEventTestCase):
    """Tests para la vista de listado de eventos"""

    def test_events_view_with_login(self):
        """Vista events con usuario autenticado"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/events.html")
        self.assertIn("events", response.context)
        self.assertEqual(len(response.context["events"]), 2)
        self.assertFalse(response.context["user_is_organizer"])

        events = list(response.context["events"])
        self.assertEqual(events[0].id, self.event1.id)
        self.assertEqual(events[1].id, self.event2.id)

    def test_events_view_with_organizer_login(self):
        """Vista events con organizador"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_is_organizer"])

    def test_events_view_without_login(self):
        """Sin login ⇒ redirige a login"""
        response = self.client.get(reverse("events"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))


class EventDetailViewTest(BaseEventTestCase):
    """Tests para la vista de detalle de un evento"""

    def test_event_detail_view_with_login(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_detail.html")
        self.assertEqual(response.context["event"].id, self.event1.id)

    def test_event_detail_view_without_login(self):
        response = self.client.get(reverse("event_detail", args=[self.event1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_event_detail_view_with_invalid_id(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[999]))
        self.assertEqual(response.status_code, 404)

class EventFormViewTest(BaseEventTestCase):
    """Tests para la vista del formulario de eventos"""

    def test_event_form_view_with_organizer(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_form"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertTrue(response.context["user_is_organizer"])

    def test_event_form_view_with_regular_user(self):
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_form"))
        self.assertRedirects(response, reverse("events"))

    def test_event_form_view_without_login(self):
        response = self.client.get(reverse("event_form"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_event_form_edit_existing(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_edit", args=[self.event1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertEqual(response.context["event"].id, self.event1.id)

class EventFormSubmissionTest(BaseEventTestCase):
    """Tests para la creación y edición de eventos mediante POST"""

def test_event_form_post_create(self):
    venue = Venue.objects.create(name="Salón Principal", location="Calle Falsa 123", capacity=100)
    event_data = {
        "title": "Nuevo Evento",
        "description": "Descripción del nuevo evento.",
        "scheduled_date": "2025-06-15",
        "scheduled_time": "18:00",
        "general_tickets_total": 50,
        "vip_tickets_total": 20,
        "general_price": "100.00",
        "vip_price": "200.00",
        "venue": venue.id,
    }
    response = self.client.post(reverse("event_create"), data=event_data)

    print(response.context["form"].errors)
    print(response.context["form"].non_field_errors())

    new_event = Event.objects.get(title="Nuevo Evento")
    self.assertRedirects(response, reverse("event_detail", args=[new_event.id]))


def test_event_form_post_edit(self):
    venue = Venue.objects.create(name="Salón B", location="Calle Verdadera 456", capacity=80)
    self.event1.venue = venue
    self.event1.save()

    updated_data = {
        "title": "Evento Editado",
        "description": "Descripción actualizada.",
        "scheduled_date": "2025-07-20",
        "scheduled_time": "20:00",
        "general_tickets_total": 60,
        "vip_tickets_total": 25,
        "general_price": "150.00",
        "vip_price": "250.00",
        "venue": venue.id,
    }
    response = self.client.post(reverse("event_edit", args=[self.event1.id]), data=updated_data)

    print(response.context["form"].errors)
    print(response.context["form"].non_field_errors())

    self.event1.refresh_from_db()
    self.assertRedirects(response, reverse("event_detail", args=[self.event1.id]))

class EventDeleteViewTest(BaseEventTestCase):
    """Tests para la eliminación de eventos"""

    def test_event_delete_with_organizer(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.post(reverse("event_delete", args=[self.event1.id]))
        self.assertRedirects(response, reverse("events"))
        self.assertFalse(Event.objects.filter(pk=self.event1.id).exists())

    def test_event_delete_with_regular_user(self):
        self.client.login(username="regular", password="password123")
        response = self.client.post(reverse("event_delete", args=[self.event1.id]))
        self.assertRedirects(response, reverse("events"))
        self.assertTrue(Event.objects.filter(pk=self.event1.id).exists())

    def test_event_delete_with_get_request(self):
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_delete", args=[self.event1.id]))
        self.assertRedirects(response, reverse("event_detail", args=[self.event1.id]))
        self.assertTrue(Event.objects.filter(pk=self.event1.id).exists())

    def test_event_delete_nonexistent_event(self):
        self.client.login(username="organizador", password="password123")
        nonexistent_id = 9999
        response = self.client.post(reverse("event_delete", args=[nonexistent_id]))
        self.assertEqual(response.status_code, 404)

    def test_event_delete_without_login(self):
        response = self.client.post(reverse("event_delete", args=[self.event1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        self.assertTrue(Event.objects.filter(pk=self.event1.id).exists())
