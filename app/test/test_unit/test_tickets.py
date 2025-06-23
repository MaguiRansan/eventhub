import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils import timezone

from app.models import Event, Ticket, User


class TicketLimitUnitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cliente",
            email="cliente@test.com",
            password="test123",
        )

        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="test123",
            is_organizer=True,
        )

        self.event = Event.objects.create(
            title="Recital Prueba",
            description="Evento de prueba para entradas",
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
            general_price=Decimal("50.00"),
            general_tickets_total=100,
            general_tickets_available=100,
            vip_price=Decimal("150.00"),
            vip_tickets_total=20,
            vip_tickets_available=20,
        )

    def test_user_can_buy_up_to_4_tickets(self):
        """Un usuario puede comprar hasta 4 entradas en total para un evento"""
        Ticket.create_ticket(user=self.user, event=self.event, quantity=2, ticket_type='GENERAL')
        Ticket.create_ticket(user=self.user, event=self.event, quantity=2, ticket_type='GENERAL')

        total = Ticket.objects.filter(user=self.user, event=self.event).aggregate(
            total=models.Sum("quantity")
        )["total"]
        self.assertEqual(total, 4)

    def test_user_cannot_exceed_ticket_limit(self):
        """El sistema impide comprar más de 4 entradas en total"""
        Ticket.create_ticket(user=self.user, event=self.event, quantity=3, ticket_type='GENERAL')

        with self.assertRaises(ValidationError) as context:
            Ticket.create_ticket(user=self.user, event=self.event, quantity=2, ticket_type='GENERAL')

        self.assertIn("No podés comprar más de 4 entradas para este evento", str(context.exception))

    def test_multiple_users_can_buy_up_to_limit(self):
        """Usuarios distintos pueden comprar hasta 4 entradas cada uno"""
        other_user = User.objects.create_user(
            username="cliente2",
            email="c2@test.com",
            password="test123"
        )

        Ticket.create_ticket(user=self.user, event=self.event, quantity=4, ticket_type='GENERAL')
        Ticket.create_ticket(user=other_user, event=self.event, quantity=4, ticket_type='GENERAL')

        total_user1 = Ticket.objects.filter(user=self.user, event=self.event).aggregate(
            total=models.Sum("quantity")
        )["total"]
        total_user2 = Ticket.objects.filter(user=other_user, event=self.event).aggregate(
            total=models.Sum("quantity")
        )["total"]

        self.assertEqual(total_user1, 4)
        self.assertEqual(total_user2, 4)

    def test_user_can_buy_single_ticket(self):
        """Un usuario puede comprar un solo ticket"""
        ticket = Ticket.create_ticket(user=self.user, event=self.event, quantity=1, ticket_type='GENERAL')

        self.assertEqual(ticket.quantity, 1)
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.event, self.event)
        self.assertEqual(ticket.type, 'GENERAL')

    def test_vip_ticket_limit_validation(self):
        """Los tickets VIP tienen un límite de 2 por compra"""
        with self.assertRaises(ValidationError) as context:
            Ticket.create_ticket(user=self.user, event=self.event, quantity=3, ticket_type='VIP')

        self.assertIn("Máximo 2 tickets VIP por compra", str(context.exception))

    def test_ticket_code_generation(self):
        """El código de ticket se genera automáticamente"""
        ticket = Ticket.create_ticket(user=self.user, event=self.event, quantity=1, ticket_type='GENERAL')

        self.assertIsNotNone(ticket.ticket_code)
        self.assertTrue(ticket.ticket_code.startswith('RECI'))
        self.assertEqual(len(ticket.ticket_code), 13)

    def test_pricing_calculation(self):
        """Los precios se calculan correctamente"""
        general_ticket = Ticket.create_ticket(
            user=self.user,
            event=self.event,
            quantity=2,
            ticket_type='GENERAL'
        )

        expected_subtotal = Decimal('50.00') * 2
        expected_taxes = expected_subtotal * Decimal('0.10')
        expected_total = expected_subtotal + expected_taxes

        self.assertEqual(general_ticket.subtotal, expected_subtotal)
        self.assertEqual(general_ticket.taxes, expected_taxes)
        self.assertEqual(general_ticket.total, expected_total)

    def test_available_tickets_decrease(self):
        """Las entradas disponibles disminuyen al comprar"""
        initial_general = self.event.general_tickets_available
        initial_vip = self.event.vip_tickets_available

        Ticket.create_ticket(user=self.user, event=self.event, quantity=3, ticket_type='GENERAL')


        self.event.refresh_from_db()

        self.assertEqual(self.event.general_tickets_available, initial_general - 3)
        self.assertEqual(self.event.vip_tickets_available, initial_vip)

    def test_insufficient_tickets_validation(self):
        """No se pueden comprar más entradas de las disponibles"""

        self.event.general_tickets_available = 2
        self.event.save()

        with self.assertRaises(ValidationError) as context:
            Ticket.create_ticket(user=self.user, event=self.event, quantity=3, ticket_type='GENERAL')

        self.assertIn("No hay suficientes entradas general disponibles", str(context.exception))
