#!/usr/bin/python3
import telebot, random, subprocess, os, sys, sqlite3, configparser, json, time, pprint
from sqlite3 import Error, IntegrityError
from signal import SIGTERM
#
# Your user id (message.from_user.id).
# Main admin - can change event, add event-admins, recieve errors etc.
#
config = configparser.ConfigParser()  # создаём объекта парсера
config.read("settings.ini")  # читаем конфиг в формате ini
admin_id = int(config["Telegram"]["admin_id"])
token = str(config["Telegram"]["token"])
remote_point_name = str(config["Rclone"]["remote_point_name"])
bot = telebot.TeleBot(token, parse_mode=str(config["Telegram"]["parse_mode"]))

# Find directory, where tapok.py is
dirname = os.path.dirname(os.path.abspath(__file__))
if config.has_option("General","db_path"):
    db_path = config["General"]["db_path"]
else:
    db_path = dirname+"/tapok_sqlite.db"
    #!/usr/bin/env python

if config.has_option("General","stderr"):
    stderr = config["General"]["stderr"]
else:
    stderr = "/var/log/syslog"

if config.has_option("General","stdout"):
    stdout = config["General"]["stdout"]
else:
    stdout = "/var/log/message"


def create_connection():
    """ create a database connection to a SQLite database """
    conn = None
    # event with event_id = 0 - 'all events'
    init_script = '''create table if not exists events(
        event_id                INTEGER PRIMARY KEY AUTOINCREMENT,
        admins                  TEXT,
        title                   TEXT,
        bot_sends_main_tasks    INTEGER NOT NULL,
        private                 INTEGER NOT NULL,
        tasks_from_all_events   INTEGER NOT NULL,
        person_in_team          INTEGER NOT NULL,
        start_time                    TEXT,
        creation_time           INTEGER NOT NULL
);
create table if not exists users(
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT NOT NULL,
        user_id   INTEGER NOT NULL,
        event_id  INTEGER NOT NULL,
        enable    INTEGER NOT NULL
);
create table if not exists tasks(
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        description     TEXT,
        event_id        INTEGER NOT NULL,
        main            INTEGER NOT NULL,
        additional      INTEGER NOT NULL,
        enable          INTEGER NOT NULL,
        UNIQUE(name)
);
create table if not exists teams(
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id        INTEGER NOT NULL,
        main            TEXT NOT NULL,
        additional      TEXT,
        users           TEXT NOT NULL,
        photos          TEXT,
        photos_count    INTEGER NOT NULL
);
'''
    try:
        conn = sqlite3.connect(db_path)
    except Error as e:
        bot.send_message(admin_id,str(e).replace("_",r"\_"))
    finally:
        if conn:
            conn.executescript(init_script)
            return conn

