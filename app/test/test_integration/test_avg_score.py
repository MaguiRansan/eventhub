import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from app.models import Event, Venue, User, Ticket, Rating
from django.db import IntegrityError 
from django.db.models import Avg, DecimalField 

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

        # Crear venue con organizer 
        self.venue = Venue.objects.create(
            name="Venue de Prueba",
            address="Calle Falsa 123",
            city="Ciudad Test", # Asegúrate de que este campo existe en tu modelo Venue
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


class EventAverageRatingTest(BaseEventTestCase):
    """Tests para verificar el cálculo del promedio de calificaciones de eventos."""

    def setUp(self):
        super().setUp()
        # Asegurarse de que el evento ya ocurrió para poder calificarlo
        self.event1.scheduled_at = timezone.now() - datetime.timedelta(days=1)
        self.event1.save()
        # Asegurarse de que los usuarios regulares tienen un ticket para el evento1
        Ticket.objects.create(
            user=self.regular_user,
            event=self.event1,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='REGULAR-USER-TICKET'
        )
        Ticket.objects.create(
            user=self.another_regular_user,
            event=self.event1,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='ANOTHER-USER-TICKET'
        )

    def test_initial_average_rating_is_none(self):
        """Verifica que el promedio de calificación es None si no hay calificaciones."""
        self.assertIsNone(self.event1.average_rating)
        self.assertEqual(self.event1.total_ratings_count, 0)

    def test_add_single_rating_updates_average(self):
        """Añadir una sola calificación debe reflejarse en el promedio."""
        self.client.login(username="regular", password="password123")
        rating_data = {
            'title': 'Muy bueno',
            'score': 4,
            'comment': 'Un evento decente.',
        }
        self.client.post(reverse("event_detail", args=[self.event1.id]), rating_data)
        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, 4.0)
        self.assertEqual(self.event1.total_ratings_count, 1)

    def test_add_multiple_ratings_updates_average_correctly(self):
        """Añadir múltiples calificaciones de diferentes usuarios debe calcular el promedio correctamente."""
        # Usuario 1 califica con 5
        self.client.login(username="regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Fantástico', 'score': 5, 'comment': 'Me encantó!'
        })
        self.client.logout()

        # Usuario 2 califica con 3
        self.client.login(username="another_regular", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Regular', 'score': 3, 'comment': 'Podría mejorar.'
        })
        self.client.logout()

        # Asegúrate de que el evento esté actualizado con las nuevas calificaciones
        self.event1.refresh_from_db()
        # Promedio: (5 + 3) / 2 = 4.0
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'))
        self.assertEqual(self.event1.total_ratings_count, 2)

        # Agregamos más calificaciones simulando el flujo completo de compra de ticket y luego calificación
        temp_user1 = User.objects.create_user(username="temp_user1", email="temp1@test.com", password="password123")
        Ticket.objects.create(user=temp_user1, event=self.event1, quantity=1, type='GENERAL', payment_confirmed=True, ticket_code='TEMP-USER1-TICKET')
        self.client.login(username="temp_user1", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Genial', 'score': 4, 'comment': 'Super!'
        })
        self.client.logout()

        temp_user2 = User.objects.create_user(username="temp_user2", email="temp2@test.com", password="password123")
        Ticket.objects.create(user=temp_user2, event=self.event1, quantity=1, type='GENERAL', payment_confirmed=True, ticket_code='TEMP-USER2-TICKET')
        self.client.login(username="temp_user2", password="password123")
        self.client.post(reverse("event_detail", args=[self.event1.id]), {
            'title': 'Malo', 'score': 2, 'comment': 'No me gustó.'
        })
        self.client.logout()

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('3.5'))
        self.assertEqual(self.event1.total_ratings_count, 4)

    def test_edit_rating_updates_average(self):
        """Editar una calificación existente debe recalcular el promedio."""
        Rating.objects.create(event=self.event1, user=self.regular_user, title='Inicial', score=5)
        Rating.objects.create(event=self.event1, user=self.another_regular_user, title='Otro', score=3)

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0')) 
        self.assertEqual(self.event1.total_ratings_count, 2)

        self.client.login(username="regular", password="password123")
        
        # Obtenemos la calificación para editar
        regular_user_rating = Rating.objects.get(user=self.regular_user, event=self.event1)
        updated_rating_data = {
            'title': 'Actualizado',
            'score': 1, 
            'comment': 'Cambio mi opinión.',
            'rating_id': regular_user_rating.id, 
        }
        self.client.post(reverse("event_detail", args=[self.event1.id]), updated_rating_data)

        self.event1.refresh_from_db()
        # Nuevo promedio: (1 + 3) / 2 = 2.0
        self.assertAlmostEqual(self.event1.average_rating, Decimal('2.0'))
        self.assertEqual(self.event1.total_ratings_count, 2)


    def test_delete_rating_updates_average(self):
        """Eliminar una calificación debe recalcular el promedio."""
        # Agregamos algunas calificaciones iniciales
        rating1 = Rating.objects.create(event=self.event1, user=self.regular_user, title='Rating 1', score=5)
        rating2 = Rating.objects.create(event=self.event1, user=self.another_regular_user, title='Rating 2', score=3)

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'))
        self.assertEqual(self.event1.total_ratings_count, 2)

        # Loguear como el usuario que creó la primera calificación
        self.client.login(username="regular", password="password123")
        
        # Ahora eliminamos la primera calificación
        response = self.client.post(reverse("rating_delete", args=[self.event1.id, rating1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("event_detail", args=[self.event1.id]))

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('3.0'))
        self.assertEqual(self.event1.total_ratings_count, 1)

    def test_delete_all_ratings_sets_average_to_none(self):
        """Eliminar todas las calificaciones debe dejar el promedio como None."""
        # Creamos las calificaciones
        self.client.login(username="regular", password="password123")
        rating1 = Rating.objects.create(event=self.event1, user=self.regular_user, title='Rating 1', score=5)
        self.client.logout()

        self.client.login(username="another_regular", password="password123")
        rating2 = Rating.objects.create(event=self.event1, user=self.another_regular_user, title='Rating 2', score=3)
        self.client.logout()

        self.event1.refresh_from_db()
        self.assertAlmostEqual(self.event1.average_rating, Decimal('4.0'))
        self.assertEqual(self.event1.total_ratings_count, 2)

        # Eliminar el primer rating (logueado como regular user)
        self.client.login(username="regular", password="password123")
        self.client.post(reverse("rating_delete", args=[self.event1.id, rating1.id]))
        self.client.logout()

        # Eliminar el segundo rating (logueado como another_regular_user)
        self.client.login(username="another_regular", password="password123")
        self.client.post(reverse("rating_delete", args=[self.event1.id, rating2.id]))

        self.event1.refresh_from_db()
        self.assertIsNone(self.event1.average_rating)
        self.assertEqual(self.event1.total_ratings_count, 0)