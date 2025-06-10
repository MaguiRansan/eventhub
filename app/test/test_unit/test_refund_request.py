from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app.forms import RefundRequestForm
from app.models import Category, Event, RefundRequest, Ticket, User, Venue


class RefundRequestFormTest(TestCase):
    def setUp(self):

        self.organizer = User.objects.create_user(
            username='Organizador',
            password='testpass123',
            is_organizer=True
        )
        self.user = User.objects.create_user(
            username='Usuario',
            password='testpass123'
        )

        self.venue = Venue.objects.create(
            name='Estadio Unico La Plata',
            address='Av. 25, B1900',
            city='La Plata',
            capacity=100,
            contact='contact@test.com',
            organizer=self.organizer
        )

        self.category = Category.objects.create(
            name='Musica',
            description='Evento relacionado con conciertos, festivales y presentaciones musicales.',
            is_active=True
        )

        self.event = Event.objects.create(
            title='Concierto de Rock',
            description='Concierto de Rock en La Plata',
            scheduled_at=timezone.now() + timedelta(days=3),
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal('10000.00'),
            vip_price=Decimal('15000.00'),
            general_tickets_total=50,
            general_tickets_available=50,
            vip_tickets_total=20,
            vip_tickets_available=20
        )
        self.event.categories.add(self.category)

        self.ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            ticket_code='TEST-12345',
            type=Ticket.TicketType.GENERAL,
            quantity=1,
            is_used=False,
            payment_confirmed=True
        )

    def create_form(self, ticket=None, user=None, **kwargs):
        ticket = ticket or self.ticket
        user = user or self.user
        form_data = {
            'ticket_code': ticket.ticket_code,
            'reason': 'Salud',
            'details': '',
            'accept_policy': True,
            **kwargs
        }
        return RefundRequestForm(data=form_data, user=user)

    def test_valid_form_submission(self):
        form = self.create_form()
        self.assertTrue(form.is_valid())

    def test_rejects_used_ticket(self):
        self.ticket.is_used = True
        self.ticket.save()
        form = self.create_form()
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)

    def test_rejects_existing_ticket_request(self):
        RefundRequest.objects.create(
            ticket_code=self.ticket.ticket_code,
            user=self.user,
            reason='Salud'
        )
        form = self.create_form()
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)

    def test_rejects_user_with_active_refund(self):

        RefundRequest.objects.create(
            ticket_code='TEST-54321',
            user=self.user,
            reason='Emergencia Familiar',
            approved=None
        )

        form = self.create_form()
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)
        self.assertIn('Ya tienes solicitudes de reembolso pendientes', str(form.errors))

    def test_rejects_event_within_48_hours(self):
        self.event.scheduled_at = timezone.now() + timedelta(hours=47)
        self.event.save()
        form = self.create_form()
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)

    def test_rejects_wrong_ticket_owner(self):
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        form = self.create_form(user=other_user)
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)

    def test_requires_policy_acceptance(self):
        form = self.create_form(accept_policy=False)
        self.assertFalse(form.is_valid())
        self.assertIn('accept_policy', form.errors)

    def test_requires_details_for_other_reason(self):
        form = self.create_form(reason='Otros', details='')
        self.assertFalse(form.is_valid())
        self.assertIn('details', form.errors)

    def test_accepts_with_details_for_other_reason(self):
        form = self.create_form(reason='Otros', details='Razón específica')
        self.assertTrue(form.is_valid())

    def test_rejects_past_event(self):
        self.event.scheduled_at = timezone.now() - timedelta(days=1)
        self.event.save()
        form = self.create_form()
        self.assertFalse(form.is_valid())
        self.assertIn('ticket_code', form.errors)

    def test_successful_form_save(self):
        form = self.create_form()
        self.assertTrue(form.is_valid())
        refund_request = form.save(commit=False)
        refund_request.user = self.user
        refund_request.save()

        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.ticket_code, self.ticket.ticket_code)
        self.assertEqual(refund_request.user, self.user)
        self.assertIsNone(refund_request.approved)