def start_bot():

    @bot.message_handler(commands=['start'])
    def start_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            start_text = '''Здравствуй.
Для регистрации на событие отправь /sign_in
Для выхода из события отправь /quit
Если ты не хочешь получать уведомления о новых ФотоКвестах - отправь /silence  
Для получения даты следующего события - отправь /when  
Вызов справки, узнать о сути мероприятия, показать все команды - /help  
'''
            cursor.execute("DELETE FROM users WHERE event_id = 0 AND user_id = ?",[message.from_user.id])
            cursor.execute("INSERT INTO users (username, user_id, event_id, enable) VALUES (?, ?, 0, 1)",[message.from_user.username, message.from_user.id])
            conn.commit()
            conn.close()
            bot.send_message(message.from_user.id, start_text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['silence'])
    def silence_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            text = '''Вы больше не будете получать уведомления о новых событиях.
Если вы решите изменить свое решение - отправьте /notify  '''
            cursor.execute("UPDATE users SET enable = 0 WHERE user_id = ? AND event_id = 0",[message.from_user.id])
            conn.commit()
            conn.close()
            bot.send_message(message.from_user.id, text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['notify'])
    def notify_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            text = '''Вы снова получаете уведомления на наши события!
Если вы решите изменить свое решение - отправьте /silence  '''
            cursor.execute("UPDATE users SET enable = 1 WHERE user_id = ? AND event_id = 0",[message.from_user.id])
            conn.commit()
            conn.close()
            bot.send_message(message.from_user.id, text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['sign_in'])
    def sign_in_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            start_text = '''Привет, тебя записали на **ФотоКвест**.
На старте первого этапа тебе в личные сообщения придут теги других участников твоей команды.
Скоординируйтесь и выполните задание. Через час вы должны быть на новой точке сбора и уже загрузить 3-5 лучших фотографий от своей команды через бота (просто прикрепи фото и отправь сообщением).
На старте второго этапа процесс повторится.
Если ты не хочешь участвовать в мероприятии вообще или во втором заходе в частности - отправь команду /quit  
'''
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            bot_sends_main_tasks = event[3]
            if not bot_sends_main_tasks:
                start_text += '''Найдите друг друга, подойдите к шляпе (стоит на точке сбора) и возьмите задание.
'''
            start_text += '''Отправьте /help <Название задания>, если не знаете что снимать.
Отправьте /additional , если уже все сняли, а времени еще вагон.  '''
            event_is_private = event[4]
            event_id = event[0]

            user = cursor.execute("SELECT * FROM users WHERE user_id = ? AND event_id = ?;", [message.from_user.id, event_id]).fetchall()
            if user:
                for u in user:
                    cursor.execute("UPDATE users SET enable = 1 WHERE user_id = ?", [message.from_user.id])
            else:
                cursor.execute("INSERT INTO users (username, user_id, event_id, enable) VALUES (?, ?, ?, 1)",[message.from_user.username, message.from_user.id, event_id])

            conn.commit()
            conn.close()
            bot.send_message(message.from_user.id, start_text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['show_my_uid'])
    def show_uid_message(message):
        try:
            bot.reply_to(message,str(message.from_user.id))
        except:
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['clean_base'])
    def clean_base_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                event_id = event[0]
                cursor.execute("DELETE FROM users WHERE event_id = ?", [event_id])
                text = ('Все записи пользователей с event_id = '+ str(event_id) +' удалены').replace("_",r"\_")
                bot.reply_to(message, text)
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()).replace("_",r"\_"))

    @bot.message_handler(commands=['show_bases'])
    def show_bases_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()
                text = []
                for table in tables:
                    text.append(table[0])
                text.remove('sqlite_sequence')
                bot.send_message(message.from_user.id, ", ".join(text).replace("_",r"\_"))
            else:
                bot.reply_to(message, 'У вас нет доступа')

            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['show_base'])
    def show_base_message(message):
        try:
            if message.text == "/show_base" or message.text == "/show_base ":
                bot.reply_to(message, 'Введите название базы. Вывести список баз: /show_bases'.replace("_",r"\_"))
            else:
                if message.from_user.id == admin_id:
                    base = message.text.split()[1]
                    conn = create_connection()
                    cursor = conn.cursor()
                    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()
                    if any(k[0] == base for k in tables):
                        table = cursor.execute("SELECT * FROM " + base +" ORDER BY event_id DESC;").fetchall()
                        if table:
                            columns = cursor.execute("PRAGMA table_info("+base+");").fetchall()
                            column_names = []
                            for column in columns:
                                column_names.append(column[1])
                            bot.send_message(message.from_user.id, ", ".join(column_names).replace("_",r"\_"))
                            bot.send_message(message.from_user.id, str(pprint.pformat(table)).replace("_",r"\_"))
                        else:
                            bot.send_message(message.from_user.id, ('Похоже, база ' + base + ' пуста.').replace("_",r"\_"))
                    else:
                        bot.send_message(message.from_user.id, ('Базы с именем ' + base + ' не существует. /show_bases').replace("_",r"\_"))
                else:
                    bot.reply_to(message, 'У вас нет доступа')

                conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['show_users'])
    def show_users_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:

                text = "Enabled: \n"
                users = cursor.execute("SELECT username FROM users WHERE event_id = ? and enable = 1", [event[0]]).fetchall()
                for user in users:
                    text += "@"+user[0]+" "
                text +="\nTotal: %s\n" % str(len(users))
                text +="\nDisabled: \n"
                users = cursor.execute("SELECT username FROM users WHERE event_id = ? and enable = 0", [event[0]]).fetchall()
                for user in users:
                    text += "@"+user[0]+" "
                text +="\nTotal: %s\n" % str(len(users))
                bot.send_message(message.from_user.id, text.replace("_",r"\_"))

            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['help'])
    def help_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            if message.text == "/help" or message.text == "/help ":
                admins = ""
                for admin in event[1].split(","):
                    admins += "@" + admin + " "
                help_message = '''/sign_in чтобы зайти в игру.
Отправь /quit чтобы выйти из игры.


/help НАЗВАНИЕ ЗАДАНИЯ - для вывода справки по этому заданию (небольшой текст, который возможно поможет тебе найти искомое)
/additional - для дополнительного задания
/silence - перестать получать уведомления о новых ФотоКвестах
/notify - начать их получать  
/when - узнать время следующего события   
Текущие организаторы ФотоКвеста - ''' + admins + '''

По всем вопросам о боте - @Zerginwan  '''
                bot.send_message(message.from_user.id, help_message.replace("_",r"\_"))
                admin_usernames = event[1].split(",")
                if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                     bot.send_message(message.from_user.id, '/additional /add_task /clean_base /disable_task /enable_task /help /quit /remove_user /start /sort /send_photo /show_users /show_my_uid /show_tasks /send_to_all'.replace("_",r"\_"))
                if message.from_user.id == admin_id:
                    bot.send_message(message.from_user.id, '/add_admin /new_event /remove_admin /show_base /show_bases /send_to_all_all'.replace("_",r"\_"))


            else:
                help_task = message.text.replace("/help ","").strip().lower()
                row = cursor.execute("SELECT * FROM tasks WHERE name = ? AND enable = 1", [help_task]).fetchone()
                if row:
                    if row[2] == "":
                        description = "Для этого задания нет описания. Трактуйте его максимально вольно!"
                    else:
                        description = row[2]
                    bot.reply_to(message, str(description).replace("_",r"\_"))
                else:
                    bot.reply_to(message, 'Такое задание не найдено. Проверьте текст на опечатки.')
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['additional'])
    def additional_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            tasks = []
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            tasks_from_all_events = event[5]
            if tasks_from_all_events:
                event_ids = (0, event[0])
            else:
                event_ids = (event[0])
            for task in cursor.execute("SELECT name FROM tasks WHERE additional = 1 AND enable = 1 AND event_id IN "+ str(event_ids) + ";"):
                tasks.append(task[0])

            additional = str(random.choice(tasks))
            id = cursor.execute("SELECT id FROM teams WHERE event_id = '"+ str(event[0]) + "' AND users LIKE '%"+ str(message.from_user.id) +"%' ORDER BY id DESC LIMIT 1;").fetchone()[0]
            cursor.execute("UPDATE teams SET additional = additional || ',' || '"+additional+"' WHERE id = ?",[id])
            for user_id in str(cursor.execute("SELECT users FROM teams ORDER BY id DESC LIMIT 1;").fetchone()[0]).split(","):
                bot.send_message(int(user_id), "Ваше новое дополнительное задание: " + str(random.choice(tasks)).replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))
            raise

    @bot.message_handler(commands=['quit'])
    def quit_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            cursor.execute("UPDATE users SET enable = 0 WHERE user_id = ? AND event_id = ?;", [message.from_user.id, event[0]])
            bot.send_message(message.chat.id, '''Спасибо, что были с нами!
Если вы вычеркнули себя из списка участников по ошибке - отправьте /sign_in'''.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(content_types=['photo'])
    def save_photo(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event_id = cursor.execute("SELECT event_id FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()[0]
            team = cursor.execute("SELECT * FROM teams WHERE event_id = ? AND users LIKE ? ORDER BY id DESC LIMIT 1;",[event_id, "%"+str(message.from_user.id)+"%"]).fetchone()
            output_photo = dirname + '/photos'
            if not os.path.exists(output_photo):
                os.makedirs(output_photo)
            output_photo = os.path.join(output_photo, message.from_user.username + '_' +str(message.date)+'_'+str(message.message_id)+'.jpg')
            if team[5]:
                new_db_photo_text = team[5] + "," + str(output_photo)
            else:
                new_db_photo_text = str(output_photo)
            cursor.execute("UPDATE teams SET photos = ?, photos_count = ? WHERE event_id = ?;",[new_db_photo_text, (int(team[6]) + 1), team[0]])
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(output_photo, 'wb') as new_file:
                new_file.write(downloaded_file)
            conn.commit()
            conn.close()
            bot.reply_to(message, "Фото добавлено")
            bashCommand = "rclone move "+ dirname +"/photos " + remote_point_name + ":photos_"+str(event_id)+"/"
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()

        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0])

    @bot.message_handler(commands=['sort'])
    def sort_all(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            bot_sends_main_tasks = event[3]
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                tasks = []
                tasks_from_all_events = event[5]
                if tasks_from_all_events:
                    event_ids = (0, event[0])
                else:
                    event_ids = (event[0])
                for task in cursor.execute("SELECT name FROM tasks WHERE main = 1 AND enable = 1 AND event_id IN "+ str(event_ids) + ";"):
                    tasks.append(task[0])

                if not tasks:
                    raise "Нет доступных заданий! Вероятно, это приватное собтие с приватными категориями, которые забыли добавить.".replace("_",r"\_")
                if message.text.replace("/sort ","").replace("/sort","") != "":
                    person_in_team = int(message.text.replace("/sort ",""))
                else:
                    person_in_team = event[6]
                users = []
                for user_id in cursor.execute("SELECT user_id FROM users WHERE enable = 1 AND event_id = ?",[event[0]]):
                    users.append(user_id[0])


                teams = {}
                counter = 0
                team_number = 0
                teams.update({team_number: {}})
                last_team_id = 0
                while users:
                        chosen=random.choice(users)
                        if not counter:
                            cursor.execute("INSERT INTO teams (event_id, main, additional, users, photos, photos_count) VALUES (?, ?, '', ?, '', 0)",[event[0],str(random.choice(tasks)),str(chosen)])
                            last_team_id = cursor.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1;").fetchone()[0]
                        else:
                            cursor.execute("UPDATE teams SET users = users || ',' || ? WHERE event_id = ?;",[str(chosen), last_team_id])
                        counter += 1
                        if counter == person_in_team:
                            counter = 0
                        users.remove(chosen)

                for team in cursor.execute("SELECT * FROM teams WHERE event_id = ?;",[event[0]]):
                    if team[4]:
                        mates = ''
                        for user_id in team[4].split(','):
                            mate = cursor.execute("SELECT username FROM users WHERE enable = 1 AND event_id = ? AND user_id = ?;",[event[0], int(user_id)]).fetchone()[0]
                            mates = mates + '@' + mate + ' '

                        message = '''Номер команды: '''+ str(team[0]) + '''
Собери их всех: ''' + mates + '''
Загружай свои выбранные фотографии прямо сюда. Прикрепляй их как фото.
'''
                        if bot_sends_main_tasks:
                            message += '''Ваше задание:
''' + team[2]
                        for user_id in team[4].split(','):
                            bot.send_message(user_id, message.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))
            raise

    @bot.message_handler(commands=['send_photo'])
    def send_photo_to_google_drive(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event_id = cursor.execute("SELECT event_id FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()[0]
            #
            #           apt install -y rclone && rclone config
            # make your own remote point. My was ZerginwanGoogleDrive.
            #
            bashCommand = "rclone move "+ dirname +"/photos " + remote_point_name + ":photos_"+event_id+"/"
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            conn.commit()
            conn.close()
            bot.reply_to(message,'Есть основания полагать, что процесс стартовал успешно.')
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['send_to_all'])
    def send_to_all(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/send_to_all ", "").replace("/send_to_all", "")
                if text != "":
                    for user_id in cursor.execute("SELECT user_id FROM users WHERE event_id = ? AND enable = 1;",[event[0]]):
                        bot.send_message(user_id[0], text.replace("_",r"\_"))
                else:
                    bot.reply_to(message,'После /send_to_all введите сообщение, которое вы хотите отослать всем.'.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['send_to_all_all'])
    def send_to_all_all(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                text = message.text.replace("/send_to_all_all ", "").replace("/send_to_all_all", "")
                if text != "":
                    for user_id in cursor.execute("SELECT user_id FROM users WHERE event_id = 0 AND enable = 1;"):
                        bot.send_message(user_id[0], text.replace("_",r"\_"))
                else:
                    bot.reply_to(message,'После /send_to_all введите сообщение, которое вы хотите отослать всем.'.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))
    @bot.message_handler(commands=['when'])
    def when_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = str(cursor.execute("SELECT admins, title, start_time  FROM events WHERE private = 0 ORDER BY event_id DESC LIMIT 1;").fetchone())
            admins = []
            for admin in event[0].split(','):
                admins.append("@" + admin)
            text = event[1] + "\n" + event[2] + "\nАдминистраторы забега: " + ', '.join(admins)
            bot.send_message(message.from_user.id,text.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))
    @bot.message_handler(commands=['new_event'])
    def new_event_message(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                text = message.text.replace("/new_event ", "").replace("/new_event", "").strip()
                if text != "":
                    new_event = json.loads(text.replace(r"\_", "_"))
                    cursor.execute("INSERT INTO events (admins, title, bot_sends_main_tasks, private, tasks_from_all_events, person_in_team, start_time, creation_time) VALUES(?, ?, ?, ?, ?, ?, ?, ?);",[new_event["admins"], new_event["title"], new_event["bot_sends_main_tasks"], new_event["private"], new_event["tasks_from_all_events"], new_event["person_in_team"], new_event["start_time"], int(time.time())])
                    bot.reply_to(message,'Новое событие запущено. Отправьте /send_all_all чтобы оповестить всех заинтересованных.'.replace("_",r"\_"))

                else:
                    bot.reply_to(message,r'Пришлите верный JSON после /new_event {"admins":"","title":"", "bot_sends_main_tasks": 1, "private": 0, "tasks_from_all_events": 1, "person_in_team": 3, "start_time": ""}'.replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))


    @bot.message_handler(commands=['add_task'])
    def add_task(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/add_task ", "").replace("/add_task", "")
                if text != "":
                    new_task = json.loads(text.replace(r"\_", "_"))
                    cursor.execute("INSERT INTO tasks (name, description, event_id, main, additional, enable) VALUES (?, ?, ?, ?, ?, 1);",[new_task["name"].strip().lower(),new_task["description"],new_task["event_id"],new_task["main"],new_task["additional"]])
                    id = cursor.execute("SELECT id FROM tasks WHERE name = ?;",[new_task["name"].strip().lower()]).fetchone()[0]
                    bot.reply_to(message,('Задание добавлено. id: ' + str(id)).replace("_",r"\_"))

                else:
                    bot.send_message(message.from_user.id,'Пришлите верный JSON после /add_task. event_id: 0 для задачи из общего списка (для всех событий). {"name": "low case name","description":"", "event_id": %i, "main": 1, "additional": 0}'.replace("_",r"\_") % event[0])
            conn.commit()
            conn.close()
        except IntegrityError:
            try:
                conn.close()
            except:
                pass
            bot.reply_to(message,'Задание с таким name уже существует в базе!'.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))


    @bot.message_handler(commands=['enable_task'])
    def enable_task(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/enable_task ", "").replace("/enable_task", "")
                if text != "":
                    cursor.execute("UPDATE tasks SET enable = 1 WHERE id = ?;",[int(text)])
                    bot.reply_to(message,'Задание включено. id: ' + str(text))

                else:
                    bot.reply_to(message,"Пришлите /enable_task ID".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))


    @bot.message_handler(commands=['disable_task'])
    def disable_task(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/disable_task ", "").replace("/disable_task", "")
                if text != "":
                    cursor.execute("UPDATE tasks SET enable = 0 WHERE id = ?;",[int(text)])
                    bot.reply_to(message,'Задание выключено. id: ' + str(text))

                else:
                    bot.reply_to(message,"Пришлите /disable_task ID".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['show_tasks'])
    def show_tasks(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                tasks = {}
                tasks["main_enabled"] = cursor.execute("SELECT id, event_id,name FROM tasks WHERE enable = 1 AND main = 1;").fetchall()
                tasks["main_disabled"] = cursor.execute("SELECT id, event_id,name FROM tasks WHERE enable = 0 AND main = 1;").fetchall()
                tasks["additional_enabled"] = cursor.execute("SELECT id, event_id,name FROM tasks WHERE enable = 1 AND additional = 1;").fetchall()
                tasks["additional_disabled"] = cursor.execute("SELECT id, event_id,name FROM tasks WHERE enable = 0 AND additional = 1;").fetchall()
                tasks["private"] = cursor.execute("SELECT id, event_id,name FROM tasks WHERE event_id = ?;",[event[0]]).fetchall()
                bot.send_message(message.from_user.id, str(pprint.pformat(tasks)).replace("_",r"\_"))

            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['remove_user'])
    def remove_user(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()
            event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                username = message.text.replace("/remove_user ", "").replace("/remove_user", "").replace(r"@","")
                if username != "":
                    cursor.execute("UPDATE users SET enable = 0 WHERE event_id = ? AND username = ?;",[event[0], username])
                    bot.reply_to(message,'Пользователь выключен из списка. Он должен отправить /sign_in , чтобы вернуться.'.replace("_",r"\_"))
                    user_id = cursor.execute("SELECT user_id FROM users  WHERE event_id = ? AND username = ?;",[event[0], username]).fetchone()[0]
                    bot.send_message(user_id, 'Администраторы исключили вас из мероприятия. Чтобы зайти в него снова, отправьте /sign_in'.replace("_",r"\_"))

                else:
                    bot.reply_to(message,"Пришлите /remove_user USERNAME".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['remove_task'])
    def remove_task(message):
        try:
            conn = create_connection()
            cursor = conn.cursor()

            if message.from_user.id == admin_id:
                task_id = message.text.replace("/remove_task ", "").replace("/remove_task", "")
                if task_id != "":
                    task_id = int(task_id)
                    cursor.execute("DELETE FROM tasks WHERE id = ?",[task_id])
                    bot.reply_to(message,'Задание удалено из базы'.replace("_",r"\_"))

                else:
                    bot.reply_to(message,"Пришлите /remove_task ID /show_tasks для того, чтобы узнать ID".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['add_admin'])
    def add_admin(message):
        try:
            if message.from_user.id == admin_id:
                conn = create_connection()
                cursor = conn.cursor()
                event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
                admin_usernames = event[1].split(",")
                username = message.text.replace("/add_admin ", "").replace("/add_admin", "").replace(r"@","").replace(r"\_","_")
                if username != "":
                    cursor.execute("UPDATE events SET admins = admins || ',' || ? WHERE event_id = ?;",[username,event[0]])
                    event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
                    bot.reply_to(message,('Пользователь добавлен в список админов мероприятия. Текущие админы: ' + str(event[1]) ).replace("_",r"\_"))

                else:
                    bot.reply_to(message,"Пришлите /add_admin username".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    @bot.message_handler(commands=['remove_admin'])
    def remove_admin(message):
        try:
            if message.from_user.id == admin_id:
                conn = create_connection()
                cursor = conn.cursor()
                event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
                admin_usernames = event[1].split(",")
                username = message.text.replace("/remove_admin ", "").replace("/remove_admin", "").replace(r"@","")
                if username != "":
                    if username in admin_usernames:
                        admin_usernames.remove(username)
                    admin_usernames = ','.join(admin_usernames)
                    cursor.execute("UPDATE events SET admins = ? WHERE event_id = ?;",[admin_usernames,event[0]])
                    event = cursor.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT 1;").fetchone()
                    bot.reply_to(message,( 'Пользователь удален из списка админов мероприятия. Текущие админы: ' + str(event[1]) ).replace("_",r"\_"))

                else:
                    bot.reply_to(message,"Пришлите /remove_admin username".replace("_",r"\_"))
            conn.commit()
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, str(sys.exc_info()[0]).replace("_",r"\_"))

    while True:
        try:
            print('Started:')
            bot.polling(none_stop=True)

        except Exception as e:
            print(e)  # или просто print(e) если у вас логгера нет,
            # или import traceback; traceback.print_exc() для печати полной инфы
            time.sleep(15)


if __name__ == '__main__':
    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    so = open(stdout, 'a+')
    se = open(stderr, 'a+')
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    
    start_bot()