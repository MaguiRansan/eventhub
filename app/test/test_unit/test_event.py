import datetime
from decimal import Decimal 
from django.test import TestCase
from django.utils import timezone
from app.models import Event, User, Category, Rating 


class EventModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        # Usuarios adicionales para los tests de calificación
        self.regular_user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="password123"
        )
        self.regular_user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="password123"
        )
        self.regular_user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="password123"
        )
        self.category1 = Category.objects.create(name='Música')
        self.category2 = Category.objects.create(name='Deportes')

        # Evento específico para los tests de calificación 
        self.event_for_ratings = Event.objects.create(
            title="Evento con Calificaciones",
            description="Descripción del evento para calificar",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )

    def test_event_creation(self):
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )
        """Test que verifica la creación correcta de eventos"""
        self.assertEqual(event.title, "Evento de prueba")
        self.assertEqual(event.description, "Descripción del evento de prueba")
        self.assertEqual(event.organizer, self.organizer)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_validate_with_valid_data(self):
        """Test que verifica la validación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("Título válido", "Descripción válida", scheduled_at)
        self.assertEqual(errors, {})

    def test_event_validate_with_empty_title(self):
        """Test que verifica la validación de eventos con título vacío"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("", "Descripción válida", scheduled_at)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un título")

    def test_event_validate_with_empty_description(self):
        """Test que verifica la validación de eventos con descripción vacía"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate("Título válido", "", scheduled_at)
        self.assertIn("description", errors)
        self.assertEqual(errors["description"], "Por favor ingrese una descripción")

    def test_event_new_with_valid_data(self):
        """Test que verifica la creación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        success, event = Event.new(
            title="Nuevo evento",
            description="Descripción del nuevo evento",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
            general_tickets=100,
            vip_tickets=50,
            categories=[self.category1, self.category2]
        )

        self.assertTrue(success)
        self.assertIsInstance(event, Event)

        # Verificar que el evento fue creado en la base de datos
        new_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(new_event.pk, event.pk)
        self.assertEqual(new_event.description, "Descripción del nuevo evento")
        self.assertEqual(new_event.organizer, self.organizer)
        self.assertAlmostEqual(new_event.scheduled_at, scheduled_at, delta=datetime.timedelta(seconds=1))
        self.assertEqual(new_event.general_tickets_total, 100)
        self.assertEqual(new_event.vip_tickets_total, 50)
        self.assertEqual(new_event.general_tickets_available, 100)
        self.assertEqual(new_event.vip_tickets_available, 50)
        self.assertEqual(new_event.categories.count(), 2)
        self.assertTrue(self.category1 in new_event.categories.all())
        self.assertTrue(self.category2 in new_event.categories.all())


    def test_event_new_with_invalid_data(self):
        """Test que verifica que no se crean eventos con datos inválidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        initial_count = Event.objects.count()

        # Intentar crear evento con título vacío
        success, errors = Event.new(
            title="",
            description="Descripción del evento",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
        )

        self.assertFalse(success)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un título")

        # Verificar que no se creó ningún evento nuevo
        self.assertEqual(Event.objects.count(), initial_count)

    def test_event_update(self):
        """Test que verifica la actualización de eventos"""
        new_title = "Título actualizado"
        new_description = "Descripción actualizada"
        new_scheduled_at = timezone.now() + datetime.timedelta(days=3)

        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        event.update(
            title=new_title,
            description=new_description,
            scheduled_at=new_scheduled_at,
            organizer=self.organizer,
        )

        # Recargar el evento desde la base de datos
        updated_event = Event.objects.get(pk=event.pk)

        self.assertEqual(updated_event.title, new_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at.time(), new_scheduled_at.time())

    def test_event_update_partial(self):
        """Test que verifica la actualización parcial de eventos"""
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
        )

        original_title = event.title
        original_scheduled_at = event.scheduled_at
        new_description = "Solo la descripción ha cambiado"

        event.update(
            title=None,
            description=new_description,
            scheduled_at=None,
            organizer=None,
        )

        # Recargar el evento desde la base de datos
        updated_event = Event.objects.get(pk=event.pk)

        # Verificar que solo cambió la descripción
        self.assertEqual(updated_event.title, original_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at, original_scheduled_at)

    def test_initial_average_rating_and_count(self):
        """Verifica que el promedio es None y el conteo es 0 cuando no hay calificaciones."""
        self.assertIsNone(self.event_for_ratings.average_rating)
        self.assertEqual(self.event_for_ratings.total_ratings_count, 0)

    def test_average_rating_with_one_rating(self):
        """Verifica el promedio y el conteo con una sola calificación."""
        Rating.objects.create(
            event=self.event_for_ratings,
            user=self.regular_user1,
            score=4,
            title="Buen evento",
            comment="Me gustó mucho."
        )
        self.event_for_ratings.refresh_from_db()

        self.assertEqual(self.event_for_ratings.average_rating, Decimal('4.0'))
        self.assertEqual(self.event_for_ratings.total_ratings_count, 1)

    def test_average_rating_with_multiple_ratings(self):
        """Verifica el promedio y el conteo con múltiples calificaciones."""
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Excelente", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=3, title="Regular", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=4, title="Bueno", comment="")

        self.event_for_ratings.refresh_from_db()

        self.assertEqual(self.event_for_ratings.average_rating, Decimal('4.0'))
        self.assertEqual(self.event_for_ratings.total_ratings_count, 3)

    def test_average_rating_with_decimal_result(self):
        """Verifica el promedio con un resultado decimal."""
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Genial", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=4, title="Bueno", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=5, title="Increíble", comment="")

        self.event_for_ratings.refresh_from_db()

        self.assertAlmostEqual(self.event_for_ratings.average_rating, Decimal('4.6666666666666665'), places=10)
        self.assertEqual(self.event_for_ratings.total_ratings_count, 3)

    def test_average_rating_after_deleting_rating(self):
        """Verifica que el promedio y el conteo se actualizan después de eliminar una calificación."""
        rating1 = Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Excelente", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=3, title="Regular", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=4, title="Bueno", comment="")

        self.event_for_ratings.refresh_from_db()
        self.assertEqual(self.event_for_ratings.average_rating, Decimal('4.0'))
        self.assertEqual(self.event_for_ratings.total_ratings_count, 3)

        rating1.delete()
        self.event_for_ratings.refresh_from_db()

        self.assertEqual(self.event_for_ratings.average_rating, Decimal('3.5'))
        self.assertEqual(self.event_for_ratings.total_ratings_count, 2)