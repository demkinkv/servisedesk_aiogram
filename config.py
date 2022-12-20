import sqlite3

TOKEN = '!!!TOKEN!!!'

def ensure_connection(func):
    """ Декоратор для подключения к СУБД: открывает соединение,
        выполняет переданную функцию и закрывает за собой соединение.
        Потокобезопасно!
    """
    def inner(*args, **kwargs):
        with sqlite3.connect('base.db') as conn:
            kwargs['conn'] = conn
            res = func(*args, **kwargs)
        return res

    return inner

@ensure_connection
def init_db(conn, force: bool = False):
    """ Проверить что нужные таблицы существуют, иначе создать их

        Важно: миграции на такие таблицы вы должны производить самостоятельно!

        :param conn: подключение к СУБД
    """
    c = conn.cursor()

    # Информация о пользователе
    # TODO: создать при необходимости...

    # Сообщения от пользователей
    #c.execute('DROP TABLE IF EXISTS task')

    c.execute('''
        CREATE TABLE IF NOT EXISTS task (
            task_id_pk        INTEGER PRIMARY KEY,
            user_id           INTEGER NOT NULL,
            first_name        TEXT,
            name_task         TEXT NOT NULL,
            address_task      TEXT NOT NULL,
            name_user         TEXT NOT NULL,
            phone_user        INTEGER NOT NULL,
            mail_user         TEXT NOT NULL,
            text_task         TEXT NOT NULL,
            log_task          TEXT,
            comm_task         TEXT,
            name_worker       TEXT,
            data_task_start   DATETIME NOT NULL,
            data_task_end     DATETIME,
            status_task       TEXT
        );
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id_pk                INTEGER PRIMARY KEY,
            user_id                   INTEGER NOT NULL,
            first_name                TEXT,
            role                      TEXT,
            name_worker               TEXT,
            worker_query_addr         TEXT,
            data_create_worker_start  DATETIME NOT NULL,
            data_create_worker_edit    DATETIME,
            status                    TEXT
        );
    ''')

    # Сохранить изменения
    conn.commit()

#select name is user id
@ensure_connection
def select_users_name_from_id(conn, user_id: int, limit: int = 1):
    c = conn.cursor()
    c.execute('SELECT name_worker FROM users WHERE user_id = ? LIMIT ?;', (user_id, limit))
    (res, ) = c.fetchone()
    return res

#select my task
@ensure_connection
def select_my_task(conn, user_id: int, limit: int = 10):
    c = conn.cursor()
    c.execute('SELECT task_id_pk, name_task, address_task, status_task FROM task WHERE name_worker = ? ORDER BY task_id_pk DESC LIMIT ?;', (user_id, limit))
    return c.fetchall()

#
@ensure_connection
def set_action_value_my_task(conn, status_task: str, task_id_pk: int):
    c = conn.cursor()
    c.execute('UPDATE task SET data_task_end=CURRENT_TIMESTAMP, status_task=? WHERE task_id_pk=?;', (status_task, task_id_pk))
    conn.commit()

#insert ticket
@ensure_connection
def add_job(conn, user_id: int, first_name: str, name_task: str, address_task: str, name_user: str, phone_user: int, mail_user: str, text_task: str):
    c = conn.cursor()
    c.execute('INSERT INTO task VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, CURRENT_TIMESTAMP, NULL, ?);', (user_id, first_name, name_task, address_task, name_user, phone_user, mail_user, text_task, 'создана'))
    conn.commit()

#instart 
@ensure_connection
def add_create_worker(conn, user_id: int, first_name: str, worker_query_role: str, worker_query_name: str, worker_query_addr: str):
    c = conn.cursor()
    c.execute('INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, ?);', (user_id, first_name, worker_query_role, worker_query_name, worker_query_addr, 'создана'))
    conn.commit()

@ensure_connection
def select_worcker(conn, user_id: str = "%", limit: int = 10):
    c = conn.cursor()
    c.execute('SELECT user_id, first_name, role, name_worker, worker_query_addr, data_create_worker_start, data_create_worker_edit, status FROM users WHERE user_id LIKE ? ORDER BY data_create_worker_start LIMIT ?;', (user_id, limit))
    return c.fetchall()

@ensure_connection
def set_create_worker_user_id(conn, status: str, user_id: int):
    c = conn.cursor()
    c.execute('UPDATE users SET data_create_worker_edit=CURRENT_TIMESTAMP, status=? WHERE user_id=?;', (status, user_id))
    conn.commit()

@ensure_connection
def select_task(conn, user_id: int, limit: int = 10):
    c = conn.cursor()
    c.execute('SELECT task_id_pk, name_task, address_task, status_task FROM task WHERE user_id = ? ORDER BY task_id_pk DESC LIMIT ?;', (user_id, limit))
    return c.fetchall()

@ensure_connection
def select_task_full(conn, user_id: int, task_id_pk: int):
    c = conn.cursor()
    c.execute('SELECT task_id_pk, name_task, address_task, name_user, phone_user, mail_user, text_task, name_worker, data_task_start, data_task_end, status_task FROM task WHERE user_id = ? AND task_id_pk = ?;', (user_id, task_id_pk))
    return c.fetchone()

@ensure_connection
def count_task(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM task WHERE user_id = ? LIMIT 1', (user_id, ))
    (res, ) = c.fetchone()
    return res

@ensure_connection
def count_users(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE user_id = ? LIMIT 5', (user_id, ))
    (res, ) = c.fetchone()
    return res

@ensure_connection
def delete_tick_worker(conn, user_id: int):
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ?;', (user_id, ))
    conn.commit()

@ensure_connection
def sub_admin_addr(conn, user_id: int):
    c = conn.cursor()
    c.execute('SELECT worker_query_addr FROM users WHERE user_id = ? AND role ="Распределение"', (user_id, ))
    (res, ) = c.fetchone()
    return res

@ensure_connection
def sub_admin_select_ticket(conn, res_sub_admin_addr: str, limit: int = 10):
    c = conn.cursor()
    c.execute('SELECT task_id_pk, name_task, address_task, status_task FROM task WHERE address_task = ? AND status_task != "Выполнено" ORDER BY task_id_pk DESC LIMIT ?;', (res_sub_admin_addr, limit))
    return c.fetchall()

@ensure_connection
def select_users_ticket_addr(conn, ticket_addr: str, limit: int = 10):
    c = conn.cursor()
    c.execute('SELECT user_id, name_worker FROM users WHERE worker_query_addr = ? ORDER BY name_worker LIMIT ?;', (ticket_addr, limit))
    return c.fetchall()

@ensure_connection
def menu_data_cbu_update_ticket_users(conn, data_cbu_users: int, data_cbu_ticket: int):
    c = conn.cursor()
    c.execute('UPDATE task SET name_worker=?, status_task="Принята" WHERE task_id_pk=?;', (data_cbu_users, data_cbu_ticket))
    conn.commit()
