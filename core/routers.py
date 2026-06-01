class NavieVibeRouter:
    """
    Um roteador de banco de dados para controlar todas as operações de dados
    dos modelos nas diferentes verticais de negócios do Naviê Vibe.
    """

    # Mapeamento do rótulo do app (app_label) para o nome da conexão do banco de dados
    APP_DB_MAP = {
        'hoteis': 'hospedagem',
        'cinema': 'cinema',
        'eventos': 'eventos',
        'parques': 'parques',
        'parceiros': 'parceiros',
        'financeiro': 'hospedagem',
        'estoque': 'hospedagem',
    }

    def db_for_read(self, model, **hints):
        """
        Direciona as leituras de modelos das verticais para seus respectivos bancos de dados.
        """
        app_label = model._meta.app_label
        return self.APP_DB_MAP.get(app_label, 'default')

    def db_for_write(self, model, **hints):
        """
        Direciona as gravações de modelos das verticais para seus respectivos bancos de dados.
        """
        app_label = model._meta.app_label
        return self.APP_DB_MAP.get(app_label, 'default')

    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite qualquer relacionamento, pois gerenciaremos a integridade lógica via Django
        através do uso de db_constraint=False para relações cross-database.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Garante que as migrações dos apps das verticais rodem apenas em seus bancos dedicados,
        e que os apps globais (auth, admin, core, sessions) fiquem estritamente no banco 'default'.
        """
        target_db = self.APP_DB_MAP.get(app_label)
        if target_db:
            return db == target_db
        
        # Tabelas de sistema e core devem migrar apenas no banco 'default'
        return db == 'default'
