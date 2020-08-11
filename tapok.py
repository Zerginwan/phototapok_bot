import telebot, random, subprocess, os, sys, sqlite3, configparser, json, time, pprint
from daemonize import Daemonize
from sqlite3 import Error
#
# Your user id (message.from_user.id).
# Main admin - can change event, add event-admins, recieve errors etc.
#
config = configparser.ConfigParser()  # создаём объекта парсера
config.read("settings.ini")  # читаем конфиг в формате ini
admin_id = config["Telegram"]["admin_id"]
token = config["Telegram"]["token"]
remote_point_name = config["Rclone"]["remote_point_name"]
bot = telebot.TeleBot(token, parse_mode=config["Telegram"]["parse_mode"])

# Find directory, where tapok.py is
dirname = os.path.dirname(os.path.abspath(__file__))

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    # event with rowid = 0 - 'all events'
    init_script = '''create table if not exists events(
        admins                  TEXT,
        title                   TEXT,
        bot_sends_main_tasks    INTEGER NOT NULL,
        private                 INTEGER NOT NULL,
        tasks_from_all_events   INTEGER NOT NULL,
        person_in_team          INTEGER NOT NULL,
        when                    TEXT,
        creation_time           INTEGER NOT NULL
);
create table if not exists users(
        username  TEXT NOT NULL,
        user_id   INTEGER NOT NULL,
        event_id  INTEGER NOT NULL,
        enable    INTEGER NOT NULL
);
create table if not exists tasks(
        name            TEXT NOT NULL,
        description     TEXT,
        event_id        INTEGER NOT NULL,
        main            INTEGER NOT NULL,
        additional      INTEGER NOT NULL,
        enable          INTEGER NOT NULL,
        UNIQUE(name)
);
create table if not exists teams(
        event_id        INTEGER NOT NULL,
        main            TEXT NOT NULL,
        additional      TEXT,
        users           TEXT NOT NULL,
        photos          TEXT,
        photos_count    INTEGER NOT NULL
);
'''
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        bot.send_message(admin_id,str(e).replace("_",r"\_"))
    finally:
        if conn:
            conn.executescript(init_script)
            return conn

