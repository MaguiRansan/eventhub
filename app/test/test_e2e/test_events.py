import re
import logging
import datetime
from django.utils import timezone
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright, expect
from app.models import Event, User, Venue, Category

logger = logging.getLogger(__name__)

class EventCrudE2ETest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=False)
        cls.context = cls.browser.new_context(
            viewport={'width': 1280, 'height': 1024},
            locale='es-ES'
        )
        
    @classmethod
    def tearDownClass(cls):
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
    
    def setUp(self):
        self.page = self.context.new_page()
        
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="password123",
            is_organizer=True,
        )

        self.venue = Venue.objects.create(
            name="Main Stadium",
            address="123 Main St",
            city="Springfield",
            capacity=1000,
            contact="contact@stadium.com",
            organizer=self.organizer
        )

        self.category = Category.objects.create(
            name="Concert",
            description="Music events",
            is_active=True
        )

    def _take_screenshot(self, step_name: str):
        try:
            self.page.screenshot(
            path=f"test_results/screenshots/{self._testMethodName}{step_name}.png", 
            full_page=True
        )
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")

    def _login_user(self, username: str, password: str):
        try:
            self.page.goto(f"{self.live_server_url}/accounts/login/")
            self._take_screenshot("login_page")
            
            username_field = self.page.get_by_label("Username").or_(
                self.page.get_by_label("Usuario")).or_(
                self.page.locator('input[name="username"]'))
            username_field.fill(username)
            
            password_field = self.page.get_by_label("Password").or_(
                self.page.get_by_label("Contraseña")).or_(
                self.page.locator('input[name="password"]'))
            password_field.fill(password)
            
            login_button = self.page.get_by_role("button", name=re.compile(r"Login|Iniciar sesión", re.IGNORECASE))
            login_button.click()
            
            self.page.wait_for_load_state("networkidle")
            expect(self.page).to_have_url(re.compile(f"{self.live_server_url}/(events/)?"), timeout=10000)
            self._take_screenshot("after_login")
            
        except Exception as e:
            self._take_screenshot("login_error")
            logger.error(f"Login failed: {str(e)}")
            raise

    def test_event_crud_operations(self):
        try:
            self._login_user("organizer", "password123")
            self._take_screenshot("after_login")

            create_button = self.page.get_by_role("link", name=re.compile(r"Crear Evento|Create Event", re.IGNORECASE))
            expect(create_button).to_be_visible()
            create_button.click()
            
            self.page.wait_for_load_state("networkidle")
            self._take_screenshot("create_event_page")

            event_title = "Evento Test"
            
            title_input = self.page.get_by_label("Título").or_(
                self.page.get_by_label("Title")).or_(
                self.page.locator('input[name="title"]'))
            title_input.fill(event_title)
            
            description_input = self.page.get_by_label("Descripción").or_(
                self.page.get_by_label("Description")).or_(
                self.page.locator('textarea[name="description"]'))
            description_input.fill("Descripción del evento de prueba")
            
            today = datetime.date.today()
            future_date = today + datetime.timedelta(days=7)
            
            date_input = self.page.get_by_label("Fecha").or_(
                self.page.locator('input[name="date"]')).or_(
                self.page.locator('input[name="scheduled_date"]'))
            date_input.fill(future_date.strftime("%Y-%m-%d"))
            
            time_input = self.page.get_by_label("Hora").or_(
                self.page.get_by_label("Time")).or_(
                self.page.locator('input[name="time"]')).or_(
                self.page.locator('input[name="scheduled_time"]'))
            time_input.fill("19:00")
            
            general_price = self.page.get_by_label("Precio General").or_(
                self.page.get_by_label("General Price")).or_(
                self.page.locator('input[name="general_price"]'))
            general_price.fill("50")
            
            vip_price = self.page.get_by_label("Precio VIP").or_(
                self.page.get_by_label("VIP Price")).or_(
                self.page.locator('input[name="vip_price"]'))
            vip_price.fill("100")
            
            general_tickets = self.page.get_by_label("Tickets Generales").or_(
                self.page.get_by_label("General Tickets")).or_(
                self.page.locator('input[name="general_tickets"]'))
            general_tickets.fill("100")
            
            vip_tickets = self.page.get_by_label("Tickets VIP").or_(
                self.page.get_by_label("VIP Tickets")).or_(
                self.page.locator('input[name="vip_tickets"]'))
            vip_tickets.fill("50")
            
            venue_select = self.page.locator('select[name="venue"]').or_(
                self.page.locator('select[id="id_venue"]'))
            if venue_select.count() > 0:
                venue_select.select_option(str(self.venue.pk))
            
            category_checkbox = self.page.locator(f'input[type="checkbox"][value="{self.category.pk}"]').or_(
                self.page.locator(f'input[type="checkbox"][name="categories"][value="{self.category.pk}"]'))
            if category_checkbox.count() > 0:
                category_checkbox.check()
            
            self._take_screenshot("form_completely_filled")

            submit_button = self.page.get_by_role("button", name=re.compile(r"Guardar|Save|Crear|Create", re.IGNORECASE))
            submit_button.click()
            
            self.page.wait_for_url(re.compile(r"/events/\d+/"), timeout=10000)
            self._take_screenshot("after_submit")

            expect(self.page).to_have_url(re.compile(r"/events/\d+/"))
            
            current_url = self.page.url
            match = re.search(r'/events/(\d+)/', current_url)
            if not match:
                self.fail("No se pudo extraer el ID del evento de la URL")
            event_id = match.group(1)
            logger.info(f"Evento creado con ID: {event_id}")
            
            edit_button = self.page.get_by_role("link", name=re.compile(r"Editar|Edit", re.IGNORECASE))
            expect(edit_button).to_be_visible(timeout=5000)
            edit_button.click()
            
            self.page.wait_for_url(re.compile(rf"/events/{event_id}/edit/"), timeout=10000)
            self._take_screenshot("edit_event_page")

            title_input = self.page.get_by_label("Título").or_(
                self.page.get_by_label("Title")).or_(
                self.page.locator('input[name="title"]'))
            description_input = self.page.get_by_label("Descripción").or_(
                self.page.get_by_label("Description")).or_(
                self.page.locator('textarea[name="description"]'))
            description_input.fill("Descripción actualizada del evento")
            
            general_price = self.page.get_by_label("Precio General").or_(
                self.page.get_by_label("General Price")).or_(
                self.page.locator('input[name="general_price"]'))
            general_price.fill("75")
            
            self._take_screenshot("edit_form_filled")

            date_input = self.page.get_by_label("Fecha").or_(
                self.page.locator('input[name="date"]')).or_(
                self.page.get_by_label("Date")).or_(
                self.page.locator('input[name="scheduled_date"]'))
            date_input.fill((timezone.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d"))
            
            time_input = self.page.get_by_label("Hora").or_(
                self.page.get_by_label("Time")).or_(                
                self.page.locator('input[name="scheduled_time"]'))    
            time_input.fill("20:00")                                                                    
            vip_price = self.page.get_by_label("Precio VIP").or_(
                self.page.get_by_label("VIP Price")).or_(
                self.page.locator('input[name="vip_price"]'))
            vip_price.fill("150")
            
            self._take_screenshot("edit_form_filled")

            submit_button = self.page.get_by_role("button", name=re.compile(r"Guardar|Save|Actualizar|Update", re.IGNORECASE))
            submit_button.click()
            
            self.page.wait_for_url(re.compile(rf"/events/{event_id}/"), timeout=10000)
            self._take_screenshot("after_update")

            self.page.goto(f"{self.live_server_url}/events/")
            self._take_screenshot("events_list")

            event_row = self.page.locator("tr", has_text=re.compile(event_title, re.IGNORECASE))
            expect(event_row).to_be_visible(timeout=5000)

            delete_button = event_row.locator('button[title="Eliminar"]').or_(
            event_row.locator('button[title="Delete"]'))
            expect(delete_button).to_be_visible(timeout=5000)
            self.page.once("dialog", lambda dialog: dialog.accept())
            delete_button.click()

            self._take_screenshot("delete_confirmation")

            self.page.wait_for_load_state("networkidle")
            self._take_screenshot("after_delete")

            expect(self.page.get_by_text(re.compile(event_title, re.IGNORECASE))).not_to_be_visible(timeout=5000)
            
            with self.assertRaises(Event.DoesNotExist):
                Event.objects.get(pk=event_id)
            
        except Exception as e:
            self._take_screenshot("test_failed")
            logger.error(f"Test failed at step: {self.page.url}")
            logger.error(f"Page content: {self.page.content()}")
            logger.error(f"Error: {str(e)}")
            raise
        finally:
            if hasattr(self, 'page'):
                self.page.close()