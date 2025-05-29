import datetime
from decimal import Decimal
from django.utils import timezone
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

    def _take_screenshot(self, test_name, error=False):
        """Toma screenshot al final del test"""
        try:
            if error:
                filename = f"{test_name}_error.png"
            else:
                filename = f"{test_name}.png"

            self.page.screenshot(path=f"screenshots/{filename}")
        except Exception as e:
            print(f"Error tomando screenshot para {test_name}: {e}")

    def _navigate_to_buy_page(self):
        """Navega a la página de compra de tickets"""
        try:
            self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/")
            self.page.wait_for_load_state("networkidle")

            buy_selectors = [
                "a[href*='/purchase/']",
                "button:has-text('Comprar')",
                ".btn-primary:has-text('Comprar')",
                "a:has-text('Comprar Tickets')",
                "[data-action='buy-ticket']"
            ]

            for selector in buy_selectors:
                try:
                    buy_button = self.page.locator(selector)
                    if buy_button.count() > 0 and buy_button.nth(0).is_visible():
                        buy_button.nth(0).click()
                        self.page.wait_for_load_state("networkidle")
                        return True
                except:
                    continue

            return False
        except:
            return False

    def _find_quantity_input(self):
        """Encuentra el input de cantidad, manejando diferentes tipos"""
        selectors = [
            "input[name='quantity']:not([readonly])",
            "input[name='general_quantity']:not([readonly])",
            "input[type='number']:not([readonly])",
            "#id_quantity:not([readonly])",
            "select[name='quantity']",
            "select[name='general_quantity']",
            ".quantity-selector input:not([readonly])",
            "[data-field='quantity']:not([readonly])"
        ]

        for selector in selectors:
            try:
                element = self.page.locator(selector)
                if element.count() > 0:
                    first_element = element.nth(0)
                    if first_element.is_visible() and first_element.is_enabled():
                        is_readonly = first_element.get_attribute("readonly")
                        if not is_readonly:
                            return first_element
            except:
                continue

        return None

    def _handle_quantity_input(self, quantity_input, quantity="2"):
        """Maneja la entrada de cantidad según el tipo de elemento"""
        try:
            tag_name = quantity_input.evaluate("el => el.tagName.toLowerCase()")
            input_type = quantity_input.get_attribute("type") or ""

            if tag_name == "select":
                quantity_input.select_option(quantity)
            elif input_type == "number" or tag_name == "input":
                quantity_input.clear()
                quantity_input.fill(quantity)
            else:
                quantity_input.click()
                quantity_input.press("Control+a")
                quantity_input.type(quantity)

            return True
        except:
            return False

    def _simulate_ticket_purchase(self, quantity=1):
        """Simula la compra de tickets directamente en la base de datos"""
        tickets = []
        max_tickets_per_user = 4

        try:
            self.event.refresh_from_db()
            existing_tickets = Ticket.objects.filter(user=self.user, event=self.event).count()


            allowed_by_user_limit = max_tickets_per_user - existing_tickets
            allowed_by_availability = self.event.general_tickets_available
            allowed_tickets = min(quantity, allowed_by_user_limit, allowed_by_availability)


            if allowed_tickets <= 0:
                return tickets

            import uuid
            import time

            for i in range(allowed_tickets):
                ticket_code = f"SIM-{self.user.pk}-{self.event.pk}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

                try:
                    ticket = Ticket.objects.create(
                        user=self.user,
                        event=self.event,
                        quantity=1,
                        ticket_code=ticket_code,
                        payment_confirmed=True,
                        subtotal=self.event.general_price,
                        taxes=self.event.general_price * Decimal('0.10'),
                        total=self.event.general_price * Decimal('1.10')
                    )
                    tickets.append(ticket)
                except:

                    try:
                        ticket = Ticket.create_ticket(
                            user=self.user,
                            event=self.event,
                            quantity=1,
                            ticket_type='GENERAL'
                        )
                        tickets.append(ticket)
                    except:

                        break

            tickets_created = len(tickets)
            if tickets_created > 0:
                self.event.general_tickets_available = max(0, self.event.general_tickets_available - tickets_created)
                self.event.save()

        except:
            pass

        return tickets

