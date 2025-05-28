from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from app.models import User, Event

class TicketE2ETest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="usuario_e2e",
            password="clave123",
            is_organizer=False
        )

        self.event = Event.objects.create(
            title="Evento agotado",
            description="Sin entradas disponibles",
            scheduled_at=timezone.now() + timedelta(days=5),
            general_tickets_total=10,
            general_tickets_available=0,  
            vip_tickets_total=5,
            vip_tickets_available=0, 
            general_price=100,
            vip_price=200,
            organizer=self.user
        )

    def test_no_permite_compra_si_evento_esta_agotado(self):
        self.client.login(username="usuario_e2e", password="clave123")

        url = reverse("ticket_purchase", args=[self.event.id])

        response = self.client.post(url, {
            "quantity": 1,
            "type": "GENERAL",
            "card_number": "1234123412341234",
            "expiry_date": "12/30",
            "cvv": "123",
            "card_type": "VISA",
            "card_holder": "Usuario Test",
            "accept_terms": "on",
            "save_card": False
        }, follow=True)

        self.assertContains(response, "Evento agotado", status_code=200)
