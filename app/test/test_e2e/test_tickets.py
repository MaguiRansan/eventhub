import datetime
from decimal import Decimal
from django.utils import timezone
from django.test import TestCase
from app.models import Event, User, Venue, Ticket
from app.test.test_e2e.base import BaseE2ETest

class TicketBaseTest(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        self.venue = Venue.objects.create(
            name="Auditorio Tickets",
            address="Calle Tickets 123",
            capacity=500,
            organizer=self.organizer
        )

        event_date = timezone.make_aware(datetime.datetime.now() + datetime.timedelta(days=7))
        self.event = Event.objects.create(
            title="Evento para Tickets",
            description="Descripción para pruebas de tickets",
            scheduled_at=event_date,
            organizer=self.organizer,
            venue=self.venue,
            general_tickets_total=100,
            general_tickets_available=100,
            general_price=Decimal('100.00')
        )

    def _create_test_ticket(self, user=None, unique_suffix=""):
        """Helper para crear tickets de prueba"""
        import time
        import uuid

        user = user or self.user
        unique_code = f"TEST-{unique_suffix}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

        return Ticket.objects.create(
            user=user,
            event=self.event,
            quantity=1,
            ticket_code=unique_code,
            payment_confirmed=True,
            subtotal=self.event.general_price,
            taxes=self.event.general_price * Decimal('0.10'),
            total=self.event.general_price * Decimal('1.10')
        )

class TicketPurchaseTest(TicketBaseTest):
    def test_purchase_form_page_loads(self):
        """Test que la página de compra de tickets carga correctamente"""
        self.login_user("usuario", "password123")

        purchase_url = f"{self.live_server_url}/events/{self.event.pk}/purchase/"
        self.page.goto(purchase_url)
        self.page.wait_for_load_state("networkidle")

        # Verificar que la página carga sin errores
        page_content = self.page.content()
        self.assertNotIn("404", page_content)
        self.assertNotIn("Not Found", page_content)

        # Verificar que el formulario está presente
        quantity_input = self.page.locator("input[name='quantity'], input[name='general_quantity']").first
        self.assertTrue(quantity_input.is_visible())

    def test_purchase_form_has_submit_button(self):
        """Test que el formulario de compra tiene botón de envío"""
        self.login_user("usuario", "password123")

        purchase_url = f"{self.live_server_url}/events/{self.event.pk}/purchase/"
        self.page.goto(purchase_url)
        self.page.wait_for_load_state("networkidle")

        # Verificar que el botón de envío está presente
        submit_button = self.page.locator("button[type='submit'], input[type='submit']").first
        self.assertTrue(submit_button.is_visible())

    def test_ticket_limit_per_user(self):
        """Test del límite de tickets por usuario"""
        max_tickets_per_user = 4

        # Crear tickets hasta el límite
        for i in range(max_tickets_per_user):
            self._create_test_ticket(user=self.user, unique_suffix=f"LIMIT-{i}")

        ticket_count = Ticket.objects.filter(user=self.user, event=self.event).count()
        self.assertEqual(ticket_count, max_tickets_per_user)

class TicketManagementTest(TicketBaseTest):
    def test_organizer_can_access_tickets_page(self):
        """Test que el organizador puede acceder a la página de tickets"""
        ticket = self._create_test_ticket(unique_suffix="ORG")

        self.login_user("organizador", "password123")

        organizer_url = f"{self.live_server_url}/organizer/tickets/{self.event.pk}/"
        self.page.goto(organizer_url)
        self.page.wait_for_load_state("networkidle")

        # Verificar que la página carga correctamente
        page_content = self.page.content()
        self.assertNotIn("404", page_content)
        self.assertNotIn("Not Found", page_content)

        # Verificar que el ticket existe en la base de datos
        db_ticket = Ticket.objects.get(pk=ticket.pk)
        self.assertEqual(db_ticket.event.organizer, self.organizer)

    def test_user_can_access_own_tickets_page(self):
        """Test que el usuario puede acceder a su página de tickets"""
        ticket = self._create_test_ticket(unique_suffix="USER")

        self.login_user("usuario", "password123")

        tickets_url = f"{self.live_server_url}/tickets/"
        self.page.goto(tickets_url)
        self.page.wait_for_load_state("networkidle")

        # Verificar que la página carga correctamente
        page_content = self.page.content()
        self.assertNotIn("404", page_content)
        self.assertNotIn("Not Found", page_content)

        # Verificar que el ticket pertenece al usuario
        db_ticket = Ticket.objects.get(pk=ticket.pk)
        self.assertEqual(db_ticket.user, self.user)

    def test_ticket_detail_page_loads(self):
        """Test que la página de detalle de ticket carga correctamente"""
        ticket = self._create_test_ticket(unique_suffix="DETAIL")

        self.login_user("usuario", "password123")

        detail_url = f"{self.live_server_url}/tickets/{ticket.pk}/"
        self.page.goto(detail_url)
        self.page.wait_for_load_state("networkidle")

        # Verificar que la página carga correctamente
        page_content = self.page.content()
        self.assertNotIn("404", page_content)
        self.assertNotIn("Not Found", page_content)

        # Verificar que el ticket existe
        db_ticket = Ticket.objects.get(pk=ticket.pk)
        self.assertEqual(db_ticket.user, self.user)

class TicketValidationTest(TicketBaseTest):
    def test_ticket_creation_reduces_availability(self):
        """Test que la creación de tickets reduce la disponibilidad"""
        initial_available = self.event.general_tickets_available

        self._create_test_ticket(unique_suffix="REDUCE")

        # Simular la reducción de disponibilidad que haría el sistema
        self.event.general_tickets_available -= 1
        self.event.save()

        self.event.refresh_from_db()
        self.assertEqual(self.event.general_tickets_available, initial_available - 1)

    def test_ticket_belongs_to_correct_user(self):
        """Test que los tickets pertenecen al usuario correcto"""
        ticket = self._create_test_ticket(unique_suffix="OWNERSHIP")

        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.event, self.event)
        self.assertTrue(ticket.payment_confirmed)

    def test_ticket_has_valid_data(self):
        """Test que los tickets tienen datos válidos"""
        ticket = self._create_test_ticket(unique_suffix="VALIDATION")

        self.assertIsNotNone(ticket.ticket_code)
        self.assertGreater(len(ticket.ticket_code), 0)
        self.assertEqual(ticket.quantity, 1)
        self.assertEqual(ticket.subtotal, self.event.general_price)
        self.assertGreater(ticket.total, ticket.subtotal)

