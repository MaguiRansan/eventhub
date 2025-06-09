import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from app.models import Event, User, Category, Rating

class EventRatingModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        self.regular_user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="password123"
        )
        self.regular_user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="password123"
        )
        self.regular_user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="password123"
        )
        self.regular_user4 = User.objects.create_user( 
            username="user4", email="user4@example.com", password="password123"
        )

        self.event_for_ratings = Event.objects.create(
            title="Evento con Calificaciones",
            description="Descripción del evento para calificar",
            scheduled_at=timezone.now() - datetime.timedelta(days=1),
            organizer=self.organizer,
        )

    def test_initial_average_rating_and_count(self):
        """Verifica que el promedio es None y el conteo es 0 cuando no hay calificaciones."""
        self.assertIsNone(self.event_for_ratings.average_rating, "El promedio inicial debe ser None.")
        self.assertEqual(self.event_for_ratings.total_ratings_count, 0, "El conteo inicial debe ser 0.")


    def test_average_rating_with_one_rating(self):
        """Verifica el promedio y el conteo con una sola calificación."""
        Rating.objects.create(
            event=self.event_for_ratings, user=self.regular_user1, score=4, title="Buen evento", comment="Me gustó mucho."
        )
        self.event_for_ratings.refresh_from_db()
        self.assertEqual(self.event_for_ratings.average_rating, Decimal('4.0'), "El promedio debe ser 4.0 con una calificación.")


    def test_average_rating_with_multiple_ratings(self):
        """Verifica el promedio y el conteo con múltiples calificaciones (resultado entero)."""
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Excelente", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=3, title="Regular", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=4, title="Bueno", comment="")

        self.event_for_ratings.refresh_from_db()
        self.assertEqual(self.event_for_ratings.average_rating, Decimal('4.0'), "El promedio debe ser 4.0 con calificaciones 5, 3, 4.")


    def test_average_rating_with_decimal_result(self):
        """Verifica el promedio con un resultado decimal."""
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Genial", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=4, title="Bueno", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=5, title="Increíble", comment="")

        self.event_for_ratings.refresh_from_db()
        self.assertAlmostEqual(self.event_for_ratings.average_rating, Decimal('4.6666666666666665'), places=10, msg="El promedio debe ser 4.666... con resultado decimal.")


    def test_average_rating_after_deleting_rating(self):
        """Verifica que el promedio se actualiza después de eliminar una calificación."""
        rating1 = Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Excelente", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=3, title="Regular", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=4, title="Bueno", comment="")
        self.event_for_ratings.refresh_from_db()

        rating1.delete() 
        self.event_for_ratings.refresh_from_db()
        self.assertEqual(self.event_for_ratings.average_rating, Decimal('3.5'), "El promedio debe ser 3.5 después de eliminar una calificación.")


    def test_average_rating_after_all_ratings_deleted(self):
        """Verifica que el promedio y el conteo se actualizan a None y 0 después de eliminar todas las calificaciones."""
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user1, score=5, title="Excelente", comment="")
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user2, score=3, title="Regular", comment="")
 
        Rating.objects.create(event=self.event_for_ratings, user=self.regular_user3, score=4, title="Bueno", comment="")

        self.event_for_ratings.refresh_from_db()

        Rating.objects.filter(event=self.event_for_ratings).delete()
        self.event_for_ratings.refresh_from_db()

        self.assertIsNone(self.event_for_ratings.average_rating, "El promedio debe ser None después de eliminar todas las calificaciones.")
        self.assertEqual(self.event_for_ratings.total_ratings_count, 0, "El conteo total de calificaciones debe ser 0 después de eliminar todas las calificaciones.") 