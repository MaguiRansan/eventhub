from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, Ticket, User


class TicketPurchaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="comprador", password="12345")
        
        future_date = timezone.now() + timedelta(days=7)  
        
        cls.event = Event.objects.create(
            title="Evento agotado",
            general_tickets_available=0,
            vip_tickets_available=0,
            general_price=100,
            vip_price=200,
            scheduled_at=future_date,
            organizer=cls.user,
        )

    def test_no_se_puede_comprar_ticket_general_si_evento_agotado(self):
        self.client.login(username="comprador", password="12345")
        
        response = self.client.post(
            reverse("ticket_purchase", args=[self.event.id]),
            data={
                "type": Ticket.TicketType.GENERAL,
                "quantity": 1,
                "card_number": "1234567890123456",
                "expiration_date": "12/30",
                "cvv": "123",
                "save_card": False,
            },
            follow=True,
        )
        
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0, "No se encontraron mensajes en la respuesta")
        
        error_message = str(messages[0]).lower()
        self.assertIn("revisá los campos ingresados", error_message,
                    f"Se esperaba mensaje sobre campos inválidos, se obtuvo: '{error_message}'")

    def test_no_se_puede_comprar_ticket_vip_si_evento_agotado(self):
        self.client.login(username="comprador", password="12345")
        
        response = self.client.post(
            reverse("ticket_purchase", args=[self.event.id]),
            data={
                "type": Ticket.TicketType.VIP,
                "quantity": 1,
                "card_number": "1234567890123456",
                "expiration_date": "12/30",
                "cvv": "123",
                "save_card": False,
            },
            follow=True,
        )
        
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0, "No se encontraron mensajes en la respuesta")
        
        error_message = str(messages[0]).lower()
        self.assertIn("revisá los campos ingresados", error_message,
                    f"Se esperaba mensaje sobre campos inválidos, se obtuvo: '{error_message}'")
