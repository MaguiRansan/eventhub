import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from app.models import Event, User


class EventModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="test123",
            is_organizer=True,
        )

    def test_event_new_with_valid_data(self):
        """Test que verifica la creación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)


        success, result = Event.new(
            title="Nuevo evento",
            description="Descripción del nuevo evento",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
        )


        self.assertTrue(success)


        self.assertIsInstance(result, Event)


        self.assertEqual(result.title, "Nuevo evento")
        self.assertEqual(result.description, "Descripción del nuevo evento")
        self.assertEqual(result.organizer, self.organizer)


        saved_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(saved_event.description, "Descripción del nuevo evento")
        self.assertEqual(saved_event.organizer, self.organizer)

    def test_event_new_with_invalid_data(self):
        """Test que verifica que Event.new() retorna errores con datos inválidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)


        success, errors = Event.new(
            title="",
            description="Descripción válida",
            scheduled_at=scheduled_at,
            organizer=self.organizer,
        )


        self.assertFalse(success)


        self.assertIsInstance(errors, dict)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un titulo")

    def test_event_validation_past_date(self):
        """Test que verifica que no se pueden crear eventos en fechas pasadas"""
        past_date = timezone.now() - datetime.timedelta(days=1)


        errors = Event.validate(
            title="Evento pasado",
            description="Evento con fecha pasada",
            scheduled_at=past_date
        )


        self.assertIn("scheduled_at", errors)
        self.assertEqual(errors["scheduled_at"], "La fecha del evento debe ser en el futuro")

    def test_event_validation_negative_price(self):
        """Test que verifica la validación de tickets negativos usando Event.validate()"""
        future_date = timezone.now() + datetime.timedelta(days=7)


        errors = Event.validate(
            title="Evento con tickets negativos",
            description="Evento de prueba",
            scheduled_at=future_date,
            general_tickets=-5
        )


        self.assertIn("general_tickets", errors)
        self.assertEqual(errors["general_tickets"], "Ingrese una cantidad válida de tickets generales")

    def test_event_validation_negative_vip_tickets(self):
        """Test que verifica la validación de tickets VIP negativos"""
        future_date = timezone.now() + datetime.timedelta(days=7)

        errors = Event.validate(
            title="Evento con tickets VIP negativos",
            description="Evento de prueba",
            scheduled_at=future_date,
            vip_tickets=-3
        )


        self.assertIn("vip_tickets", errors)
        self.assertEqual(errors["vip_tickets"], "Ingrese una cantidad válida de tickets VIP")
