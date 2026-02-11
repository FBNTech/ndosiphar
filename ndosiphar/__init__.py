
import os


if os.environ.get('DB_ENGINE', 'sqlite').lower() == 'mysql':
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except Exception:
        pass
