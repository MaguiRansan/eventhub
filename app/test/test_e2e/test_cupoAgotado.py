import re
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect

from app.models import Event
from app.test.test_e2e.base import BaseE2ETest


class TicketSoldOutE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()
        self.user = self.create_test_user(is_organizer=False)
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
            organizer=self.user,
        )

    def test_no_permite_compra_si_evento_esta_agotado(self):
        """Verifica que no se permita comprar cuando no hay tickets disponibles"""
        self.login_user("usuario_test", "password123")

        event_url = reverse("event_detail", args=[self.event.pk])
        self.page.goto(f"{self.live_server_url}{event_url}")

        expect(self.page.get_by_text("Evento agotado")).to_be_visible()
        expect(self.page.get_by_text("Disponibles: 0 de 10")).to_be_visible()
        expect(self.page.get_by_text("Disponibles: 0 de 5")).to_be_visible()
        expect(self.page.get_by_role("button", name=re.compile(r"Comprar|Buy", re.IGNORECASE))).to_be_hidden()
