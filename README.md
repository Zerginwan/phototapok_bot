# Фото_Тапок_Бот  
Текущий проект - @FotoTapok_bot  
Бот для проведения фото-квестов.  

## Установка и настройка  

Для функционирования требуется rclone  
```
git clone https://github.com/Zerginwan/phototapok_bot.git
cd ./phototapok_bot
pip3 install -r requirements.txt
apt install -y rclone && rclone config
cp ./settings.ini.example ./settings.ini
```  
Заполните settings.ini!
### Запуск:  
```  
python3 tapok.py
```  
### Демонизация:  
```  
cat > /etc/systemd/system/tapok.service << EOF
[Unit]
Description=Telegram bot '@FotoTapok_bot'
After=syslog.target
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/tapok.py
RestartSec=10
Restart=always

[Install]
WantedBy=multi-user.target

EOF


systemctl daemon-reload
systemctl enable tapok.service
systemctl start tapok.service
systemctl status tapok.service
```  
## Управление  
Админ - управляющий текущего ивента. Может быть несколько.  
Суперадмин. Управляющий бота. Задается через указание id в settings.ini  
Узнать можно через /show_my_uid

Команды:  
Команда | Описание | Аргументы | Доступ
:-------| :---------------- | ----------: | ---------:
/start  | Вносит пользвателя в общий список.| - | Все
/silence  | Бот перестает оповещать пользователя через /send_all_all  | -       | Все
/notify   | Пользователь снова получает общие оповещения | -    | Все
/sign_in | Пользователь вносится в базу данных текущего ивента и становится активным | - | Все
/clean_base | Стирает таблицу пользователей текущего ивента | - | Админ, Суперадмин
/show_base | ВЫводит всю таблицу | base_name | Суперадмин
/show_bases | ВЫводит список таблиц | - | Суперадмин
/show_users | Выводит всех активных пользователей текущего ивента | - | Админ, Суперадмин
/help | Выводит справку по командам для пользователя. Выводит список команд для Админа и Суперадмина. |  В случае передачи аргумента - выводит описание задания [Название задания] | Все
/additional | Выводит случайное задание из списка дополнительных | - | Все
/quit | Делает пользователя неактивным в текущем ивенте. Для повторной активации - отправить /sign_in | - | Все
/sort | Разбивает игроков текущего ивента на новые команды. Каждому игроку приходит номер команды, контакты сокомандников, задание. | В качестве аргумента можно передать количество людей в команде  [person_in_team] | Админ, Суперадмин
/send_photo | Отправляет  загруженные в бота фотки в облако. Для дебага и форс-мажоров, так как сейчас фотки грузятся автоматом. | - | Админ, Суперадмин
/send_to_all | Отправляет ТЕКСТ всем участникам текущего ивента | ТЕКСТ | Админ, Суперадмин
/send_to_all_all | Отправяет ТЕКСТ всем пользователям в базе. Используется для анонса нового мероприятия. | ТЕКСТ | Суперадмин
/show_my_uid | Возвращает message_from_user.id. Используется для того, чтобы узнать свой admin_id  без танцев с бубном. | - | Все
/new_event | Создает новый ивент. Старый считается закрытым. | JSON: {"admins":"список админов через запятую","title":"Название ивента (алиас)", "bot_sends_main_tasks": 1 (1 - бот раздает задания. 0 - нужна шляпа), "private": 0 (зарезервировано), "tasks_from_all_events": 1 (берутся ли общие задания или используются только те, которые привязаны напрямую к этому ивенту. 1\|0 ), "person_in_team": 3 (сколько человек в команде поумолчанию), start_time: "human-readable описание того, когда ивент"}| Суперадмин
/add_task| Добавить задание в список | JSON: {"name": "low case name","description":"опциональное описание", "event_id": 0\|current_event_id, "main": 1 (является ли основным заданием), "additional": 0(является ли дополнительным заданием)}| Админ, Суперадмин
/enable_task | Задание теперь может выпасть при распределении | Task_id | Админ, Суперадмин
/disable_task | Задание теперь не может выпасть при распределении | Task_id | Админ, Суперадмин
/remove_task | Задание удаляется из базы | Task_id | Суперадмин
/show_tasks | Выводит список всех заданий | - | Админ, Суперадмин
/remove_user | Делает пользователя @username неактивным в текущем ивенте | username | Админ, Суперадмин
/add_admin | Добавляет в список админов текущего ивента пользователя @username| username | Суперадмин
/remove_admin |Убирает из списка админов текущего ивента пользователя @username| username | Суперадмин
/when |Показывает время следующего события| - | Все
