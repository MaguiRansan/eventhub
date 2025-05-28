import re
import os
import logging
import datetime
from decimal import Decimal
import urllib.parse
import time 
from django.utils import timezone
from django.test import Client 
from playwright.sync_api import expect

from app.test.test_e2e.base import BaseE2ETest
from app.models import Event, User, Venue, Ticket, Rating 

logger = logging.getLogger(__name__)

class EventRatingE2ETest(BaseE2ETest):
    """Tests E2E para la funcionalidad de calificaciones y promedio de eventos."""

    def setUp(self):
        super().setUp()
        self.django_client = Client() 

        # Crear usuarios para las pruebas
        self.regular_user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
            is_organizer=False,
        )
        self.another_user = User.objects.create_user(
            username="anotheruser",
            email="anotheruser@example.com",
            password="password123",
            is_organizer=False,
        )
        self.organizer_user = User.objects.create_user(
            username="organizeruser",
            email="organizer@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear un venue para el evento
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="123 Test St",
            city="Testville",
            capacity=100,
            organizer=self.organizer_user
        )

        # Crear un evento en el pasado para que sea calificable
        self.event_past = Event.objects.create(
            title="Evento Pasado para Calificar",
            description="Este evento ya ha ocurrido y es calificable.",
            scheduled_at=timezone.now() - datetime.timedelta(days=7), 
            organizer=self.organizer_user,
            venue=self.venue,
            general_price=Decimal('10.00'),
            vip_price=Decimal('20.00'),
            general_tickets_total=50,
            general_tickets_available=50,
            vip_tickets_total=20,
            vip_tickets_available=20,
        )

        # Crear un ticket para el usuario regular, para que pueda calificar
        Ticket.objects.create(
            user=self.regular_user,
            event=self.event_past,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True, 
            ticket_code='ABC123DEF'
        )
        # Crear un ticket para el segundo usuario
        Ticket.objects.create(
            user=self.another_user,
            event=self.event_past,
            quantity=1,
            type='GENERAL',
            payment_confirmed=True,
            ticket_code='XYZ789UVW'
        )
    
    # Función auxiliar para tomar capturas de pantalla 
    def _take_screenshot(self, step_name: str):
        screenshots_dir = "test_results/screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshots_dir, f"{self.__class__.__name__}_{self._testMethodName}_{step_name}.png")
        try:
            self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Captura de pantalla tomada: {screenshot_path}")
        except Exception as e:
            logger.error(f"Error al tomar la captura de pantalla '{step_name}': {str(e)}")
   

    def _login_user_e2e(self, username, password):
        # Realizar el login con el cliente de Django para obtener la sesión
        login_successful = self.django_client.login(username=username, password=password)
        self.assertTrue(login_successful, f"Login de Django falló para el usuario {username}")

        # Obtener las cookies de la sesión de Django
        session_cookie = self.django_client.cookies.get('sessionid')
        if session_cookie:
            # Parsear la URL para obtener solo el dominio
            parsed_url = urllib.parse.urlparse(self.live_server_url)
            domain = parsed_url.hostname 

            # Inyectar la cookie en el contexto de Playwright
            self.page.context.add_cookies([
                {
                    'name': 'sessionid',
                    'value': session_cookie.value,
                    'domain': domain, 
                    'path': '/',
                }
            ])
        else:
            self.fail("No se encontró la cookie de sesión después del login de Django.")
        self.page.goto(f"{self.live_server_url}/events/")
        self.page.wait_for_load_state('networkidle')


    def _logout_user_e2e(self):
        self.django_client.logout()
        
        # Limpiar las cookies de sesión en Playwright para simular el logout en el navegador
        self.page.context.clear_cookies()
        
        self.page.goto(self.live_server_url)
        self.page.wait_for_load_state('networkidle')
        # Verificar que el botón de login/registro vuelve a ser visible
        expect(self.page.get_by_role("link", name=re.compile(r"Ingresá|Login", re.IGNORECASE))).to_be_visible()


    def test_submit_rating_and_check_average_display(self):
        """
        Verifica que un usuario puede enviar una calificación
        y que el promedio se actualiza y muestra correctamente para el organizador.
        """
        event_url = f"{self.live_server_url}/events/{self.event_past.id}/"
        try:
            self._login_user_e2e(self.regular_user.username, "password123")
            self._take_screenshot("after_regular_user_login") 
            self.page.goto(event_url) 
            self.page.wait_for_load_state('networkidle')
            self._take_screenshot("event_page_regular_user") 

            expect(self.page.get_by_text("Dejar una reseña")).to_be_visible()

            self.page.locator('#title').fill("Gran Evento")
            self.page.locator('#score').select_option("4") 
            self.page.locator('#comment').fill("Me gustó mucho la organización y el ambiente.")
            self.page.get_by_role("button", name="Enviar calificación").click()

            self.page.wait_for_url(event_url)
            self._take_screenshot("after_first_rating_submission") 

            # Verificar el mensaje de éxito
            expect(self.page.get_by_text("¡Tu calificación ha sido guardada con éxito!")).to_be_visible()

            self._logout_user_e2e() 
            self._take_screenshot("after_first_logout") 
            
            self._login_user_e2e(self.another_user.username, "password123")
            self._take_screenshot("after_second_user_login") 
            self.page.goto(event_url) 
            self.page.wait_for_load_state('networkidle')
            self._take_screenshot("event_page_second_user") 

            expect(self.page.get_by_text("Dejar una reseña")).to_be_visible()
            self.page.locator('#title').fill("Simplemente Genial")
            self.page.locator('#score').select_option("5") 
            self.page.locator('#comment').fill("Increíble, lo recomiendo totalmente.")
            self.page.get_by_role("button", name="Enviar calificación").click()

            # Esperar a que la página se recargue
            self.page.wait_for_url(event_url)
            self._take_screenshot("after_second_rating_submission")

            # Verificar el mensaje de éxito
            expect(self.page.get_by_text("¡Tu calificación ha sido guardada con éxito!")).to_be_visible()

            self._logout_user_e2e() 
            self._take_screenshot("after_second_logout") 
            
            self._login_user_e2e(self.organizer_user.username, "password123")
            self._take_screenshot("after_organizer_login") 
            self.page.goto(event_url) 
            self.page.wait_for_load_state('networkidle')
            self._take_screenshot("event_page_organizer") 

            time.sleep(1) 
            
          
            average_score_text_locator = self.page.locator('.card-body h5.card-title span.badge.bg-success.ms-2.fs-6')
            
            # Buscamos el texto "4,5" como valor esperado
            expect(average_score_text_locator).to_have_text("4,5", timeout=5000) 

            # Verificamos el conteo de calificaciones
            expect(self.page.get_by_text("(2 calificaciones)")).to_be_visible(timeout=5000)

            # Verificar las estrellas visuales para un promedio de 4.5
            average_stars_container = self.page.locator('.card-body h5.card-title .d-inline-block.align-middle.ms-2')
            
            expect(average_stars_container.locator('.bi-star-fill')).to_have_count(4)
            expect(average_stars_container.locator('.bi-star-half')).to_have_count(1)
            expect(average_stars_container.locator('.bi-star')).to_have_count(0)
            
            expect(self.page.get_by_text("Gran Evento")).to_be_visible()
            expect(self.page.get_by_text("Simplemente Genial")).to_be_visible()

            self._take_screenshot("all_assertions_passed") 

        except Exception as e:
            screenshots_dir = "test_failures_screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshots_dir, f"{self.__class__.__name__}__{self._testMethodName}_failure.png")
            try:
                self.page.screenshot(path=screenshot_path, full_page=True)
                logger.error(f"\n¡TEST FALLIDO! Captura de pantalla tomada: {screenshot_path}")
            except Exception as screenshot_e:
                logger.error(f"Error al tomar la captura de pantalla: {str(screenshot_e)}")
            
            logger.error(f"Test failed at URL: {self.page.url}")
            logger.error(f"Page content at failure:\n{self.page.content()}")
            raise e