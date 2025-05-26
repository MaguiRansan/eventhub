import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from app.models import Event, Venue, User

class BaseEventTestCase(TestCase):
    """Clase base con la configuración común para todos los tests de eventos"""

    def setUp(self):
        # Crear un usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )

        # Crear un usuario regular
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )

        # Crear venue con organizer - AUMENTAR CAPACIDAD PARA LOS TESTS
        self.venue = Venue.objects.create(
            name="Venue de Prueba",
            address="Calle Falsa 123",
            capacity=300,  # Aumentado de 100 a 300
            organizer=self.organizer
        )

        # Crear algunos eventos de prueba
        self.event1 = Event.objects.create(
            title="Evento 1",
            description="Descripción del evento 1",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal("100.00"),
            vip_price=Decimal("200.00"),
            general_tickets_total=100,
            vip_tickets_total=50,
            general_tickets_available=50,
            vip_tickets_available=20
        )

        self.event2 = Event.objects.create(
            title="Evento 2",
            description="Descripción del evento 2",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal("150.00"),
            vip_price=Decimal("250.00"),
            general_tickets_total=120,
            vip_tickets_total=60,
            general_tickets_available=40,
            vip_tickets_available=15
        )

        # Cliente para hacer peticiones
        self.client = Client()


class EventsListViewTest(BaseEventTestCase):
    """Tests para la vista de listado de eventos"""

    def test_events_view_with_login(self):
        """Test que verifica que la vista events funciona cuando el usuario está logueado"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/events.html")
        self.assertIn("events", response.context)
        self.assertEqual(len(response.context["events"]), 2)

        # Verificar orden por fecha
        events = list(response.context["events"])
        self.assertEqual(events[0].id, self.event1.id)
        self.assertEqual(events[1].id, self.event2.id)

    def test_events_view_with_organizer_login(self):
        """Test que verifica que la vista events funciona cuando el usuario es organizador"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_organizer)

    def test_events_view_without_login(self):
        """Test que verifica que la vista events redirige a login cuando el usuario no está logueado"""
        response = self.client.get(reverse("events"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))


class EventDetailViewTest(BaseEventTestCase):
    """Tests para la vista de detalle de un evento"""

    def test_event_detail_view_with_login(self):
        """Test que verifica que la vista event_detail funciona cuando el usuario está logueado"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_detail.html")
        self.assertEqual(response.context["event"].id, self.event1.id)

    def test_event_detail_view_without_login(self):
        """Test que verifica que la vista event_detail redirige a login cuando el usuario no está logueado"""
        response = self.client.get(reverse("event_detail", args=[self.event1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_event_detail_view_with_invalid_id(self):
        """Test que verifica que la vista event_detail devuelve 404 cuando el evento no existe"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[999]))
        self.assertEqual(response.status_code, 404)


class EventFormViewTest(BaseEventTestCase):
    """Tests para la vista del formulario de eventos"""

    def test_event_form_view_with_organizer(self):
        """Test que verifica que la vista event_form funciona cuando el usuario es organizador"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_form"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertTrue(response.wsgi_request.user.is_organizer)

    def test_event_form_view_with_regular_user(self):
        """Test que verifica que la vista event_form redirige cuando el usuario no es organizador"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_form"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("events"))

    def test_event_form_view_without_login(self):
        """Test que verifica que la vista event_form redirige a login cuando el usuario no está logueado"""
        response = self.client.get(reverse("event_form"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_event_form_edit_existing(self):
        """Test que verifica que se puede editar un evento existente"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_edit", args=[self.event1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["event"].id, self.event1.id)


class EventFormSubmissionTest(BaseEventTestCase):
    """Tests para la creación y edición de eventos mediante POST"""

    def test_event_form_post_create(self):
        """Test que verifica que se puede crear un evento mediante POST"""
        self.client.login(username="organizador", password="password123")

        event_data = {
            "title": "Nuevo Evento",
            "description": "Descripción del nuevo evento",
            "scheduled_date": (timezone.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
            "scheduled_time": "20:00",
            "venue": self.venue.id,
            "general_price": "100.00",
            "vip_price": "200.00",
            "general_tickets_total": 80,  # Reducido de 100 a 80
            "vip_tickets_total": 40,      # Reducido de 50 a 40
            "general_tickets_available": 50,
            "vip_tickets_available": 20
        }

        response = self.client.post(reverse("event_form"), event_data)

        if response.status_code == 200:
            print("Errores del formulario:", response.context['form'].errors)

        self.assertEqual(response.status_code, 302)

        # Verificar que se creó el evento
        self.assertTrue(Event.objects.filter(title="Nuevo Evento").exists())

        # Obtener el evento creado y verificar que redirecciona a su página de detalle
        nuevo_evento = Event.objects.get(title="Nuevo Evento")
        expected_url = reverse("event_detail", args=[nuevo_evento.id])
        self.assertEqual(response.url, expected_url)

    def test_event_form_post_edit(self):
        """Test que verifica que se puede editar un evento existente mediante POST"""
        self.client.login(username="organizador", password="password123")

        updated_data = {
            "title": "Evento 1 Actualizado",
            "description": "Nueva descripción",
            "scheduled_date": (timezone.now() + datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
            "scheduled_time": "21:00",
            "venue": self.venue.id,
            "general_price": "120.00",
            "vip_price": "220.00",
            "general_tickets_total": 90,  # Reducido de 120 a 90
            "vip_tickets_total": 50,      # Reducido de 60 a 50
            "general_tickets_available": 60,
            "vip_tickets_available": 25
        }

        response = self.client.post(
            reverse("event_edit", args=[self.event1.id]),
            updated_data
        )

        if response.status_code == 200:
            print("Errores del formulario:", response.context['form'].errors)

        self.assertEqual(response.status_code, 302)
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.title, "Evento 1 Actualizado")


class EventDeleteViewTest(BaseEventTestCase):
    """Tests para la eliminación de eventos"""

    def test_event_delete_with_organizer(self):
        """Test que verifica que un organizador puede eliminar un evento"""
        self.client.login(username="organizador", password="password123")
        event_id = self.event1.id
        response = self.client.post(reverse("event_delete", args=[event_id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(pk=event_id).exists())

    def test_event_delete_with_regular_user(self):
        """Test que verifica que un usuario regular no puede eliminar un evento"""
        self.client.login(username="regular", password="password123")
        event_id = self.event1.id
        response = self.client.post(reverse("event_delete", args=[event_id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(pk=event_id).exists())

    def test_event_delete_with_get_request(self):
        """Test que verifica que la vista redirecciona si se usa GET en lugar de POST"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_delete", args=[self.event1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(pk=self.event1.id).exists())

    def test_event_delete_nonexistent_event(self):
        """Test que verifica el comportamiento al intentar eliminar un evento inexistente"""
        self.client.login(username="organizador", password="password123")
        response = self.client.post(reverse("event_delete", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_event_delete_without_login(self):
        """Test que verifica que la vista redirecciona a login si el usuario no está autenticado"""
        response = self.client.post(reverse("event_delete", args=[self.event1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
