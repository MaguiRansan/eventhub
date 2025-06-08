import datetime
from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
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
    """Tests para la vista de listado de eventos"""

    def test_events_view_with_login(self):
        """Test que verifica que la vista events funciona cuando el usuario está logueado"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("events"))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/events.html")
        self.assertEqual(len(response.context["events"]), 2)
        self.assertFalse(response.context["user_is_organizer"])
        self.assertContains(response, "Concierto de Rock")
        self.assertContains(response, "Exposición de Arte")

        events = list(response.context["events"])
        self.assertEqual(events[0].id, self.event1.pk)
        self.assertEqual(events[1].id, self.event2.pk)

    def test_events_view_with_organizer_login(self):
        """Test que verifica que la vista events funciona cuando el usuario es organizador"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("events"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_is_organizer"])
        self.assertContains(response, "Crear Evento")
        self.assertTrue(response.wsgi_request.user.is_organizer)

    def test_events_view_without_login(self):
        """Test que verifica la redirección cuando el usuario no está logueado"""
        response = self.client.get(reverse("events"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        
    def test_events_view_filtering(self):
        """Test que verifica los filtros de la vista de eventos"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("events") + "?categoria=" + str(self.category1.pk))
        self.assertEqual(len(response.context["events"]), 1)
        self.assertEqual(response.context["events"][0].id, self.event1.pk)
        response = self.client.get(reverse("events") + "?venue=" + str(self.venue.pk))
        self.assertEqual(len(response.context["events"]), 2)
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

    def test_events_view_filtering(self):
        """Test que verifica los filtros de la vista de eventos"""
        self.client.login(username="regular", password="password123")
        
       
        response = self.client.get(reverse("events") + "?categoria=" + str(self.category1.pk))
        self.assertEqual(len(response.context["events"]), 1)
        self.assertEqual(response.context["events"][0].id, self.event1.pk)
        
 
        response = self.client.get(reverse("events") + "?venue=" + str(self.venue.pk))
        self.assertEqual(len(response.context["events"]), 2)
        
       
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
    """Tests para la vista de detalle de un evento"""

    def test_event_detail_view_with_login(self):
        """Test que verifica que la vista event_detail funciona cuando el usuario está logueado"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_detail.html")
        self.assertEqual(response.context["event"].id, self.event1.pk)
        self.assertContains(response, "Concierto de Rock")
        self.assertContains(response, "Descripción del concierto")
        self.assertContains(response, "Música")

    def test_event_detail_view_with_organizer(self):
        """Test que verifica los permisos del organizador en la vista de detalle"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_edit"])
        self.assertContains(response, "Editar")
        self.assertContains(response, "Eliminar")

    def test_event_detail_view_rating_form(self):
        """Test que verifica el formulario de calificación en la vista de detalle"""
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
        
        self.assertIn("form", response.context)
        self.assertIsNotNone(response.context["form"])
        self.assertIn("rating_to_edit", response.context)

    def test_event_detail_view_without_login(self):
        """Test que verifica que la vista event_detail redirige a login cuando el usuario no está logueado"""
        response = self.client.get(reverse("event_detail", args=[self.event1.pk]))
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
        self.assertIn("form", response.context)
        self.assertIn("venues", response.context)
        self.assertIn("categories", response.context)
        self.assertTrue(response.wsgi_request.user.is_organizer)

    def test_event_form_edit_existing(self):
        """Test que verifica que se puede editar un evento existente"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_edit", args=[self.event1.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["event"].id, self.event1.pk)
        form_title = response.context.get("form_title", "")
        if not form_title and "event" in response.context:
            self.assertTrue(True)
        else:
            self.assertEqual(form_title, "Editar Evento")
        self.assertContains(response, self.event1.title)

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
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_edit", args=[self.event1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "app/event_form.html")
        self.assertEqual(response.context["event"].id, self.event1.id)


class EventFormSubmissionTest(BaseEventTestCase):
    """Tests para la creación y edición de eventos mediante POST"""

    def test_event_creation(self):
        """Test que verifica que se puede crear un evento mediante POST"""
        self.client.login(username="organizador", password="password123")
        
        event_data = {
            "title": "Nuevo Evento",
            "description": "Descripción del nuevo evento",
            "scheduled_date": (timezone.now() + datetime.timedelta(days=3)).date(),
            "scheduled_time": "14:30",
            "venue": self.venue.pk,
            "general_price": "150.00",
            "vip_price": "300.00",
            "general_tickets_total": "400",
            "vip_tickets_total": "50",
            "categories": [self.category1.pk, self.category2.pk],
        }
        
        response = self.client.post(reverse("event_form"), event_data)
        
        if response.status_code == 200:
            print("Errores del formulario:", response.context.get('form', {}).errors if response.context else "No context")
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(title="Nuevo Evento").exists())
        
        new_event = Event.objects.get(title="Nuevo Evento")
        self.assertEqual(new_event.organizer, self.organizer)
        self.assertEqual(new_event.general_tickets_available, 400)
        self.assertEqual(new_event.vip_tickets_available, 50)
        self.assertEqual(new_event.categories.count(), 2)

       
        expected_url = reverse("event_detail", args=[new_event.pk])
        self.assertEqual(response.url, expected_url)

    def test_event_edit(self):
        """Test que verifica que se puede editar un evento existente mediante POST"""
        self.client.login(username="organizador", password="password123")
        
        updated_data = {
            "title": "Concierto Actualizado",
            "description": "Nueva descripción",
            "scheduled_date": (timezone.now() + datetime.timedelta(days=5)).date(),
            "scheduled_time": "20:00",
            "venue": self.venue.pk,
            "general_price": "120.00",
            "vip_price": "250.00",
            "general_tickets_total": "600",
            "vip_tickets_total": "150",
            "categories": [self.category2.pk],
        }
        
        response = self.client.post(reverse("event_edit", args=[self.event1.pk]), updated_data)
        
        if response.status_code == 200:
            print("Errores del formulario:", response.context.get('form', {}).errors if response.context else "No context")
        
        self.assertEqual(response.status_code, 302)
        self.event1.refresh_from_db()
        
        self.assertEqual(self.event1.title, "Concierto Actualizado")
        self.assertTrue(self.event1.general_tickets_total == 600)
        self.assertTrue(self.event1.vip_tickets_total == 150)
        self.assertEqual(self.event1.categories.count(), 1)
        self.assertEqual(self.event1.categories.first().pk, self.category2.pk)

    def test_event_creation_with_invalid_data(self):
        """Test que verifica la validación de datos inválidos"""
        self.client.login(username="organizador", password="password123")
        
        invalid_data = {
            "title": "Evento Inválido",
            "description": "Descripción",
            "scheduled_date": (timezone.now() - datetime.timedelta(days=1)).date(),
            "scheduled_time": "14:30",
            "general_price": "100.00",
            "vip_price": "200.00",
            "general_tickets_total": "100",
            "vip_tickets_total": "20",
            "venue": self.venue.pk,
        }
        
        response = self.client.post(reverse("event_form"), invalid_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Evento Inválido").exists())
        self.assertContains(response, "La fecha del evento no puede estar en el pasado")


class EventDeleteViewTest(BaseEventTestCase):
    """Tests para la eliminación de eventos"""

    def test_event_delete_with_organizer(self):
        """Test que verifica que un organizador puede eliminar un evento"""
        self.client.login(username="organizador", password="password123")
        event_id = self.event1.pk
        response = self.client.post(reverse("event_delete", args=[event_id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("events"))
        self.assertFalse(Event.objects.filter(pk=event_id).exists())

    def test_event_delete_with_regular_user(self):
        """Test que verifica que un usuario regular no puede eliminar un evento"""
        self.client.login(username="regular", password="password123")
        event_id = self.event1.pk
        response = self.client.post(reverse("event_delete", args=[event_id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("events"))
        self.assertTrue(Event.objects.filter(pk=event_id).exists())

    def test_event_delete_with_get_request(self):
        """Test que verifica que la vista redirecciona si se usa GET en lugar de POST"""
        self.client.login(username="organizador", password="password123")
        response = self.client.get(reverse("event_delete", args=[self.event1.pk]))
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(pk=self.event1.pk).exists())

    def test_event_delete_nonexistent_event(self):
        """Test que verifica el comportamiento al intentar eliminar un evento inexistente"""
        self.client.login(username="organizador", password="password123")
        response = self.client.post(reverse("event_delete", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_event_delete_without_login(self):
        """Test que verifica que la vista redirecciona a login si el usuario no está autenticado"""
        response = self.client.post(reverse("event_delete", args=[self.event1.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))