from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import datetime
from app.models import Event, User, Venue, Category

class EventViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_organizer=False
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            password='orgpass123',
            is_organizer=True
        )
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            capacity=100,
            contact='test@venue.com',
            organizer=self.organizer
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description',
            is_active=True
        )
        
        now = timezone.now()
        self.past_event = Event.objects.create(
            title='Past Event',
            description='Past Event Description',
            scheduled_at=now - datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            general_tickets_total=100,
            general_tickets_available=100
        )
        self.past_event.categories.add(self.category)
        
        self.future_event = Event.objects.create(
            title='Future Event',
            description='Future Event Description',
            scheduled_at=now + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
            general_tickets_total=100,
            general_tickets_available=100
        )
        self.future_event.categories.add(self.category)
        
        self.client.login(username='testuser', password='testpass123')

    def test_events_view_default_shows_only_future_events(self):
        """Test que verifica que por defecto solo se muestran eventos futuros y valida los objetos en el contexto."""
        response = self.client.get(reverse('events'))
        self.assertEqual(response.status_code, 200)
        
    
        self.assertContains(response, 'Future Event')
        self.assertNotContains(response, 'Past Event')

        self.assertIn('events', response.context)
        events_in_context = list(response.context['events'])

    
        self.assertEqual(len(events_in_context), 1)
        self.assertEqual(events_in_context[0].title, 'Future Event')
 
        self.assertTrue(events_in_context[0].scheduled_at > timezone.now())


    def test_events_view_with_show_past_parameter(self):
        """Test que verifica que con el parámetro mostrar_pasados se ven solo eventos pasados y valida los objetos en el contexto."""
        response = self.client.get(reverse('events') + '?mostrar_pasados=true')
        self.assertEqual(response.status_code, 200)
        
     
        self.assertNotContains(response, 'Future Event')
        self.assertContains(response, 'Past Event')

    
        self.assertIn('events', response.context)
        events_in_context = list(response.context['events']) 

       
        self.assertEqual(len(events_in_context), 1)
        self.assertEqual(events_in_context[0].title, 'Past Event')

        
        self.assertTrue(events_in_context[0].scheduled_at < timezone.now())

    def test_events_view_filtering_with_date(self):
        """Test que verifica que el filtrado por fecha funciona correctamente y valida los objetos en el contexto."""
        
     
        past_date = (timezone.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('events') + f'?fecha={past_date}')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Future Event')
        self.assertContains(response, 'Past Event')
        
        events_in_context_past = list(response.context['events'])
        self.assertEqual(len(events_in_context_past), 1)
        self.assertEqual(events_in_context_past[0].title, 'Past Event')
        self.assertTrue(events_in_context_past[0].scheduled_at.date() == (timezone.now() - datetime.timedelta(days=1)).date())
        
       
        future_date = (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('events') + f'?fecha={future_date}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Future Event')
        self.assertNotContains(response, 'Past Event')

        events_in_context_future = list(response.context['events'])
        self.assertEqual(len(events_in_context_future), 1)
        self.assertEqual(events_in_context_future[0].title, 'Future Event')
        self.assertTrue(events_in_context_future[0].scheduled_at.date() == (timezone.now() + datetime.timedelta(days=1)).date())


    def test_events_view_filtering_with_date_overrides_show_past(self):
        """Test que verifica que cuando se especifica fecha, esta tiene prioridad sobre mostrar_pasados y valida los objetos en el contexto."""
        
        future_date = (timezone.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(reverse('events') + f'?fecha={future_date}&mostrar_pasados=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Future Event')
        self.assertNotContains(response, 'Past Event')

       
        events_in_context = list(response.context['events'])
        self.assertEqual(len(events_in_context), 1)
        self.assertEqual(events_in_context[0].title, 'Future Event')
        self.assertTrue(events_in_context[0].scheduled_at.date() == (timezone.now() + datetime.timedelta(days=1)).date())


    def test_events_view_template_context(self):
        """Test que verifica que el contexto se pasa correctamente al template"""
        response = self.client.get(reverse('events'))
        self.assertEqual(response.status_code, 200)
        
        
        self.assertIn('events', response.context)
        self.assertIn('user_is_organizer', response.context)
        self.assertIn('categorias', response.context)
        self.assertIn('venues', response.context)
        
        
        self.assertFalse(response.context['user_is_organizer'])
        
        
        events = response.context['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, 'Future Event')

    def test_events_view_category_filtering(self):
        """Test que verifica el filtrado por categoría y valida los objetos en el contexto."""
    
        other_category = Category.objects.create(
            name='Other Category',
            description='Other Description',
            is_active=True
        )
        other_event = Event.objects.create(
            title='Other Event',
            description='Other Event Description',
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            general_tickets_total=50,
            general_tickets_available=50
        )
        other_event.categories.add(other_category)
        
    
        response = self.client.get(reverse('events') + f'?categoria={self.category.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Future Event')
        self.assertNotContains(response, 'Other Event')

      
        events_in_context = list(response.context['events'])
        self.assertEqual(len(events_in_context), 1)
        self.assertEqual(events_in_context[0].title, 'Future Event')
        self.assertTrue(self.category in events_in_context[0].categories.all())


    def test_events_view_venue_filtering(self):
        """Test que verifica el filtrado por venue y valida los objetos en el contexto."""
    
        other_venue = Venue.objects.create(
            name='Other Venue',
            address='456 Other St',
            city='Other City',
            capacity=200,
            contact='other@venue.com',
            organizer=self.organizer
        )
        other_event = Event.objects.create(
            title='Other Venue Event',
            description='Event at other venue',
            scheduled_at=timezone.now() + datetime.timedelta(days=2),
            organizer=self.organizer,
            venue=other_venue,
            general_tickets_total=50,
            general_tickets_available=50
        )
        other_event.categories.add(self.category)
        
        
        response = self.client.get(reverse('events') + f'?venue={self.venue.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Future Event')
        self.assertNotContains(response, 'Other Venue Event')

   
        events_in_context = list(response.context['events'])
        self.assertEqual(len(events_in_context), 1)
        self.assertEqual(events_in_context[0].title, 'Future Event')
        self.assertEqual(events_in_context[0].venue, self.venue)