import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db import transaction, IntegrityError
from datetime import timedelta

from app.models import Ticket, Event, RefundRequest
from app.forms import RefundRequestForm

@pytest.mark.django_db
class TestRefundRequestIntegration:
    @pytest.fixture
    def setup_data(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        self.event = Event.objects.create(
            name='Test Event',
            scheduled_at=timezone.now() + timedelta(days=5),
            refund_policy="48 hours before event"
        )

        self.ticket = Ticket.objects.create(
            ticket_code='TICKET123',
            user=self.user,
            event=self.event,
            is_used=False,
            is_refundable=True
        )

        self.non_refundable_ticket = Ticket.objects.create(
            ticket_code='TICKET456',
            user=self.user,
            event=self.event,
            is_used=False,
            is_refundable=False
        )
 
        self.used_ticket = Ticket.objects.create(
            ticket_code='TICKET789',
            user=self.user,
            event=self.event,
            is_used=True,
            is_refundable=True
        )

        past_event = Event.objects.create(
            name='Past Event',
            scheduled_at=timezone.now() - timedelta(days=1)
        )
        
        self.past_event_ticket = Ticket.objects.create(
            ticket_code='TICKET000',
            user=self.user,
            event=past_event,
            is_used=False,
            is_refundable=True
        )

        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.other_user_ticket = Ticket.objects.create(
            ticket_code='OTHER123',
            user=self.other_user,
            event=self.event,
            is_used=False,
            is_refundable=True
        )

    def test_valid_refund_request(self, setup_data, client):
        """Test que una solicitud válida se crea correctamente"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET123',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)

        assert response.status_code == 302
        assert response.url == reverse('my_refunds')
        
        assert RefundRequest.objects.count() == 1
        refund_request = RefundRequest.objects.first()
        assert refund_request is not None
        assert refund_request.user == self.user
        assert refund_request.ticket_code == 'TICKET123'
        assert refund_request.is_pending

    def test_refund_request_with_existing_pending(self, setup_data, client):
        """Test que no se puede crear solicitud si ya hay una pendiente"""
        client.force_login(self.user)
     
        RefundRequest.objects.create(
            user=self.user,
            ticket_code='TICKET123',
            reason='Salud',
            approved=None
        )
        
        data = {
            'ticket_code': 'TICKET123',
            'reason': 'Trabajo',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 1

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("Ya existe una solicitud de reembolso pendiente" in str(m) for m in messages_list)

    def test_refund_request_with_existing_processed(self, setup_data, client):
        """Test que no se puede crear solicitud si ya hay una procesada"""
        client.force_login(self.user)
      
        RefundRequest.objects.create(
            user=self.user,
            ticket_code='TICKET123',
            reason='Salud',
            approved=True
        )
        
        data = {
            'ticket_code': 'TICKET123',
            'reason': 'Trabajo',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 1

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("Ya existe una solicitud de reembolso procesada" in str(m) for m in messages_list)

    def test_refund_request_with_other_reason_no_details(self, setup_data, client):
        """Test que requiere detalles cuando la razón es 'Otros'"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET123',
            'reason': 'Otros',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 0

        assert 'details' in response.context['form'].errors

    def test_refund_request_non_refundable_ticket(self, setup_data, client):
        """Test que no se puede solicitar reembolso para ticket no reembolsable"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET456',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)

        assert RefundRequest.objects.count() == 0

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("no es elegible para reembolso" in str(m) for m in messages_list)

    def test_refund_request_used_ticket(self, setup_data, client):
        """Test que no se puede solicitar reembolso para ticket usado"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET789',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)

        assert RefundRequest.objects.count() == 0

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("No se puede reembolsar un ticket que ya ha sido usado" in str(m) for m in messages_list)

    def test_refund_request_past_event(self, setup_data, client):
        """Test que no se puede solicitar reembolso para evento pasado"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET000',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 0

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("No se puede solicitar un reembolso para un evento que ya ocurrió" in str(m) for m in messages_list)

    def test_refund_request_less_than_48h(self, setup_data, client):
        """Test que no se puede solicitar reembolso con menos de 48h"""
        client.force_login(self.user)

        soon_event = Event.objects.create(
            name='Soon Event',
            scheduled_at=timezone.now() + timedelta(hours=47)
        )
        
        soon_ticket = Ticket.objects.create(
            ticket_code='SOON123',
            user=self.user,
            event=soon_event,
            is_used=False,
            is_refundable=True
        )
        
        data = {
            'ticket_code': 'SOON123',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)

        assert RefundRequest.objects.count() == 0

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("No puedes solicitar un reembolso con menos de 48 horas" in str(m) for m in messages_list)

    def test_refund_request_not_own_ticket(self, setup_data, client):
        """Test que no se puede solicitar reembolso para ticket de otro usuario"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'OTHER123',
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 0
      
        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("Este ticket no te pertenece" in str(m) for m in messages_list)

    def test_refund_request_multiple_pending_blocks_new(self, setup_data, client):
        """Test que tener múltiples solicitudes pendientes bloquea nuevas"""
        client.force_login(self.user)
        
        RefundRequest.objects.create(
            user=self.user,
            ticket_code='TICKET123',
            reason='Salud',
            approved=None
        )
        
        RefundRequest.objects.create(
            user=self.user,
            ticket_code='TICKET456',
            reason='Trabajo',
            approved=None
        )
        
        data = {
            'ticket_code': 'TICKET789',
            'reason': 'Emergencia Familiar',
            'details': '',
            'accept_policy': True
        }
        
        response = client.post(reverse('refund_request'), data)
        
        assert RefundRequest.objects.count() == 2

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("Ya tienes solicitudes de reembolso pendientes" in str(m) for m in messages_list)

    def test_refund_request_without_accepting_policy(self, setup_data, client):
        """Test que no se puede enviar sin aceptar la política"""
        client.force_login(self.user)
        
        data = {
            'ticket_code': 'TICKET123',
            'reason': 'Salud',
            'details': '',
        }
        
        response = client.post(reverse('refund_request'), data)

        assert RefundRequest.objects.count() == 0

        assert 'accept_policy' in response.context['form'].errors

    def test_get_refund_request_with_pending_requests(self, setup_data, client):
        """Test que GET redirige si hay solicitudes pendientes"""
        client.force_login(self.user)

        RefundRequest.objects.create(
            user=self.user,
            ticket_code='TICKET123',
            reason='Salud',
            approved=None
        )
        
        response = client.get(reverse('refund_request'))
    
        assert response.status_code == 302
        assert response.url == reverse('my_refunds')

        messages_list = list(messages.get_messages(response.wsgi_request))
        assert any("Ya tienes solicitudes de reembolso pendientes" in str(m) for m in messages_list)