def main():
#    
# Tasks in main 'tasks' dict must had to be written in low-case!!!!
#

    @bot.message_handler(commands=['start'])
    def start_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            start_text = '''Здравствуй.  
Для регистрации на событие отправь /sign_in  
Для выхода из события отправь /quit  
Если ты не хочешь получать уведомления о новых ФотоКвестах - отправь /silence  '''
            cursor.executescript("INSERT INTO users (username, user_id, event_id, enable) VALUES (?, ?, 0, 1)",[message.from_user.username, message.from_user.id])
            conn.close()
            bot.send_message(message.from_user.id, start_text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['silence'])
    def silence_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            text = '''Вы больше не будете получать уведомления о новых событиях.  
Если вы решите изменить свое решение - отправьте /notify  '''
            cursor.executescript("UPDATE users SET enable = 0 WHERE user_id = ? AND event_id = 0",[message.from_user.id])
            conn.close()
            bot.send_message(message.from_user.id, text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['notify'])
    def notify_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            text = '''Вы снова получаете уведомления на наши события!  
Если вы решите изменить свое решение - отправьте /silence  '''
            cursor.executescript("UPDATE users SET enable = 1 WHERE user_id = ? AND event_id = 0",[message.from_user.id])
            conn.close()
            bot.send_message(message.from_user.id, text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['sign_in'])
    def sign_in_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            start_text = '''Привет, тебя записали на **ФотоКвест**.  
На старте первого этапа тебе в личные сообщения придут теги других участников твоей команды.  
Скоординируйтесь и выполните задание. Через час вы должны быть на новой точке сбора и уже загрузить 3-5 лучших фотографий от своей команды через бота (просто прикрепи фото и отправь сообщением).  
На старте второго этапа процесс повторится.  
Если ты не хочешь участвовать в мероприятии вообще или во втором заходе в частности - отправь команду /quit   
'''
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            bot_sends_main_tasks = event[3]
            if not bot_sends_main_tasks:
                start_text += '''Найдите друг друга, подойдите к шляпе (стоит на точке сбора) и возьмите задание.  
'''
            start_text += '''Отправьте /help <Название задания>, если не знаете что снимать.  
Отправьте /additional , если уже все сняли, а времени еще вагон.  '''
            
            all_event = cursor.executescript("SELECT * FROM events WHERE rowid = '0';")
            event_is_private = event[4]
            event_id = event[0]

            user = cursor.executescript("SELECT * FROM users WHERE user_id = ? AND event_id = ?;", [message.from_user.id, event_id])
            if user:
                for u in user:
                    cursor.executescript("UPDATE users SET enable = 1 WHERE user_id = ?", [message.from_user.id])
            else:
                cursor.executescript("INSERT INTO users (username, user_id, event_id, enable) VALUES (?, ?, ?, 1)",[message.from_user.username, message.from_user.id, event_id])
            
            conn.close()
            bot.send_message(message.from_user.id, start_text.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))


    @bot.message_handler(commands=['clean_base'])
    def clean_base_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                event_id = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")[0]
                cursor.executescript("DELETE FROM users WHERE event_id = ?", [event_id])
                bot.reply_to(message, 'Все записи пользователей с event_id = '+ event_id +' удалены')
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['show_base'])
    def show_base_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                table = cursor.executescript("SELECT * FROM events")
                bot.send_message(message.from_user.id, str(table).replace("_",r"\_"))
                table = cursor.executescript("SELECT * FROM users")
                bot.send_message(message.from_user.id, str(table).replace("_",r"\_"))
                table = cursor.executescript("SELECT * FROM tasks")
                bot.send_message(message.from_user.id, str(table).replace("_",r"\_"))
                table = cursor.executescript("SELECT * FROM teams")
                bot.send_message(message.from_user.id, str(table).replace("_",r"\_"))
            else:
                bot.reply_to(message, 'У вас нет доступа')
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['show_users'])
    def show_users_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                new_message = ""
                for user in cursor.executescript("SELECT username FROM users WHERE event_id = ?", [event[0]]):
                    new_message = new_message + " @" + user[0]
                bot.send_message(message.from_user.id, new_message.replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['help'])
    def help_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
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
Текущие организаторы ФотоКвеста - ''' + admins + '''  
  
По всем вопросам о боте - @Zerginwan  '''
                bot.send_message(message.from_user.id, help_message.replace("_",r"\_"))
                admin_usernames = event[1].split(",")
                if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                     bot.send_message(message.from_user.id, '/additional /add_task /clean_base /disable_task /enable_task /help /quit /remove_user /start /sort /send_photo /show_users /show_tasks /send_to_all'.replace("_",r"\_"))
                if message.from_user.id == admin_id:
                    bot.send_message(message.from_user.id, '/add_admin /new_event /remove_admin /show_base /send_to_all_all'.replace("_",r"\_"))


            else:
                tasks_from_all_events = event[5]
                if tasks_from_all_events:
                    using_event_id = (0, event[0])
                else:
                    using_event_id = (event[0])
                help_task = message.text.replace("/help ","").strip().lower()
                tasks = ()
                for row in cursor.execute("SELECT * FROM tasks WHERE name = ? AND event_id IN ? AND enable = 1", [help_task, using_event_id]):
                    if row[2]:
                        description = row[2]
                    else:
                        description = "Для этого задания нет описания. Трактуйте его максимально вольно!"
                if description:
                    bot.reply_to(message, description.replace("_",r"\_"))
                else:
                    bot.reply_to(message, 'Такое задание не найдено. Проверьте текст на опечатки.')
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['additional'])
    def additional_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            tasks = []
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            tasks_from_all_events = event[5]
            if tasks_from_all_events:
                event_ids = (0, event[0])
            else:
                event_ids = (event[0])
            for task in cursor.executescript("SELECT name FROM tasks WHERE additional = 1 AND enable = 1 AND event_id IN ?", [event_ids]):
                tasks.append(task[0])
            conn.close()
            additional = str(random.choice(tasks))
            cursor.executescript("UPDATE teams SET additional = additional || ',' || ? WHERE event_id IN ? AND users LIKE '%?%'", [event_ids, str(message.from_user.id)])
            for user_id in cursor.executescript("SELECT users FROM teams WHERE rowid = ?;",[cursor.lastrowid])[0].split(","):
                bot.send_message(int(user_id), "Ваше новое дополнительное задание: " + str(random.choice(tasks)).replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['quit'])
    def quit_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            cursor.executescript("UPDATE users SET enable = 0 WHERE user_id = ? AND event_id = ?;", [message.from_user.id, event[0]])
            bot.send_message(message.chat.id, '''Спасибо, что были с нами!  
