from modules.database import init_db, query
init_db()
print('Usuarios:', len(query('select * from users')))
print('Plantillas:', len(query('select * from templates')))
