import os
import sys
sys.path.insert(0, os.getcwd())
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navievibe.settings')
django.setup()

from hoteis.models import Hotel, Quarto, UnidadeQuarto, Reserva
from django.test import RequestFactory
from hoteis.views import api_buscar_quartos
from datetime import datetime, date

def main():
    hotel = Hotel.objects.get(id=4)
    units = []
    for q in hotel.quartos.all():
        units.extend(list(q.unidades.filter(ativa=True)))

    print("Units to block:", [u.identificador for u in units])

    checkin_d = date(2026, 7, 10)
    checkout_d = date(2026, 7, 15)

    from django.contrib.auth.models import User
    user_obj = User.objects.first()
    if not user_obj:
        user_obj = User.objects.create_user(username='testuser', password='password')

    temp_res = []
    try:
        for u in units:
            r = Reserva.objects.create(
                usuario=user_obj,
                unidade=u,
                data_checkin=checkin_d,
                data_checkout=checkout_d,
                valor_total=1000.0,
                status='confirmada'
            )
            temp_res.append(r)
        print("Created temporary reservations to block units:", len(temp_res))

        rf = RequestFactory()
        request = rf.get('/api/hotel/4/buscar-quartos/', {'datas': '10/07/2026 - 15/07/2026', 'guests': '2'})
        request.session = {}
        
        response = api_buscar_quartos(request, 4)
        content = response.content.decode('utf-8', errors='ignore')
        
        print("Status Code:", response.status_code)
        print("Includes 'Sem vagas':", 'Sem vagas' in content)
        print("Includes 'Sugestão de datas':", 'Sugestão de datas' in content)
        
        suggestions = re.findall(r'📅 \d+/\d+ a \d+/\d+', content)
        print("Found suggestions in HTML:", suggestions)

    finally:
        for r in temp_res:
            r.delete()
        print("Deleted temporary reservations.")

if __name__ == '__main__':
    main()