Если вы вычеркнули себя из списка участников по ошибке - отправьте /sign_in'''.replace("_",r"\_"))
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(content_types=['photo'])
    def save_photo(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event_id = cursor.executescript("SELECT rowid FROM events ORDER BY rowid DESC LIMIT 1;")[0]
            team = cursor.executescript("SELECT rowid FROM teams WHERE event_id = ? AND user_id = ?;",[event_id, message.from_user.id])
            output_photo = dirname + '/photos'
            if not os.path.exists(output_photo):
                os.makedirs(output_photo)
            output_photo = os.path.join(output_photo, message.from_user.username + '_' +str(message.date)+'_'+str(message.message_id)+'.jpg')
            if team[5]:
                new_db_photo_text = team[5] + "," + str(output_photo)
            else:
                new_db_photo_text = str(output_photo)
            cursor.executescript("UPDATE teams SET photo = ?, photo_count = ? WHERE rowid = ?;",[new_db_photo_text, sum(team[6], 1), team[0]])
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(output_photo, 'wb') as new_file:
                new_file.write(downloaded_file)
            conn.close()
            bot.reply_to(message, "Фото добавлено")

        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0])

    @bot.message_handler(commands=['sort'])
    def sort_all(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            bot_sends_main_tasks = event[3]
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                tasks = []
                tasks_from_all_events = event[5]
                if tasks_from_all_events:
                    event_ids = (0, event[0])
                else:
                    event_ids = (event[0])
                for task in cursor.executescript("SELECT name FROM tasks WHERE main = 1 AND enable = 1 AND event_id IN ?", [event_ids]):
                    tasks.append(task[0])

                if not tasks:
                    raise "Нет доступных заданий! Вероятно, это приватное собтие с приватными категориями, которые забыли добавить.".replace("_",r"\_")
                if message.text.replace("/sort ",""):
                    person_in_team = int(message.text.replace("/sort ",""))
                else:
                    person_in_team = event[6]
                users = []
                for user_id in cursor.executescript("SELECT user_id FROM users WHERE enable = 1 AND event_id = ?",[event[0]]):
                    users.append(user_id[0])


                teams = {}
                counter = 0
                team_number = 0
                teams.update({team_number: {}})
                last_team_row_id = 0
                while users:
                        chosen=random.choice(users)
                        if not counter:
                            cursor.executescript("INSERT INTO teams (event_id, main, additional, users, photos, photos_count]) VALUES (?, ?, '', ?, '', 0)",[event[0],str(random.choice(tasks)),str(chosen)])
                            last_team_row_id = cursor.lastrowid
                        else:
                            cursor.executescript("UPDATE teams SET users = users || ',' || ? WHERE rowid = ?;",[str(chosen), last_team_row_id])
                        counter += 1
                        if counter == person_in_team:
                            counter = 0
                        users.remove(chosen)

                for team in cursor.executescript("SELECT * FROM teams WHERE event_id = ?;",[event[0]]):
                    if team[4]:
                        mates = ''
                        for user_id in team[4].split(','):
                            mate = cursor.executescript("SELECT username FROM users WHERE enable = 1 AND event_id = ? AND user_id = ?;",[event[0], int(user_id)])
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
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['send_photo'])
    def send_photo_to_google_drive(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event_id = cursor.executescript("SELECT rowid FROM events ORDER BY rowid DESC LIMIT 1;")[0]
            #
            #           apt install -y rclone && rclone config
            # make your own remote point. My was ZerginwanGoogleDrive.
            #
            bashCommand = "rclone move "+ dirname +"/photos " + remote_point_name + ":photos_"+event_id+"/"
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            conn.close()
            bot.reply_to(message,'Есть основания полагать, что процесс стартовал успешно.')
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['send_to_all'])
    def send_to_all(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/send_to_all ", "")
                if text:
                    for user_id in cursor.executescript("SELECT user_id FROM users WHERE event_id = ? AND enable = 1;",[event[0]]):
                        bot.send_message(user_id[0], text.replace("_",r"\_"))
                else:
                    bot.reply_to(message,'После /send_to_all введите сообщение, которое вы хотите отослать всем.'.replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    @bot.message_handler(commands=['send_to_all_all'])
    def send_to_all_all(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                text = message.text.replace("/send_to_all_all ", "")
                if text:
                    for user_id in cursor.executescript("SELECT user_id FROM users WHERE event_id = 0 AND enable = 1;"):
                        bot.send_message(user_id[0], text.replace("_",r"\_"))
                else:
                    bot.reply_to(message,'После /send_to_all введите сообщение, которое вы хотите отослать всем.'.replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    @bot.message_handler(commands=['new_event'])
    def new_event_message(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            if message.from_user.id == admin_id:
                text = message.text.replace("/new_event ", "").strip()
                if text:
                    new_event = json.loads(text)
                    cursor.executescript("INSERT INTO events (admins, title, bot_sends_main_tasks, private, tasks_from_all_events, person_in_team, when, creation_time) VALUES(?, ?, ?, ?, ?, ?, ?, ?);",[new_event["admins"], new_event["title"], new_event["bot_sends_main_tasks"], new_event["private"], new_event["tasks_from_all_events"], new_event["person_in_team"], new_event["when"], int(time.time())])
                    bot.reply_to(message,'Новое событие запущено. Отправьте /send_all_all чтобы оповестить всех заинтересованных.')
                    
                else:
                    bot.reply_to(message,r"Пришлите верный JSON после /new_event. {'admins':'','title':'', 'bot_sends_main_tasks': 1, 'private': 0, 'tasks_from_all_events': 1, 'person_in_team': 3, when: ''}".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    
    @bot.message_handler(commands=['add_task'])
    def add_task(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/add_task ", "")
                if text:
                    new_task = json.loads(text)
                    cursor.executescript("INSERT INTO tasks (name, description, event_id, main, additional, enable) VALUES (?, ?, ?, ?, ?, 1);",[new_task["name"],new_task["description"],new_task["event_id"],new_task["main"],new_task["additional"]])
                    bot.reply_to(message,'Задание добавлено. rowid: ' + str(cursor.lastrowid))
                        
                else:
                    bot.reply_to(message,"Пришлите верный JSON после /add_task. event_id: 0 для задачи из общего списка (для всех событий). {'name': 'low case name','description':'', 'event_id': %i, 'main': 1, 'additional': 0, 'enable': 1}".replace("_",r"\_") % event[0])
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    @bot.message_handler(commands=['enable_task'])
    def enable_task(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/enable_task ", "")
                if text:
                    cursor.executescript("UPDATE tasks SET enable = 1 WHERE rowid = ?;",int(text))
                    bot.reply_to(message,'Задание включено. rowid: ' + str(cursor.lastrowid))
                        
                else:
                    bot.reply_to(message,"Пришлите /enable_task ID".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['disable_task'])
    def disable_task(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                text = message.text.replace("/disable_task ", "")
                if text:
                    cursor.executescript("UPDATE tasks SET enable = 0 WHERE rowid = ?;",[int(text)])
                    bot.reply_to(message,'Задание выключено. rowid: ' + str(cursor.lastrowid))
                        
                else:
                    bot.reply_to(message,"Пришлите /disable_task ID".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    @bot.message_handler(commands=['show_tasks'])
    def show_tasks(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                tasks = {}
                tasks["main_enabled"] = cursor.executescript("SELECT rowid,name FROM tasks WHERE enable = 1 AND main = 1;")
                tasks["main_disabled"] = cursor.executescript("SELECT rowid,name FROM tasks WHERE enable = 0 AND main = 1;")
                tasks["additioanl_enabled"] = cursor.executescript("SELECT rowid,name FROM tasks WHERE enable = 1 AND additional = 1;")
                tasks["additioanl_disabled"] = cursor.executescript("SELECT rowid,name FROM tasks WHERE enable = 0 AND additional = 1;")
                tasks["private"] = cursor.executescript("SELECT rowid,name FROM tasks WHERE event_id = ?;"[event[0]])
                bot.send_message(message.from_user.id, str(pprint.pformat(tasks)).replace("_",r"\_"))

            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['remove_user'])
    def remove_user(message):
        try:
            conn = create_connection(dirname+"/tapok_sqlite.db")
            cursor = conn.cursor()
            event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
            admin_usernames = event[1].split(",")
            if message.from_user.id == admin_id or message.from_user.username in admin_usernames:
                username = message.text.replace("/remove_user ", "").replace(r"@","")
                if username:
                    cursor.executescript("UPDATE users SET enable = 0 WHERE event_id = ? AND username = ?;",[event[0], username])
                    bot.reply_to(message,'Пользователь выключен из списка. Он должен отправить /sign_in , чтобы вернуться.'.replace("_",r"\_"))
                    user_id = cursor.executescript("SELECT user_id FROM users  WHERE event_id = ? AND username = ?;",[event[0], username])[0]
                    bot.send_message(user_id, 'Администраторы исключили вас из мероприятия. Чтобы зайти в него снова, отправьте /sign_in'.replace("_",r"\_"))
                        
                else:
                    bot.reply_to(message,"Пришлите /remove_user username".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    @bot.message_handler(commands=['add_admin'])
    def add_admin(message):
        try:
            if message.from_user.id == admin_id:
                conn = create_connection(dirname+"/tapok_sqlite.db")
                cursor = conn.cursor()
                event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
                admin_usernames = event[1].split(",")
                username = message.text.replace("/add_admin ", "").replace(r"@","")
                if username:
                    cursor.executescript("UPDATE events SET admins = admins || ',' || ? WHERE event_id = ?;",[username,event[0]])
                    event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
                    bot.reply_to(message,'Пользователь добавлен в список админов мероприятия. Текущие админы: '.replace("_",r"\_") + str(event[1]))
                        
                else:
                    bot.reply_to(message,"Пришлите /add_admin username".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))

    @bot.message_handler(commands=['remove_admin'])
    def remove_admin(message):
        try:
            if message.from_user.id == admin_id:
                conn = create_connection(dirname+"/tapok_sqlite.db")
                cursor = conn.cursor()
                event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
                admin_usernames = event[1].split(",")
                username = message.text.replace("/remove_admin ", "").replace(r"@","")
                if username:
                    admin_usernames.remove(username)
                    admin_usernames = str(admin_usernames.join(','))
                    cursor.executescript("UPDATE events SET admins = ? WHERE event_id = ?;",[admin_usernames,event[0]])
                    event = cursor.executescript("SELECT * FROM events ORDER BY rowid DESC LIMIT 1;")
                    bot.reply_to(message,'Пользователь удален из списка админов мероприятия. Текущие админы: '.replace("_",r"\_") + str(event[1]))
                        
                else:
                    bot.reply_to(message,"Пришлите /remove_admin username".replace("_",r"\_"))
            conn.close()
        except:
            try:
                conn.close()
            except:
                pass
            bot.send_message(admin_id, sys.exc_info()[0].replace("_",r"\_"))
    
    bot.polling()

if __name__ == '__main__':
        myname=os.path.basename(sys.argv[0])
        pidfile='/tmp/%s.pid' % myname       # any name
        daemon = Daemonize(app=myname,pid=pidfile, action=main)
        daemon.start()
        # For disabling daemonization: comment all in this section. Uncomment line below.
        #main()