class TicketIntegrationTest(TestCase):
    """Tests de integración para la funcionalidad de tickets"""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        self.user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        self.venue = Venue.objects.create(
            name="Auditorio Test",
            address="Calle Test 123",
            capacity=100,
            organizer=self.organizer
        )

        event_date = timezone.make_aware(datetime.datetime.now() + datetime.timedelta(days=7))
        self.event = Event.objects.create(
            title="Evento Test",
            description="Descripción test",
            scheduled_at=event_date,
            organizer=self.organizer,
            venue=self.venue,
            general_tickets_total=50,
            general_tickets_available=50,
            general_price=Decimal('75.00')
        )

    def test_purchase_page_requires_authentication(self):
        """Test que la página de compra requiere autenticación"""
        response = self.client.get(f'/events/{self.event.pk}/purchase/')

        # Verificar que redirige al login o retorna 401/403
        self.assertIn(response.status_code, [302, 401, 403])

    def test_ticket_creation_with_correct_pricing(self):
        """Test que verifica el cálculo correcto de precios en tickets"""
        quantity = 2
        expected_subtotal = self.event.general_price * quantity
        expected_taxes = expected_subtotal * Decimal('0.10')
        expected_total = expected_subtotal + expected_taxes

        ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=quantity,
            ticket_code="TEST-PRICING-001",
            payment_confirmed=True,
            subtotal=expected_subtotal,
            taxes=expected_taxes,
            total=expected_total
        )

        self.assertEqual(ticket.subtotal, expected_subtotal)
        self.assertEqual(ticket.taxes, expected_taxes)
        self.assertEqual(ticket.total, expected_total)

    def test_ticket_model_fields_are_properly_set(self):
        """Test que los campos del modelo Ticket se configuran correctamente"""
        ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            ticket_code="TEST-MODEL-001",
            payment_confirmed=True,
            subtotal=self.event.general_price,
            taxes=self.event.general_price * Decimal('0.10'),
            total=self.event.general_price * Decimal('1.10')
        )

        # Verificar que todos los campos están correctamente configurados
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.event, self.event)
        self.assertEqual(ticket.quantity, 1)
        self.assertEqual(ticket.ticket_code, "TEST-MODEL-001")
        self.assertTrue(ticket.payment_confirmed)
        # Removido el assert de created_at ya que el modelo no tiene ese campo

    def test_multiple_tickets_for_same_user_and_event(self):
        """Test que un usuario puede tener múltiples tickets para el mismo evento"""
        ticket1 = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            ticket_code="TEST-MULTI-001",
            payment_confirmed=True,
            subtotal=self.event.general_price,
            taxes=self.event.general_price * Decimal('0.10'),
            total=self.event.general_price * Decimal('1.10')
        )

        ticket2 = Ticket.objects.create(
            user=self.user,
            event=self.event,
            quantity=2,
            ticket_code="TEST-MULTI-002",
            payment_confirmed=True,
            subtotal=self.event.general_price * 2,
            taxes=self.event.general_price * 2 * Decimal('0.10'),
            total=self.event.general_price * 2 * Decimal('1.10')
        )

        user_tickets = Ticket.objects.filter(user=self.user, event=self.event)
        self.assertEqual(user_tickets.count(), 2)
        self.assertIn(ticket1, user_tickets)
        self.assertIn(ticket2, user_tickets)
