import datetime
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, Rating, Ticket, User, Venue


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

        # Crear otro usuario regular para pruebas de calificaciones (para ratings múltiples)
        self.another_regular_user = User.objects.create_user(
            username="another_regular",
            email="another_regular@test.com",
            password="password123",
            is_organizer=False,
        )

        # Crear un tercer usuario regular para pruebas de calificaciones
        self.third_regular_user = User.objects.create_user(
            username="third_regular",
            email="third_regular@test.com",
            password="password123",
            is_organizer=False,
        )

        # Crear venue con organizer
        self.venue = Venue.objects.create(
            name="Venue de Prueba",
            address="Calle Falsa 123",
            city="Ciudad Test",
            capacity=300,
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


class EventAverageRatingIntegrationTest(BaseEventTestCase):
    """Test para verificar el cálculo del promedio de calificaciones de eventos a través de las vistas."""

    def setUp(self):
        super().setUp()
        self.event1.scheduled_at = timezone.now() - datetime.timedelta(days=1)
        self.event1.save()

        Ticket.objects.create(
            user=self.regular_user,
            event=self.event1,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='REGULAR-USER-TICKET-1'
        )
        Ticket.objects.create(
            user=self.another_regular_user,
            event=self.event1,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='ANOTHER-USER-TICKET-1'
        )
        Ticket.objects.create(
            user=self.third_regular_user,
            event=self.event1,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='THIRD-USER-TICKET-1'
        )


    def test_initial_average_rating_is_none_via_model(self):
        """Verifica que el promedio de calificación es None si no hay calificaciones"""
        self.assertIsNone(self.event1.average_rating, "El promedio inicial debe ser None sin calificaciones.")

    def test_add_single_rating_updates_average_via_view(self):
        """Añadir una sola calificación a través de la vista debe reflejarse en el promedio del evento."""
        self.client.login(username="regular", password="password123")
        rating_data = {
            'title': 'Muy bueno',
            'score': 4,
            'comment': 'Un evento decente.',
        }
        response = self.client.post(reverse("event_detail", args=[self.event1.id]), rating_data)
        self.assertEqual(response.status_code, 302, "La petición POST para agregar calificación debe redirigir.")

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'), "El promedio debe ser 4.0 con una calificación.")

    def test_add_multiple_ratings_updates_average_via_view(self):
        """Añadir múltiples calificaciones a través de la vista debe calcular el promedio correctamente."""
        self.client.login(username="regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Fantástico', 'score': 5, 'comment': 'Me encantó!'
        })
        self.client.logout()

        self.client.login(username="another_regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Regular', 'score': 3, 'comment': 'Podría mejorar.'
        })
        self.client.logout()

        self.client.login(username="third_regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Genial', 'score': 4, 'comment': 'Super!'
        })
        self.client.logout()

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'), "El promedio debe ser 4.0 con múltiples calificaciones.")

    def test_edit_rating_updates_average_via_view(self):
        """Editar una calificación existente a través de la vista debe recalcular el promedio."""
        initial_rating_user1 = Rating.objects.create(event=self.event1, user=self.regular_user, title='Inicial', score=5)
        Rating.objects.create(event=self.event1, user=self.another_regular_user, title='Otro', score=3)
        self.event1.refresh_from_db() 

        self.client.login(username="regular", password="password123")

        updated_rating_data = {
            'title': 'Actualizado',
            'score': 1,
            'comment': 'Cambio mi opinión.',
            'rating_id': initial_rating_user1.id, 
        }
        response = self.client.post(reverse("event_detail", args=[self.event1.id]), updated_rating_data)
        self.assertEqual(response.status_code, 302, "La petición POST para editar calificación debe redirigir.")

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('2.0'), "El promedio debe ser 2.0 después de editar una calificación.")

    def test_delete_rating_updates_average_via_view(self):
        """Eliminar una calificación a través de la vista debe recalcular el promedio."""
        rating_to_delete = Rating.objects.create(event=self.event1, user=self.regular_user, title='Rating a borrar', score=5)
        Rating.objects.create(event=self.event1, user=self.another_regular_user, title='Rating existente', score=3)
        self.event1.refresh_from_db() 

        self.client.login(username="regular", password="password123")

        response = self.client.post(reverse("rating_delete", args=[self.event1.id, rating_to_delete.id]))
        self.assertEqual(response.status_code, 302, "La petición POST para eliminar calificación debe redirigir.")

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('3.0'), "El promedio debe ser 3.0 después de eliminar una calificación.")

    def test_delete_all_ratings_sets_average_to_none_via_views(self):
        """Eliminar todas las calificaciones a través de las vistas debe dejar el promedio como None."""
        self.client.login(username="regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {'title': 'R1', 'score': 5, 'comment': ''})
        self.client.logout()

        self.client.login(username="another_regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {'title': 'R2', 'score': 3, 'comment': ''})
        self.client.logout()

        r1_obj = Rating.objects.get(event=self.event1, user=self.regular_user)
        r2_obj = Rating.objects.get(event=self.event1, user=self.another_regular_user)

        self.event1.refresh_from_db()
        self.assertEqual(self.event1.total_ratings_count, 2, "El conteo inicial debe ser 2 antes de eliminar todas.")
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'), "El promedio inicial debe ser 4.0 antes de eliminar todas.")

        self.client.login(username="regular", password="password123")
        self.client.post(reverse("rating_delete", args=[self.event1.id, r1_obj.id]))
        self.client.logout()

        self.client.login(username="another_regular", password="password123")
        self.client.post(reverse("rating_delete", args=[self.event1.id, r2_obj.id]))
        self.client.logout()

        self.event1.refresh_from_db()
        self.assertIsNone(self.event1.average_rating, "El promedio debe ser None después de eliminar todas las calificaciones.")
        self.assertEqual(self.event1.total_ratings_count, 0, "El conteo total debe ser 0 después de eliminar todas las calificaciones.")