import pytest
from django.urls import reverse
from django.contrib.messages import get_messages
from app.models import User, Event, Ticket


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ticket_type",
    [Ticket.TicketType.GENERAL, Ticket.TicketType.VIP],
)
def test_no_se_puede_comprar_si_el_evento_esta_agotado(client, ticket_type):
    user = User.objects.create_user(username="comprador", password="12345")
    client.login(username="comprador", password="12345")

    event = Event.objects.create(
        title="Evento agotado",
        general_tickets_available=0,
        vip_tickets_available=0,
        general_price=100,
        vip_price=200,
    )

    response = client.post(
        reverse("ticket_purchase", args=[event.id]),
        data={
            "type": ticket_type,
            "quantity": 1,
            "card_number": "1234567890123456",
            "expiration_date": "12/30",
            "cvv": "123",
            "save_card": False,
        },
        follow=True,
    )

    assert Ticket.objects.count() == 0
    messages = list(get_messages(response.wsgi_request))
    assert any(
        "agotado" in msg.message.lower() or "no hay entradas disponibles" in msg.message.lower()
        for msg in messages
    ), "No se encontró mensaje de evento agotado"

    assert response.status_code == 200
