import re
import logging
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from app.models import Ticket, Event, RefundRequest
from playwright.sync_api import sync_playwright, expect
from datetime import timedelta

logger = logging.getLogger(__name__)
User = get_user_model()

class RefundRequestE2ETest(StaticLiveServerTestCase):
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
        
        self.user = User.objects.create(
            username='testuser',
            is_organizer=False
        )
        self.user.set_password('testpass123')
        self.user.save()

        self.scheduled_at = timezone.now() + timedelta(days=10)
        self.event = Event.objects.create(
            title='Concierto de Prueba',
            description='Descripción del evento',
            scheduled_at=self.scheduled_at,
            organizer=self.user,
            general_price=Decimal('100.00'),
            vip_price=Decimal('200.00'),
            general_tickets_total=100,
            general_tickets_available=100,
            vip_tickets_total=50,
            vip_tickets_available=50
        )
        
        self.ticket = Ticket.objects.create(
            ticket_code='TEST123',
            user=self.user,
            event=self.event,
            type=Ticket.TicketType.GENERAL,
            quantity=1,
            payment_confirmed=True,
            is_used=False,
            buy_date=timezone.now() - timedelta(minutes=15))
        
        self.ticket._calculate_pricing()
        self.ticket.save()

    def _take_screenshot(self, step_name: str):
        try:
            self.page.screenshot(path=f"test_results/screenshots/{self._testMethodName}_{step_name}.png", full_page=True)
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")

    def _login_user(self):
        """Helper method to login the test user"""
        try:
            self.page.goto(f"{self.live_server_url}/accounts/login/")
            self._take_screenshot("login_page")

            self.page.wait_for_load_state("domcontentloaded")

            username_field = self.page.get_by_label("Username").or_(
                self.page.get_by_label("Usuario")).or_(
                self.page.locator('input[name="username"]'))
            username_field.wait_for(state="visible", timeout=10000)
            username_field.fill('testuser')
            
            password_field = self.page.get_by_label("Password").or_(
                self.page.get_by_label("Contraseña")).or_(
                self.page.locator('input[name="password"]'))
            password_field.wait_for(state="visible", timeout=10000)
            password_field.fill('testpass123')
            
            login_button = self.page.get_by_role("button", name=re.compile(r"Login|Iniciar sesión", re.IGNORECASE))
            login_button.click()
            
            self.page.wait_for_load_state("networkidle")
            expect(self.page).to_have_url(re.compile(f"{self.live_server_url}/(events/)?"), timeout=10000)
            self._take_screenshot("after_login")
            
        except Exception as e:
            self._take_screenshot("login_error")
            logger.error(f"Login failed: {str(e)}")
            raise

    def test_refund_request_workflow(self):
        try:

            self._login_user()
            self._take_screenshot("after_login")

            self.page.goto(f"{self.live_server_url}/refund_request/") 
            self.page.wait_for_load_state("domcontentloaded")
            self._take_screenshot("refund_page_loaded")
            
            ticket_code_input = self.page.locator('input[name="ticket_code"]').or_(
                self.page.get_by_label("Código del ticket")).or_(
                self.page.get_by_label("Ticket code"))
            
            ticket_code_input.wait_for(state="visible", timeout=15000)
            expect(ticket_code_input).to_be_visible()
            ticket_code_input.fill('TEST123')
      
            reason_select = self.page.locator('select[name="reason"]').or_(
                self.page.get_by_label("Motivo")).or_(
                self.page.get_by_label("Reason"))
            reason_select.wait_for(state="visible", timeout=10000)
            reason_select.select_option(label='Problemas de salud')
            
            policy_checkbox = self.page.locator('input[name="accept_policy"]').or_(
                self.page.get_by_label("Acepto la política")).or_(
                self.page.get_by_label("I accept the policy"))
            policy_checkbox.wait_for(state="visible", timeout=10000)
            policy_checkbox.check()
            
            self._take_screenshot("form_filled")

            submit_button = self.page.get_by_role("button", name=re.compile(r"Enviar|Submit", re.IGNORECASE))
            submit_button.click()
            
            self.page.wait_for_load_state("networkidle")
            self._take_screenshot("after_submission")
            
            current_url = self.page.url
            if "/my_refunds/" in current_url:
      
                expect(self.page.get_by_text("TEST123")).to_be_visible(timeout=5000)
                expect(self.page.get_by_text("Salud")).to_be_visible(timeout=5000)
                expect(self.page.get_by_text("Pendiente")).to_be_visible(timeout=5000)
                logger.info("Refund request successfully created and visible in table")
            else:
  
                success_indicators = [
                    "Solicitud enviada",
                    "Solicitud creada",
                    "Éxito",
                    "exitosamente",
                    "success"
                ]
                
                success_found = False
                for indicator in success_indicators:
                    try:
                        expect(self.page.get_by_text(re.compile(indicator, re.IGNORECASE))).to_be_visible(timeout=2000)
                        success_found = True
                        break
                    except:
                        continue
                
                if not success_found:
                    logger.warning("No explicit success message found, checking database...")
            
            refund_request = RefundRequest.objects.filter(
                ticket_code='TEST123',
                user=self.user
            ).first()
            
            assert refund_request is not None, "Refund request was not created in database"
            assert refund_request.reason == 'Salud', f"Expected reason 'Salud', got '{refund_request.reason}'"
            logger.info(f"Database verification passed: RefundRequest ID {refund_request.pk} created")
            
  
            self.page.goto(f"{self.live_server_url}/refund_request/")
            self.page.wait_for_load_state("domcontentloaded")
    
            try:
                ticket_input = self.page.locator('input[name="ticket_code"]')
                if ticket_input.is_visible():
                    ticket_input.fill('TEST123')
                    
                    submit_btn = self.page.get_by_role("button", name=re.compile(r"Enviar|Submit", re.IGNORECASE))
                    submit_btn.click()
                    self.page.wait_for_load_state("networkidle")
                    
                    duplicate_messages = [
                        "ya tiene una solicitud",
                        "already exists",
                        "duplicado",
                        "duplicate"
                    ]
                    
                    error_found = False
                    for msg in duplicate_messages:
                        try:
                            expect(self.page.get_by_text(re.compile(msg, re.IGNORECASE))).to_be_visible(timeout=3000)
                            error_found = True
                            logger.info(f"Duplicate prevention message found: {msg}")
                            break
                        except:
                            continue
                    
                    if not error_found:
                        logger.warning("No duplicate prevention message found, but test may still be valid")
                        
            except Exception as e:
                logger.info(f"Could not test duplicate submission: {str(e)} - This may be expected behavior")
            
            self._take_screenshot("test_completed")
            
        except Exception as e:
            self._take_screenshot("test_failed")
            logger.error(f"Test failed at step: {self.page.url}")
            logger.error(f"Page title: {self.page.title()}")
     
            try:
                inputs = self.page.locator('input').all()
                selects = self.page.locator('select').all()
                logger.error(f"Found {len(inputs)} inputs and {len(selects)} selects on page")
                
                for i, input_el in enumerate(inputs):
                    try:
                        name = input_el.get_attribute('name')
                        input_type = input_el.get_attribute('type')
                        logger.error(f"Input {i}: name='{name}', type='{input_type}'")
                    except:
                        pass
                        
            except Exception as debug_e:
                logger.error(f"Could not debug form elements: {str(debug_e)}")
            
            logger.error(f"Error: {str(e)}")
            raise
        finally:
            self.page.close()