import datetime
import logging
import re

from django.utils import timezone
from playwright.sync_api import Locator, expect

from app.models import Category, Event, User, Venue
from app.test.test_e2e.base import BaseE2ETest

logger = logging.getLogger(__name__)

class EventFilteringE2ETest(BaseE2ETest):

    def setUp(self):
        super().setUp()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            is_organizer=True
        )
        
        self.category = Category.objects.create(
            name='Music Concert',
            description='Live music events'
        )
        
        self.venue = Venue.objects.create(
            name='City Arena',
            address='123 Main St',
            city='Metropolis',
            capacity=5000,
            contact='contact@arena.com',
            organizer=self.user
        )
        
        self.now = timezone.now()
        
        self.past_event = Event.objects.create(
            title='Rock Festival 2023',
            description='Annual rock music festival',
            scheduled_at=self.now - datetime.timedelta(days=1),
            organizer=self.user,
            venue=self.venue
        )
        self.past_event.categories.set([self.category])
        
        self.future_event = Event.objects.create(
            title='Jazz Night 2024',
            description='Smooth jazz evening',
            scheduled_at=self.now + datetime.timedelta(days=1),
            organizer=self.user,
            venue=self.venue
        )
        self.future_event.categories.set([self.category])
        
        self.today_event = Event.objects.create(
            title='Pop Show Tonight',
            description='Live pop music performance',
            scheduled_at=self.now + datetime.timedelta(hours=2),
            organizer=self.user,
            venue=self.venue
        )
        self.today_event.categories.set([self.category])
    

    def test_future_and_today_events_visible_by_default(self):
        """
        Verifica que los eventos futuros y de hoy sean visibles por defecto,
        y que los eventos pasados no lo sean, sin aplicar ningún filtro.
        """
        self.login_user(self.user.username, "testpass123")
        self.page.goto(f"{self.live_server_url}/events/")
        
        expect(self.page.locator("table")).to_be_visible(timeout=10000)
        
        expect(self.page.get_by_text(self.future_event.title)).to_be_visible()
        expect(self.page.get_by_text(self.today_event.title)).to_be_visible()
        expect(self.page.get_by_text(self.past_event.title)).not_to_be_visible()
        logger.info("Eventos futuros y de hoy visibles, evento pasado oculto por defecto.")

    def test_show_past_events_filter(self):
        """
        Verifica que al marcar el checkbox 'Mostrar eventos pasados' y aplicar el filtro,
        el evento pasado se vuelva visible.
        """
        self.login_user(self.user.username, "testpass123")
        self.page.goto(f"{self.live_server_url}/events/")
        
        expect(self.page.locator("table")).to_be_visible(timeout=10000)

       
        past_events_checkbox: Locator = self.page.get_by_label(re.compile(r"Show past events|Mostrar eventos pasados", re.IGNORECASE)).or_(
            self.page.locator('input[name="mostrar_pasados"]').or_(
            self.page.locator('input[id="mostrar-pasados"]'))
        )
        expect(past_events_checkbox).to_be_visible()
        
       
        past_events_checkbox.check()
        logger.info("Checkbox 'Mostrar eventos pasados' marcado.")
        
   
        search_button = self.page.get_by_role("button", name=re.compile(r"Buscar|Search", re.IGNORECASE))
        expect(search_button).to_be_visible()
        search_button.click()
        self.page.wait_for_load_state("networkidle")
        
      
        expect(self.page.locator("table")).to_be_visible(timeout=10000)
        expect(self.page.get_by_text(self.past_event.title)).to_be_visible()
        logger.info("Evento pasado visible después de aplicar el filtro.")
        
       
        past_event_row = self.page.locator(f"tr:has-text('{self.past_event.title}')")
        expect(past_event_row).to_have_class(re.compile("past-event|bg-light", re.IGNORECASE))
        logger.info("La fila del evento pasado tiene la clase CSS esperada.")

    def test_hide_past_events_filter(self):
        """
        Verifica que al desmarcar el checkbox 'Mostrar eventos pasados' y aplicar el filtro,
        el evento pasado se oculte.
        """
        self.login_user(self.user.username, "testpass123")
        self.page.goto(f"{self.live_server_url}/events/?mostrar_pasados=true")
        self.page.wait_for_load_state("networkidle")
        
        expect(self.page.locator("table")).to_be_visible(timeout=10000)
        expect(self.page.get_by_text(self.past_event.title)).to_be_visible()

        past_events_checkbox: Locator = self.page.get_by_label(re.compile(r"Show past events|Mostrar eventos pasados", re.IGNORECASE)).or_(
            self.page.locator('input[name="mostrar_pasados"]').or_(
            self.page.locator('input[id="mostrar-pasados"]'))
        )
        expect(past_events_checkbox).to_be_visible()
        
  
        past_events_checkbox.uncheck()
        logger.info("Checkbox 'Mostrar eventos pasados' desmarcado.")


        search_button = self.page.get_by_role("button", name=re.compile(r"Buscar|Search", re.IGNORECASE))
        expect(search_button).to_be_visible()
        search_button.click()
        self.page.wait_for_load_state("networkidle")
        
        
        expect(self.page.get_by_text(self.past_event.title)).not_to_be_visible()
        logger.info("Evento pasado oculto después de desmarcar el filtro.")

    def test_direct_url_past_events_filter(self):
        """
        Verifica que el evento pasado sea visible cuando se accede directamente
        a la URL con el parámetro de filtro activado.
        """
        self.login_user(self.user.username, "testpass123")
        self.page.goto(f"{self.live_server_url}/events/?mostrar_pasados=true")
        self.page.wait_for_load_state("networkidle")
        
        expect(self.page.locator("table")).to_be_visible(timeout=10000)
        expect(self.page.get_by_text(self.past_event.title)).to_be_visible()
        logger.info("Evento pasado visible al filtrar por URL directamente.")