from django import forms
from .models import Atividade
from django.db.models import Q

class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ['titulo', 'descricao', 'status', 'prioridade', 'data_vencimento', 'lembrete', 'usuario', 'hospede', 'quarto', 'reserva']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all',
                'placeholder': 'Ex: Limpeza do Quarto 102...'
            }),
            'data_vencimento': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'}, format='%Y-%m-%dT%H:%M'),
            'lembrete': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'}, format='%Y-%m-%dT%H:%M'),
            'descricao': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full modal-input-glass rounded-2xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all resize-none',
                'placeholder': 'Adicione detalhes importantes ou itens do enxoval...'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
            'prioridade': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
            'usuario': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
            'hospede': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
            'quarto': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
            'reserva': forms.Select(attrs={
                'class': 'w-full modal-input-glass rounded-xl px-4 py-2.5 text-xs font-bold focus:outline-none transition-all'
            }),
        }

    def __init__(self, *args, **kwargs):
        pousada = kwargs.pop('pousada', None)  # Pega o tenant
        super().__init__(*args, **kwargs)
        
        # Garante que o funcionário só veja dados de sua própria pousada
        if pousada:
            if 'quarto' in self.fields:
                self.fields['quarto'].queryset = self.fields['quarto'].queryset.filter(pousada=pousada)
            if 'reserva' in self.fields:
                self.fields['reserva'].queryset = self.fields['reserva'].queryset.filter(quarto__pousada=pousada)
            if 'usuario' in self.fields:
                self.fields['usuario'].queryset = self.fields['usuario'].queryset.filter(
                    Q(pousada_vinculada=pousada) | Q(role='DIRECAO') | Q(is_superuser=True)
                )
