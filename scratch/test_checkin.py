import os
import sys
import django
from datetime import date

# Set up Django
sys.path.append(r"c:\Dev\JAVA\Naviê Vibe")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navie.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from hoteis.models import Reserva, ParceiroUsuario, Hotel, Quarto, UnidadeQuarto
from hoteis.views import partner_reserva_checkin

# Get a user and hotel
user = User.objects.filter(perfil_parceiro__isnull=False).first()
if not user:
    print("No user found")
    sys.exit()

hotel = user.perfil_parceiro.hotel

# Create or get a reserva
quarto = Quarto.objects.filter(hotel=hotel).first()
if not quarto:
    quarto = Quarto.objects.create(hotel=hotel, nome="Quarto Teste", preco=100)
unidade = UnidadeQuarto.objects.filter(quarto=quarto).first()
if not unidade:
    unidade = UnidadeQuarto.objects.create(quarto=quarto, identificador="101")

reserva = Reserva.objects.filter(unidade__quarto__hotel=hotel).first()
if not reserva:
    reserva = Reserva.objects.create(
        usuario=user,
        unidade=unidade,
        data_checkin=date.today(),
        data_checkout=date.today(),
        valor_total=100,
        status='pendente'
    )

print(f"Initial status: {reserva.status}")

# Simulate POST request
factory = RequestFactory()
request = factory.post(f'/hospedagens/reservas/{reserva.id}/checkin/')
request.user = user

response = partner_reserva_checkin(request, reserva.id)

print(f"Response status code: {response.status_code}")
reserva.refresh_from_db()
print(f"Status after 1st click: {reserva.status}")

# Simulate second click (unmark)
response2 = partner_reserva_checkin(request, reserva.id)
print(f"Response status code: {response2.status_code}")
reserva.refresh_from_db()
print(f"Status after 2nd click: {reserva.status}")

