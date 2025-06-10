import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, RefundRequest, Ticket

User = get_user_model()

class TestRefundRequestIntegration(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        cls.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )

        cls.organizer = User.objects.create_user(
            username='organizeruser',
            password='organizerpass123'
        )

        cls.base_event = Event.objects.create(
            title='Base Test Event',
            scheduled_at=timezone.now() + timedelta(days=5),
            organizer=cls.organizer,
            general_price=Decimal('10.00'),
            vip_price=Decimal('20.00'),
            general_tickets_available=100, 
            vip_tickets_available=50,    
        )

        cls.soon_event = Event.objects.create(
            title='Soon Event',
            scheduled_at=timezone.now() + timedelta(hours=47),
            organizer=cls.organizer,
            general_price=Decimal('10.00'),
            vip_price=Decimal('20.00'),
            general_tickets_available=100, 
            vip_tickets_available=50,    
        )
        
        cls.past_event = Event.objects.create(
            title='Past Event',
            scheduled_at=timezone.now() - timedelta(days=1),
            organizer=cls.organizer,
            general_price=Decimal('10.00'),
            vip_price=Decimal('20.00'),
            general_tickets_available=100, 
            vip_tickets_available=50,    
        )

        cls.ticket = Ticket.objects.create(
            ticket_code='TICKET123',
            user=cls.user,
            event=cls.base_event,
            is_used=False,
        )

        cls.non_refundable_ticket = Ticket.objects.create(
            ticket_code='TICKET456',
            user=cls.user,
            event=cls.base_event,
            is_used=True, 
        )
        
        cls.used_ticket = Ticket.objects.create(
            ticket_code='TICKET789',
            user=cls.user,
            event=cls.base_event,
            is_used=True,
        )

        cls.past_event_ticket = Ticket.objects.create(
            ticket_code='TICKET000',
            user=cls.user,
            event=cls.past_event,
            is_used=False,
        )

        cls.other_user_ticket = Ticket.objects.create(
            ticket_code='OTHER123',
            user=cls.other_user,
            event=cls.base_event,
            is_used=False,
        )

        cls.soon_ticket = Ticket.objects.create(
            ticket_code='SOON123',
            user=cls.user,
            event=cls.soon_event,
            is_used=False,
        )
        
        cls.new_ticket_for_user_with_pending = Ticket.objects.create(
            ticket_code='NEWTICKETFORUSER',
            user=cls.user,
            event=cls.base_event,
            is_used=False,
        )
        
    def _assert_message_content(self, response, expected_message_part, level=None):
        if response.status_code == 302:
            response = self.client.get(response.url)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(
            any(expected_message_part in str(m) for m in messages_list),
            f"No se encontró el mensaje esperado '{expected_message_part}' en los mensajes: {[str(m) for m in messages_list]}"
        )
        if level is not None:
            self.assertTrue(
                any(m.level == level for m in messages_list if expected_message_part in str(m)),
                f"El mensaje '{expected_message_part}' no tiene el nivel esperado {level}"
            )

    def _assert_form_error(self, response, field_name, expected_error_part):
        self.assertIn('form', response.context, "La respuesta no contiene un objeto 'form' en el contexto.")
        form = response.context['form']
        self.assertIn(field_name, form.errors, f"El campo '{field_name}' no tiene errores en el formulario.")
        self.assertTrue(
            any(expected_error_part in error for error in form.errors[field_name]),
            f"No se encontró el error esperado '{expected_error_part}' para el campo '{field_name}' en los errores del formulario: {form.errors}"
        )
        self.assertEqual(response.status_code, 200)

    def _assert_no_form_error(self, response, field_name):
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertNotIn(field_name, form.errors)
        
    def test_valid_refund_request(self):
        """Test que una solicitud válida se crea correctamente."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data, follow=True)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count + 1)
        refund_request = RefundRequest.objects.latest('id')
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.user, self.user)
        self.assertEqual(refund_request.ticket_code, self.ticket.ticket_code)
        self.assertTrue(refund_request.is_pending)

        self._assert_message_content(response, "¡Solicitud de reembolso enviada con éxito! Será revisada por un organizador.", level=messages.SUCCESS)

    def test_refund_request_with_existing_pending(self):
        """Test que no se puede crear solicitud si ya hay una pendiente para el mismo ticket."""
        self.client.force_login(self.user)
        
        RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason='Salud',
            approved=None
        )
        initial_refund_count = RefundRequest.objects.count() 

        data = {
            'ticket_code': self.ticket.ticket_code, 
            'reason': 'Trabajo',
            'details': '',
            'accept_policy': True
        }
 
        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
     
        self._assert_form_error(response, 'ticket_code', "Ya existe una solicitud de reembolso pendiente para este ticket. Por favor, espera a que sea procesada o edita la existente.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.") 

    def test_refund_request_with_existing_processed(self):
        """Test que no se puede crear solicitud si ya hay una procesada para el mismo ticket."""
        self.client.force_login(self.user)
    
        RefundRequest.objects.create(
            user=self.user,
            ticket_code=self.ticket.ticket_code,
            reason='Salud',
            approved=True 
        )
        initial_refund_count = RefundRequest.objects.count() 
        
        data = {
            'ticket_code': self.ticket.ticket_code, 
            'reason': 'Trabajo',
            'details': '',
            'accept_policy': True
        }

        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
 
        self._assert_form_error(response, 'ticket_code', "Ya existe una solicitud de reembolso procesada para este ticket.") 
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_with_other_reason_no_details(self):
        """Test que requiere detalles cuando la razón es 'Otros'."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.ticket.ticket_code,
            'reason': 'Otros',
            'details': '', 
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'details', "Si la razón es 'Otro motivo', debes especificar detalles.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_non_refundable_ticket(self):
        """Test que no se puede solicitar reembolso para ticket no reembolsable."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.non_refundable_ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)

        self.assertEqual(RefundRequest.objects.count(), initial_refund_count) 
        self._assert_form_error(response, 'ticket_code', "No se puede reembolsar un ticket que ya ha sido usado.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_used_ticket(self):
        """Test que no se puede solicitar reembolso para ticket usado."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.used_ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)

        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'ticket_code', "No se puede reembolsar un ticket que ya ha sido usado.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_past_event(self):
        """Test que no se puede solicitar reembolso para evento pasado."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.past_event_ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'ticket_code', "No se puede solicitar un reembolso para un evento que ya ocurrió.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_less_than_48h(self):
        """Test que no se puede solicitar reembolso con menos de 48h."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.soon_ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)

        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'ticket_code', "No puedes solicitar un reembolso con menos de 48 horas de anticipación al evento.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_not_own_ticket(self):
        """Test que no se puede solicitar reembolso para ticket de otro usuario."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.other_user_ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True
        }
        
        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'ticket_code', "Este ticket no te pertenece o no puedes solicitar un reembolso para él.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_multiple_pending_blocks_new(self):
        """Test que tener múltiples solicitudes pendientes bloquea nuevas."""
        self.client.force_login(self.user)

        RefundRequest.objects.create(
            user=self.user,
            ticket_code=f'PENDING123-{uuid.uuid4().hex[:8]}',
            reason='Salud',
            approved=None
        )
        RefundRequest.objects.create(
            user=self.user,
            ticket_code=f'PENDING456-{uuid.uuid4().hex[:8]}',
            reason='Trabajo',
            approved=None
        )
        initial_refund_count = RefundRequest.objects.count()
        
        valid_new_ticket = self.new_ticket_for_user_with_pending 

        data = {
            'ticket_code': valid_new_ticket.ticket_code,
            'reason': 'Emergencia Familiar',
            'details': '',
            'accept_policy': True
        }

        response = self.client.post(reverse('refund_request'), data)
        
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)

        self._assert_form_error(response, 'ticket_code', "Ya tienes solicitudes de reembolso pendientes") 
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_refund_request_without_accepting_policy(self):
        """Test que no se puede enviar sin aceptar la política."""
        self.client.force_login(self.user)
        initial_refund_count = RefundRequest.objects.count()
        
        data = {
            'ticket_code': self.ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': False
        }
        
        response = self.client.post(reverse('refund_request'), data)

        self.assertEqual(RefundRequest.objects.count(), initial_refund_count)
        self._assert_form_error(response, 'accept_policy', "Debes aceptar la política para enviar la solicitud.")
        self.assertNotContains(response, "Solicitud de reembolso creada exitosamente.")

    def test_get_refund_request_with_pending_requests(self):
        """Test que GET muestra un mensaje de error si hay solicitudes pendientes y no permite crear una nueva."""
        self.client.force_login(self.user)

        RefundRequest.objects.create(
            user=self.user,
            ticket_code=f'PENDING_GET_TEST_1-{uuid.uuid4().hex[:8]}',
            reason='Salud',
            approved=None
        )
        RefundRequest.objects.create(
            user=self.user,
            ticket_code=f'PENDING_GET_TEST_2-{uuid.uuid4().hex[:8]}',
            reason='Motivo Extra',
            approved=None
        )
  
        response = self.client.get(reverse('refund_request'), follow=True) 
        
        self.assertRedirects(response, reverse('my_refunds'))

        self._assert_message_content(response, "Ya tienes solicitudes de reembolso pendientes. Debes esperar a que sean procesadas antes de crear una nueva.", level=messages.WARNING)