import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from app.models import User, Event, Ticket, Venue

class TicketPurchaseIntegrationTest(TestCase):
    def setUp(self):

        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="12345",
            is_organizer=True
        )

        # Crear usuario comprador
        self.user = User.objects.create_user(
            username="comprador",
            email="comprador@test.com",
            password="12345"
        )

        # Crear venue con organizer
        self.venue = Venue.objects.create(
            name="Auditorio Central",
            address="Av. Siempre Viva 742",
            capacity=100,
            organizer=self.organizer
        )

        # Crear evento (sin capacity)
        self.event = Event.objects.create(
            title="Evento Integrado",
            description="Prueba de integración",
            scheduled_at=timezone.now() + datetime.timedelta(days=5),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal("100.00"),
            vip_price=Decimal("150.00"),
            general_tickets_available=100,
            vip_tickets_available=50
        )

        self.url = reverse("ticket_purchase", kwargs={"event_id": self.event.id})

    def test_puede_comprar_si_no_excede_limite(self):
        """Compra válida: el usuario tiene 2 entradas y pide 2 más"""
        self.client.login(username="comprador", password="12345")

        # Crear ticket previo de 2 entradas
        Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=2,
            type="GENERAL",
            ticket_code="TEST-123"
        )

        # Enviar POST para comprar 2 más
        response = self.client.post(self.url, {
            "quantity": 2,
            "type": "GENERAL",
            "accept_terms": True,
            "card_type": "VISA",
            "card_number": "1234567812345678",
            "expiry_date": "12/30",
            "cvv": "123",
            "card_holder": "Test User"
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Ya compraste")
        total_tickets = Ticket.objects.filter(
            user=self.user,
            event=self.event
        ).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 4)

    def test_no_puede_comprar_si_excede_4(self):
        """Compra inválida: ya tiene 4 entradas, intenta comprar 1 más"""
        self.client.login(username="comprador", password="12345")

        # Crear tickets previos: total 4 entradas
        Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=2,
            type="GENERAL",
            ticket_code="TEST-123"
        )
        Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=2,
            type="VIP",
            ticket_code="TEST-456"
        )

        # Intentar comprar 1 entrada más
        response = self.client.post(self.url, {
            "quantity": 1,
            "type": "GENERAL",
            "accept_terms": True,
            "card_type": "VISA",
            "card_number": "1234567812345678",
            "expiry_date": "12/30",
            "cvv": "123",
            "card_holder": "Test User"
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No podés comprar más de 4 entradas")
        total_tickets = Ticket.objects.filter(
            user=self.user,
            event=self.event
        ).aggregate(total=Sum('quantity'))['total']
        self.assertEqual(total_tickets, 4)

    def test_vip_ticket_limit_validation(self):
        """Los tickets VIP tienen un límite de 2 por compra"""
        self.client.login(username="comprador", password="12345")

        # Intentar comprar 3 tickets VIP (debería fallar)
        response = self.client.post(self.url, {
            "quantity": 3,
            "type": "VIP",
            "accept_terms": True,
            "card_type": "VISA",
            "card_number": "1234567812345678",
            "expiry_date": "12/30",
            "cvv": "123",
            "card_holder": "Test User"
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Máximo 2 tickets VIP por compra")
        self.assertEqual(Ticket.objects.filter(
            user=self.user,
            event=self.event,
            type="VIP"
        ).count(), 0)

    def test_successful_purchase_redirect(self):
        """Test que verifica la redirección después de una compra exitosa"""
        self.client.login(username="comprador", password="12345")

        response = self.client.post(self.url, {
            "quantity": 1,
            "type": "GENERAL",
            "accept_terms": True,
            "card_type": "VISA",
            "card_number": "1234567812345678",
            "expiry_date": "12/30",
            "cvv": "123",
            "card_holder": "Test User"
        }, follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("ticket_detail", args=[1])))

    def test_purchase_without_login(self):
        """Test que verifica que se redirige al login si el usuario no está autenticado"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
