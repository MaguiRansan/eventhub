import asyncio
import datetime
import logging
import re
import threading

from asgiref.sync import sync_to_async
from playwright.sync_api import expect

from app.models import Category, Event, User, Venue
from app.test.test_e2e.base import BaseE2ETest

logger = logging.getLogger(__name__)

class EventCrudE2ETest(BaseE2ETest):

    def setUp(self):
        super().setUp()

        self.current_test_name = self._testMethodName
        
        results_container = []
        
        async def _create_initial_data_async():
            organizer_obj = await sync_to_async(User.objects.create_user)(
                username="organizer",
                email="organizer@example.com",
                password="password123",
                is_organizer=True,
            )

            venue_obj = await sync_to_async(Venue.objects.create)(
                name="Main Stadium",
                address="123 Main St",
                city="Springfield",
                capacity=1000,
                contact="contact@stadium.com",
                organizer=organizer_obj
            )

            category_obj = await sync_to_async(Category.objects.create)(
                name="Concert",
                description="Music events",
                is_active=True
            )
            results_container.append((organizer_obj, venue_obj, category_obj))

        def _run_async_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_create_initial_data_async())
            loop.close()

        thread = threading.Thread(target=_run_async_in_thread)
        thread.start()
        thread.join() 
        
        self.organizer, self.venue, self.category = results_container[0]


    def _login_user(self, username: str, password: str):
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        
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
            
    def _fill_event_form(self, event_title: str, update_mode: bool = False):
        title_input = self.page.get_by_label("Título").or_(
            self.page.get_by_label("Title")).or_(
            self.page.locator('input[name="title"]'))
        
        title_input.fill(event_title) 
        
        description_text = "Descripción actualizada del evento" if update_mode else "Descripción del evento de prueba"
        description_input = self.page.get_by_label("Descripción").or_(
            self.page.get_by_label("Description")).or_(
            self.page.locator('textarea[name="description"]'))
        description_input.fill(description_text)
        
        future_date = datetime.date.today() + datetime.timedelta(days=7) 
        time_value = "19:00"
            
        date_input = self.page.get_by_label("Fecha").or_(
            self.page.get_by_label("Date")).or_(
            self.page.locator('input[name="date"]')).or_(
            self.page.locator('input[name="scheduled_date"]'))
        date_input.fill(future_date.strftime("%Y-%m-%d"))
        
        time_input = self.page.get_by_label("Hora").or_(
            self.page.get_by_label("Time")).or_(
            self.page.locator('input[name="time"]')).or_(
            self.page.locator('input[name="scheduled_time"]'))
        time_input.fill(time_value)
        
        general_price_value = "75" if update_mode else "50"
        vip_price_value = "150" if update_mode else "100"
        
        general_price = self.page.get_by_label("Precio General").or_(
            self.page.get_by_label("General Price")).or_(
            self.page.locator('input[name="general_price"]'))
        general_price.fill(general_price_value)
        
        vip_price = self.page.get_by_label("Precio VIP").or_(
            self.page.get_by_label("VIP Price")).or_(
            self.page.locator('input[name="vip_price"]'))
        vip_price.fill(vip_price_value)
        
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
        
        venue_select.select_option(str(self.venue.pk)) 
        
        category_checkbox = self.page.locator(f'input[type="checkbox"][value="{self.category.pk}"]').or_(
            self.page.locator(f'input[type="checkbox"][name="categories"][value="{self.category.pk}"]'))
        
        category_checkbox.check() 

    def test_event_crud_operations(self):
        self._login_user("organizer", "password123")
        
        create_button = self.page.get_by_role("link", name=re.compile(r"Crear Evento|Create Event", re.IGNORECASE))
        expect(create_button).to_be_visible()
        create_button.click()
        
        self.page.wait_for_load_state("networkidle")

        event_title = "Evento Test"
        self._fill_event_form(event_title, update_mode=False)

        submit_button = self.page.get_by_role("button", name=re.compile(r"Guardar|Save|Crear|Create", re.IGNORECASE))
        submit_button.click()
        
        self.page.wait_for_url(re.compile(r"/events/\d+/"), timeout=10000)
        expect(self.page).to_have_url(re.compile(r"/events/\d+/"))
        
        current_url = self.page.url
        match = re.search(r'/events/(\d+)/', current_url)
        event_id = match.group(1) 
        
        edit_button = self.page.get_by_role("link", name=re.compile(r"Editar|Edit", re.IGNORECASE))
        expect(edit_button).to_be_visible(timeout=5000)
        edit_button.click()
        
        self.page.wait_for_url(re.compile(rf"/events/{event_id}/edit/"), timeout=10000)

        self._fill_event_form(event_title, update_mode=True)

        submit_button = self.page.get_by_role("button", name=re.compile(r"Guardar|Save|Actualizar|Update", re.IGNORECASE))
        submit_button.click()
        
        self.page.wait_for_url(re.compile(rf"/events/{event_id}/"), timeout=10000)

        self.page.goto(f"{self.live_server_url}/events/")

        event_row = self.page.locator("tr", has_text=re.compile(event_title, re.IGNORECASE))
        expect(event_row).to_be_visible(timeout=5000)

        delete_button = event_row.locator('button[title="Eliminar"]').or_(
            event_row.locator('button[title="Delete"]'))
        expect(delete_button).to_be_visible(timeout=5000)
        
        self.page.once("dialog", lambda dialog: dialog.accept())
        delete_button.click()

        self.page.wait_for_load_state("networkidle")

        expect(self.page.get_by_text(re.compile(event_title, re.IGNORECASE))).not_to_be_visible(timeout=5000)
        
        db_check_results = []
        def _run_db_check_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(sync_to_async(Event.objects.get)(pk=event_id))
            except Event.DoesNotExist:
                db_check_results.append(True) 
            except Exception: 
                db_check_results.append(False) 
            finally:
                loop.close()

        db_thread = threading.Thread(target=_run_db_check_in_thread)
        db_thread.start()
        db_thread.join()
        
        self.assertTrue(db_check_results[0]) 
        
    def test_event_form_validation(self):
        self._login_user("organizer", "password123")
        create_button = self.page.get_by_role("link", name=re.compile(r"Crear Evento|Create Event", re.IGNORECASE))
        create_button.click()
        self.page.wait_for_load_state("networkidle")
        submit_button = self.page.get_by_role("button", name=re.compile(r"Guardar|Save|Crear|Create", re.IGNORECASE))
        submit_button.click()
        expect(self.page).to_have_url(re.compile(r".*/events/create/"))