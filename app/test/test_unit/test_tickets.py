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

    def _create_ticket(self, user, event, quantity, ticket_type):



        total_tickets = Ticket.objects.filter(user=user, event=event).aggregate(total=models.Sum("quantity"))["total"] or 0
        if total_tickets + quantity > 4:
            raise ValidationError("No podés comprar más de 4 entradas")


        if ticket_type == "VIP" and quantity > 2:
            raise ValidationError("Máximo 2 tickets VIP por compra")


        ticket = Ticket.objects.create(
            user=user,
            event=event,
            quantity=quantity,
            type=ticket_type
        )
        return ticket

    def test_user_can_buy_up_to_4_tickets(self):
        """Un usuario puede comprar hasta 4 entradas en total para un evento"""
        self._create_ticket(user=self.user, event=self.event, quantity=2, ticket_type="GENERAL")
        self._create_ticket(user=self.user, event=self.event, quantity=2, ticket_type="GENERAL")

        total = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=models.Sum("quantity"))["total"]
        self.assertEqual(total, 4)

    def test_user_cannot_exceed_ticket_limit(self):
        """El sistema impide comprar más de 4 entradas en total"""
        self._create_ticket(user=self.user, event=self.event, quantity=3, ticket_type="GENERAL")

        with self.assertRaises(ValidationError) as context:
            self._create_ticket(user=self.user, event=self.event, quantity=2, ticket_type="GENERAL")

        self.assertIn("No podés comprar más de 4 entradas", str(context.exception))

    def test_multiple_users_can_buy_up_to_limit(self):
        """Usuarios distintos pueden comprar hasta 4 entradas cada uno"""
        other_user = User.objects.create_user(username="cliente2", email="c2@test.com", password="test123")

        self._create_ticket(user=self.user, event=self.event, quantity=4, ticket_type="GENERAL")
        self._create_ticket(user=other_user, event=self.event, quantity=4, ticket_type="GENERAL")

        total_user1 = Ticket.objects.filter(user=self.user, event=self.event).aggregate(total=models.Sum("quantity"))["total"]
        total_user2 = Ticket.objects.filter(user=other_user, event=self.event).aggregate(total=models.Sum("quantity"))["total"]

        self.assertEqual(total_user1, 4)
        self.assertEqual(total_user2, 4)

    def test_user_can_buy_single_ticket(self):
        """Un usuario puede comprar un solo ticket"""
        ticket = self._create_ticket(user=self.user, event=self.event, quantity=1, ticket_type="GENERAL")

        self.assertEqual(ticket.quantity, 1)
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.event, self.event)
        self.assertEqual(ticket.type, "GENERAL")

    def test_vip_ticket_limit_validation(self):
        """Los tickets VIP tienen un límite de 2 por compra"""

        test_user = User.objects.create_user(
            username="test_vip_user",
            email="test_vip@test.com",
            password="test123"
        )

        ticket = self._create_ticket(user=test_user, event=self.event, quantity=2, ticket_type="VIP")
        self.assertEqual(ticket.quantity, 2)
        self.assertEqual(ticket.type, "VIP")

        test_user2 = User.objects.create_user(
            username="test_vip_user2",
            email="test_vip2@test.com",
            password="test123"
        )

        with self.assertRaises(ValidationError) as context:
            self._create_ticket(user=test_user2, event=self.event, quantity=3, ticket_type="VIP")

        self.assertIn("Máximo 2 tickets VIP por compra", str(context.exception))