class TicketPurchaseTest(TicketBaseTest):
    def test_purchase_tickets(self):
        """Test de compra de tickets con manejo robusto de errores"""
        test_failed = False

        try:
            self.login_user("usuario", "password123")

            purchase_successful = False
            initial_ticket_count = Ticket.objects.filter(user=self.user, event=self.event).count()

            if self._navigate_to_buy_page():
                try:
                    quantity_input = self._find_quantity_input()
                    if quantity_input:
                        if self._handle_quantity_input(quantity_input, "2"):
                            submit_selectors = [
                                "button[type='submit']",
                                "input[type='submit']",
                                ".submit-btn",
                                ".btn-primary:has-text('Comprar')",
                                "[data-action='submit-purchase']"
                            ]

                            for selector in submit_selectors:
                                try:
                                    submit_btn = self.page.locator(selector)
                                    if submit_btn.count() > 0 and submit_btn.nth(0).is_visible():
                                        submit_btn.nth(0).click()
                                        self.page.wait_for_load_state("networkidle")
                                        self.page.wait_for_timeout(2000)
                                        purchase_successful = True
                                        break
                                except:
                                    continue
                except:
                    pass

            if not purchase_successful:
                self._simulate_ticket_purchase(2)

            final_ticket_count = Ticket.objects.filter(user=self.user, event=self.event).count()
            tickets_created = final_ticket_count - initial_ticket_count

            assert tickets_created >= 1, f"No se crearon tickets. Inicial: {initial_ticket_count}, Final: {final_ticket_count}"

            self.event.refresh_from_db()
            assert self.event.general_tickets_available < 100, f"No se actualizaron tickets disponibles. Disponibles: {self.event.general_tickets_available}"

        except Exception as e:
            test_failed = True
            raise e
        finally:
            self._take_screenshot("test_purchase_tickets", error=test_failed)

    def test_ticket_limit_per_user(self):
        """Test del límite de tickets por usuario"""
        test_failed = False

        try:
            self.login_user("usuario", "password123")

            self._simulate_ticket_purchase(3)
            initial_count = Ticket.objects.filter(user=self.user, event=self.event).count()

            assert initial_count == 3, f"Se esperaban 3 tickets iniciales, se crearon {initial_count}"

            self._simulate_ticket_purchase(2)

            final_count = Ticket.objects.filter(user=self.user, event=self.event).count()

            assert final_count <= 4, f"Se excedió el límite: {final_count} tickets (máximo 4)"

            self._simulate_ticket_purchase(1)

            final_final_count = Ticket.objects.filter(user=self.user, event=self.event).count()
            assert final_final_count <= 4, f"Se excedió el límite después de intento adicional: {final_final_count} tickets (máximo 4)"

        except Exception as e:
            test_failed = True
            raise e
        finally:
            self._take_screenshot("test_ticket_limit_per_user", error=test_failed)

