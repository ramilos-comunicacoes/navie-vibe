import os
import sys
import io

# Configura encoding UTF-8 para stdout e stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

replacements = [
    (
        "cinema/migrations/0001_initial.py",
        "('empresa', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_cinema', to='core.empresa')),",
        "('empresa', models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='perfil_cinema', to='core.empresa')),"
    ),
    (
        "eventos/migrations/0001_initial.py",
        "('empresa', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_produtora', to='core.empresa')),",
        "('empresa', models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='perfil_produtora', to='core.empresa')),"
    ),
    (
        "parques/migrations/0001_initial.py",
        "('empresa', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_parque', to='core.empresa')),",
        "('empresa', models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='perfil_parque', to='core.empresa')),"
    ),
    (
        "parques/migrations/0001_initial.py",
        "('hospedagens_vinculadas', models.ManyToManyField(blank=True, related_name='parques_donos', to='hoteis.hotel')),",
        "('hospedagens_vinculadas', models.ManyToManyField(blank=True, db_constraint=False, related_name='parques_donos', to='hoteis.hotel')),"
    ),
    (
        "hoteis/migrations/0002_quartoimagem_unidadequarto_reserva_bloqueioquarto.py",
        "import django.db.models.deletion",
        "import django.db.models.deletion\nimport uuid"
    ),
    (
        "hoteis/migrations/0002_quartoimagem_unidadequarto_reserva_bloqueioquarto.py",
        "('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),",
        "('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),"
    ),
    (
        "hoteis/migrations/0002_quartoimagem_unidadequarto_reserva_bloqueioquarto.py",
        "('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservas', to=settings.AUTH_USER_MODEL)),",
        "('usuario', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservas', to=settings.AUTH_USER_MODEL)),"
    ),
    (
        "hoteis/migrations/0003_hotel_empresa.py",
        "field=models.OneToOneField(blank=True, help_text='A entidade comercial dona desta hospedagem', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='perfil_hospedagem', to='core.empresa'),",
        "field=models.OneToOneField(blank=True, db_constraint=False, help_text='A entidade comercial dona desta hospedagem', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='perfil_hospedagem', to='core.empresa'),"
    ),
    (
        "hoteis/migrations/0004_alter_hotel_empresa_alter_reserva_id_and_more.py",
        """        migrations.AlterField(
            model_name='reserva',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),""",
        ""
    ),
    (
        "hoteis/migrations/0019_reservalog.py",
        "('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reserva_logs', to=settings.AUTH_USER_MODEL)),",
        "('usuario', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reserva_logs', to=settings.AUTH_USER_MODEL)),"
    ),
    (
        "financeiro/migrations/0001_initial.py",
        "('criado_por', models.ForeignKey(blank=True, help_text='O atendente, recepcionista ou gerente humano que cadastrou a transação no sistema.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='financeiro_lancamentos', to=settings.AUTH_USER_MODEL)),",
        "('criado_por', models.ForeignKey(blank=True, db_constraint=False, help_text='O atendente, recepcionista ou gerente humano que cadastrou a transação no sistema.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='financeiro_lancamentos', to=settings.AUTH_USER_MODEL)),"
    )
]

print("🛠️ Iniciando correcao automatica de restricoes físicas e tipos UUID em migracoes...")

# Agrupando por arquivo para ler/escrever apenas uma vez
file_changes = {}
for filepath, old, new in replacements:
    file_changes.setdefault(filepath, []).append((old, new))

for filepath, changes in file_changes.items():
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        for old, new in changes:
            if old in content:
                content = content.replace(old, new)
                modified = True
            elif new in content or (old == "" or new == ""):
                pass
            else:
                print(f"⚠️ Padrao nao encontrado no arquivo {filepath}")
                
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Arquivo corrigido com sucesso: {filepath}")
        else:
            print(f"ℹ️ Arquivo ja possui todas as correcoes: {filepath}")
    else:
        print(f"❌ Arquivo nao encontrado: {filepath}")

print("🎉 Processo finalizado!")
