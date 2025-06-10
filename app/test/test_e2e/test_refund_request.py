import asyncio
import logging
import re
import threading
from datetime import timedelta
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import expect

from app.models import Event, RefundRequest, Ticket
from app.test.test_e2e.base import BaseE2ETest

User = get_user_model() 

logger = logging.getLogger(__name__)

class RefundRequestE2ETest(BaseE2ETest): 
    """
    Clase de prueba E2E para el flujo de solicitud de reembolso.
    """
    def setUp(self):
        super().setUp() 

        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 1024},
            locale='es-ES'
        )
        self.page = self.context.new_page()

        results_container = []

        def run_create_test_data():
            async def _create_test_data_async_wrapper():
                user_obj = await sync_to_async(User.objects.create)(
                    username='testuser',
                    is_organizer=False
                )
                await sync_to_async(user_obj.set_password)('testpass123')
                await sync_to_async(user_obj.save)()

                scheduled_at = timezone.now() + timedelta(days=10)
                event_obj = await sync_to_async(Event.objects.create)(
                    title='Concierto de Prueba',
                    description='Descripción del evento',
                    scheduled_at=scheduled_at,
                    organizer=user_obj, 
                    general_price=Decimal('100.00'),
                    vip_price=Decimal('200.00'),
                    general_tickets_total=100,
                    general_tickets_available=100,
                    vip_tickets_total=50,
                    vip_tickets_available=50
                )
                
                ticket_obj = await sync_to_async(Ticket.objects.create)(
                    ticket_code='TEST123',
                    user=user_obj, 
                    event=event_obj, 
                    type=Ticket.TicketType.GENERAL,
                    quantity=1,
                    payment_confirmed=True,
                    is_used=False,
                    buy_date=timezone.now() - timedelta(minutes=15)
                )
                
                await sync_to_async(ticket_obj._calculate_pricing)()
                await sync_to_async(ticket_obj.save)()
                
                return user_obj, event_obj, ticket_obj

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(_create_test_data_async_wrapper())
            results_container.append(results)
            loop.close()

        thread = threading.Thread(target=run_create_test_data)
        thread.start()
        thread.join() 

        self.user, self.event, self.ticket = results_container[0]

    def _login_user(self):
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.wait_for_load_state("domcontentloaded")

        username_field = self.page.locator('input[name="username"]')
        username_field.wait_for(state="visible", timeout=10000)
        username_field.fill('testuser')
        
        password_field = self.page.locator('input[name="password"]')
        password_field.wait_for(state="visible", timeout=10000)
        password_field.fill('testpass123')
        
        login_button = self.page.get_by_role("button", name=re.compile(r"Login|Iniciar sesión", re.IGNORECASE))
        login_button.click()
        
        self.page.wait_for_load_state("networkidle")
        
        expect(self.page).to_have_url(re.compile(f"^{re.escape(self.live_server_url)}/(events/)?$"), timeout=10000)

    def test_refund_request_workflow(self):
        """
        Prueba el flujo completo de solicitud de reembolso
        """
        self._login_user()

        self.page.goto(f"{self.live_server_url}/refund_request/") 
        self.page.wait_for_load_state("domcontentloaded") 

        ticket_code_input = self.page.locator('input[name="ticket_code"]')
        ticket_code_input.wait_for(state="visible", timeout=15000) 
        expect(ticket_code_input).to_be_visible()
        ticket_code_input.fill('TEST123')
   
        reason_select = self.page.locator('select[name="reason"]')
        reason_select.wait_for(state="visible", timeout=10000)
        reason_select.select_option(label='Problemas de salud') 
        
        policy_checkbox = self.page.locator('input[name="accept_policy"]')
        policy_checkbox.wait_for(state="visible", timeout=10000)
        policy_checkbox.check()
        
        submit_button = self.page.get_by_role("button", name=re.compile(r"Enviar|Submit", re.IGNORECASE))
        submit_button.click()
        
        self.page.wait_for_load_state("networkidle")

        refund_request_results = []
        def get_refund_request_data():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(sync_to_async(RefundRequest.objects.get)(ticket_code='TEST123', user=self.user))
            refund_request_results.append(result)
            loop.close()
        
        query_thread = threading.Thread(target=get_refund_request_data)
        query_thread.start()
        query_thread.join()
        
        refund_request = refund_request_results[0]
        self.assertEqual(refund_request.reason, 'Salud') 

        expect(self.page).to_have_url(f"{self.live_server_url}/my_refunds/")
        expect(self.page.get_by_text("TEST123")).to_be_visible(timeout=5000)
        expect(self.page.get_by_text("Salud")).to_be_visible(timeout=5000)
        expect(self.page.get_by_text("Pendiente")).to_be_visible(timeout=5000)

        self.page.goto(f"{self.live_server_url}/refund_request/", wait_until="load", timeout=30000) 

        expect(self.page).to_have_url(f"{self.live_server_url}/my_refunds/")

        ticket_code_input_locator = self.page.locator('input[name="ticket_code"]')
        expect(ticket_code_input_locator).not_to_be_visible(timeout=5000) 
        
        self.page.close()