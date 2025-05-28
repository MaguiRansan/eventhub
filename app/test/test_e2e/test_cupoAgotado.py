import re
import logging
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from playwright.sync_api import sync_playwright, expect
from app.models import User, Event

logger = logging.getLogger(__name__)

class TicketE2ETest(StaticLiveServerTestCase):
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

    def _take_screenshot(self, step_name: str):
        try:
            self.page.screenshot(
                path=f"test_results/screenshots/{self._testMethodName}_{step_name}.png", 
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

    def test_no_permite_compra_si_evento_esta_agotado(self):
        try:
            self._login_user("usuario_e2e", "clave123")
            self._take_screenshot("after_login")

            # Go to event detail page
            event_url = reverse("event_detail", args=[self.event.pk])
            self.page.goto(f"{self.live_server_url}{event_url}")
            self._take_screenshot("event_detail_page")

            # Check that the event shows as sold out
            # The page shows "Evento agotado" as the main heading
            expect(self.page.get_by_text("Evento agotado")).to_be_visible()
            
            # Also verify that tickets show as unavailable
            expect(self.page.get_by_text("Disponibles: 0 de 10")).to_be_visible()  # General tickets
            expect(self.page.get_by_text("Disponibles: 0 de 5")).to_be_visible()   # VIP tickets
            
            # Verify that there's no buy button visible since tickets are sold out
            buy_button = self.page.get_by_role("button", name=re.compile(r"Comprar|Buy", re.IGNORECASE))
            expect(buy_button).not_to_be_visible()
            
            self._take_screenshot("sold_out_verified")

        except Exception as e:
            self._take_screenshot("test_failed")
            logger.error(f"Test failed at step: {self.page.url}")
            logger.error(f"Page content: {self.page.content()}")
            logger.error(f"Error: {str(e)}")
            raise
        finally:
            if hasattr(self, 'page'):
                self.page.close()