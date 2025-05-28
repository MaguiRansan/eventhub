import re
from playwright.sync_api import expect
from app.test.test_e2e.base import BaseE2ETest


class HomePageDisplayTest(BaseE2ETest):
    """Tests relacionados con la visualización de la página de inicio"""

    def test_home_page_loads(self):
        """Test que verifica que la home carga correctamente"""
        self.page.goto(f"{self.live_server_url}/")
        logo = self.page.get_by_text("EventHub", exact=True)
        expect(logo).to_be_visible()
        expect(logo).to_have_attribute("href", "/")

        expect(self.page.get_by_text("Bienvenidos a EventHub")).to_be_visible()
        expect(
            self.page.get_by_text(
                "Descubrí los mejores eventos cerca tuyo"

            )
        ).to_be_visible()


class HomeNavigationTest(BaseE2ETest):
    """Tests relacionados con la navegación desde la página de inicio"""

    def test_login_button_navigates_to_login_page(self):
        """Test que verifica que el botón de login navega a la página de login"""
        self.page.goto(f"{self.live_server_url}/")
        self.page.get_by_role("link", name="Ingresá").click()
        expect(self.page).to_have_url(re.compile(".*/login"))


class HomeAuthenticationTest(BaseE2ETest):
    """Tests relacionados con el comportamiento de autenticación en la página de inicio"""

    def test_auth_buttons_visibility_for_anonymous_user(self):
        """Test que verifica la visibilidad de los botones para usuarios anónimos"""
        self.page.goto(f"{self.live_server_url}/")
        login_btn = self.page.get_by_role("link", name="Ingresá")
        expect(login_btn).to_be_visible()
        signup_btn = self.page.get_by_role("link", name="Creá tu cuenta")
        expect(signup_btn).to_be_visible()
        logout_btn = self.page.get_by_role("button", name="Salir")
        expect(logout_btn).to_have_count(0)

    def test_auth_buttons_visibility_for_authenticated_user(self):
        """Test que verifica la visibilidad de los botones para usuarios autenticados"""
        user = self.create_test_user()

        self.page.goto(f"{self.live_server_url}/")
        self.page.get_by_role("link", name="Ingresá").click()

        self.page.get_by_label("Usuario").fill(user.username)
        self.page.get_by_label("Contraseña").fill("password123")

        self.page.get_by_role("button", name="Iniciar sesión").click()
        
        login_btn = self.page.get_by_role("link", name="Ingresá")
        expect(login_btn).to_have_count(0)

        signup_btn = self.page.get_by_role("link", name="Creá tu cuenta")
        expect(signup_btn).to_have_count(0)

        logout_btn = self.page.get_by_role("button", name="Salir")
        expect(logout_btn).to_be_visible()