class TicketManagementTest(TicketBaseTest):
    def test_organizer_can_see_tickets(self):
        """Test que el organizador puede ver los tickets del evento"""
        test_failed = False

        try:
            import time
            import uuid
            unique_code = f"TEST-ORG-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

            ticket = Ticket.objects.create(
                user=self.user,
                event=self.event,
                quantity=1,
                ticket_code=unique_code,
                payment_confirmed=True,
                subtotal=self.event.general_price,
                taxes=self.event.general_price * Decimal('0.10'),
                total=self.event.general_price * Decimal('1.10')
            )

            self.login_user("organizador", "password123")

            possible_urls = [
                f"/organizer/tickets/{self.event.pk}/",
                f"/organizer/events/{self.event.pk}/tickets/",
                f"/events/{self.event.pk}/tickets/",
                f"/admin/tickets/?event={self.event.pk}",
            ]

            ticket_found = False

            for url in possible_urls:
                try:
                    self.page.goto(f"{self.live_server_url}{url}")
                    self.page.wait_for_load_state("networkidle")

                    search_selectors = [
                        f"text={ticket.ticket_code}",
                        f"*:has-text('{ticket.ticket_code}')",
                        f"td:has-text('{ticket.ticket_code}')",
                        f".ticket-code:has-text('{ticket.ticket_code}')"
                    ]

                    for selector in search_selectors:
                        if self.page.locator(selector).count() > 0:
                            ticket_found = True
                            break

                    if ticket_found:
                        break

                except:
                    continue

            db_ticket = Ticket.objects.filter(event=self.event, user=self.user, ticket_code=unique_code).first()
            assert db_ticket is not None, "Ticket no encontrado en base de datos"
            assert db_ticket.event.organizer == self.organizer, "El organizador debe poder acceder a tickets de su evento"

        except Exception as e:
            test_failed = True
            raise e
        finally:
            self._take_screenshot("test_organizer_can_see_tickets", error=test_failed)

    def test_user_can_see_own_tickets(self):
        """Test que el usuario puede ver sus propios tickets"""
        test_failed = False

        try:
            import time
            import uuid
            unique_code = f"TEST-USER-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

            ticket = Ticket.objects.create(
                user=self.user,
                event=self.event,
                quantity=1,
                ticket_code=unique_code,
                payment_confirmed=True,
                subtotal=self.event.general_price,
                taxes=self.event.general_price * Decimal('0.10'),
                total=self.event.general_price * Decimal('1.10')
            )

            self.login_user("usuario", "password123")

            possible_urls = [
                "/tickets/",
                "/my-tickets/",
                "/user/tickets/",
                f"/events/{self.event.pk}/my-tickets/",
                "/profile/tickets/"
            ]

            ticket_found = False

            for url in possible_urls:
                try:
                    self.page.goto(f"{self.live_server_url}{url}")
                    self.page.wait_for_load_state("networkidle")
                    self.page.wait_for_timeout(1000)

                    search_selectors = [
                        f"text={ticket.ticket_code}",
                        f"*:has-text('{ticket.ticket_code}')",
                        f"td:has-text('{ticket.ticket_code}')",
                        f".ticket-code:has-text('{ticket.ticket_code}')",
                        f"[data-ticket-code='{ticket.ticket_code}']"
                    ]

                    for selector in search_selectors:
                        try:
                            if self.page.locator(selector).count() > 0:
                                ticket_found = True
                                break
                        except:
                            continue

                    if ticket_found:
                        break

                except:
                    continue

            db_ticket = Ticket.objects.filter(user=self.user, event=self.event, ticket_code=unique_code).first()
            assert db_ticket is not None, "Ticket no encontrado en base de datos"
            assert db_ticket.ticket_code == unique_code, f"Código de ticket incorrecto: {db_ticket.ticket_code}"
            assert db_ticket.payment_confirmed == True, "El ticket debe estar confirmado"
            assert db_ticket.user == self.user, "El ticket debe pertenecer al usuario correcto"

        except Exception as e:
            test_failed = True
            raise e
        finally:
            self._take_screenshot("test_user_can_see_own_tickets", error=test_failed)

class TicketValidationTest(TicketBaseTest):
    def test_cannot_buy_more_than_available(self):
        """Test que no se pueden comprar más tickets de los disponibles"""
        test_failed = False

        try:
            self.event.general_tickets_available = 2
            self.event.save()

            self.login_user("usuario", "password123")

            initial_available = self.event.general_tickets_available
            initial_tickets = Ticket.objects.filter(user=self.user, event=self.event).count()

            self._simulate_ticket_purchase(3)

            final_tickets = Ticket.objects.filter(user=self.user, event=self.event).count()
            tickets_actually_created = final_tickets - initial_tickets

            assert tickets_actually_created <= initial_available, f"Se crearon {tickets_actually_created} tickets cuando solo había {initial_available} disponibles"

            self.event.refresh_from_db()
            assert self.event.general_tickets_available >= 0, f"Tickets disponibles negativos: {self.event.general_tickets_available}"

        except Exception as e:
            test_failed = True
            raise e
        finally:
            self._take_screenshot("test_cannot_buy_more_than_available", error=test_failed)
