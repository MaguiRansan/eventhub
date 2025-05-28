import pytest
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.models import Event, Ticket, User


@pytest.mark.django_db
def test_no_se_puede_comprar_mas_de_lo_disponible_para_cada_tipo():
    organizer = User.objects.create_user(
        username="organizador", password="pass", is_organizer=True
    )
    buyer = User.objects.create_user(username="comprador", password="pass")

    event = Event.objects.create(
        title="Evento Mixto",
        description="Evento con generales y VIPs limitadas",
        scheduled_at=timezone.now() + timedelta(days=1),
        organizer=organizer,
        general_price=Decimal("100"),
        vip_price=Decimal("200"),
        general_tickets_total=5,
        general_tickets_available=5,
        vip_tickets_total=3,
        vip_tickets_available=3,
    )

    with pytest.raises(ValidationError) as exc_info_general:
        Ticket.objects.create(
            user=buyer,
            event=event,
            type=Ticket.TicketType.GENERAL,
            quantity=6,  
        )
    assert "entradas disponibles" in str(exc_info_general.value)

    with pytest.raises(ValidationError) as exc_info_vip:
        Ticket.objects.create(
            user=buyer,
            event=event,
            type=Ticket.TicketType.VIP,
            quantity=4,  
        )
    assert "entradas disponibles" in str(exc_info_vip.value)
