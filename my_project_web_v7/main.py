from flask import Flask, redirect, render_template
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask import jsonify
from flask import request

from data import db_session
from data.users import User
from data.records import Record

from loginform import LoginForm
from re_form import RegisterForm
from moveform import MoveForm

from random import randrange
from datetime import datetime, timedelta


OLD = 2 # сколько дней должно пройти, чтобы записи считались "старыми" и подлежали удалению
OLD_USER = 5 # сколько дней пользователь должен быть неактивным, чтобы подлежать удалению

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
db_session.global_init('db/bulls.db')


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template("base.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.rep_password.data:
            return render_template('index.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.login.data).first():
            return render_template('index.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User()
        user.name = form.name.data
        user.email = form.login.data
        user.surname = form.surname.data
        user.level = 1
        user.status = "user"
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('index.html', title='Регистрация', form=form)


# Начинается новая игра
@app.route('/new_game',  methods=['GET', 'POST'])
@login_required
def new_game():

    def generate_all_nums(nums, num, alf):
        # генерация всех 4-значных последовательностей из различных цифр
        # к последовательности приписываются два нуля - место под "быков" и "коров"
        if len(num) == 4:
            nums.append([0, 0, num])
        else:
            for i in range(len(alf)):
                nm = num + alf[i]
                a = ''.join(c for c in alf if c != alf[i])
                generate_all_nums(nums, nm, a)

    all_nums = []
    generate_all_nums(all_nums, '', '1234567890') 
    s = all_nums[randrange(len(all_nums))][2]
    games[current_user.email] = {'secret':s, 'ability': all_nums, 'nums':[], 'messages':[]}
    return redirect('/move')


# собственно игра
@app.route('/move',  methods=['GET', 'POST'])
@login_required
def move():

    def bulls_cows(ans, right_ans):
        # быки-коровы, первый параметр - число игрока, второй - "задуманное"
        bulls = sum(1 for i in range(len(ans)) if ans[i] == right_ans[i])
        return bulls, sum(1 for x in ans if x in right_ans) - bulls
    
    history = request.args.get('history', default=0, type=int)
    form = MoveForm()
    message = ""
    if form.validate_on_submit():
        num = form.move._value()
        if len(num) != 4 or len(set(num)) != 4 or not all(c.isdigit() for c in num):
            return render_template('move.html', title='Ваш ход',
                                   form=form,
                                   message="Вводите четыре различных цифры",
                                   number=len(games[current_user.email]))
        if num in games[current_user.email]['nums']:
            return render_template('move.html', title='Ваш ход',
                                   form=form,
                                   message="Такой ход уже был",
                                   number=len(games[current_user.email]))
        games[current_user.email]['nums'].append(num)
        if num == games[current_user.email]['secret']:
            return redirect('/end_game')
        else:
           
            for i in range(len(games[current_user.email]['ability'])):
                games[current_user.email]['ability'][i][0], games[current_user.email]['ability'][i][1] =\
                                                            bulls_cows(num, games[current_user.email]['ability'][i][2])
        # для всех допустимых вариантов чисел вычисляются "быки" и "коровы"
        # по отношению к текущему ходу игрока
            games[current_user.email]['ability'].sort()
        # сортируем, чтобы варианты с одинаковыми "быками" и "коровами" стояли рядом
        # дальше ищем наиболее распространенный набор "быков" и "коров"
            prev = games[current_user.email]['ability'][0]
            k = 0
            mx = 0
            i_mx = 0
            for i in range(1, len(games[current_user.email]['ability'])):
                if games[current_user.email]['ability'][i][0] == prev[0] and \
                   games[current_user.email]['ability'][i][1] == prev[1]:
                    k += 1
                    if k > mx:
                        mx = k
                        i_mx = i
                else:
                    prev = games[current_user.email]['ability'][i]
                    k = 0
            new_secret = games[current_user.email]['ability'][i_mx]

        # оставляем из всех чисел только с выбранными наборами "быки"-"коровы"
            games[current_user.email]['ability'] = list(filter(lambda abc:
                                                               new_secret[0] == abc[0] and
                                                               new_secret[1] == abc[1],
                                                               games[current_user.email]['ability']))
            
        # и "перезагадываем" цифровую последовательность (да-да, она есть, и возможность угадать тоже есть)
            i = randrange(len(games[current_user.email]['ability']))
            games[current_user.email]['secret'] = games[current_user.email]['ability'][i][2]
            
        # а вот эту строку неплохо бы удалить, чтобы играть по-честному (вывод в консоль загаданного числа)
            print('это нужно удалить для честной игры...', games[current_user.email]['secret'])
            
            bulls, cows = bulls_cows(num,  games[current_user.email]['secret'])
            message = "Быков {}, коров {}".format(bulls, cows)
            games[current_user.email]['messages'].append("{}: быков {}, коров {}".format(num, bulls, cows))
            
    # параметр в url histtory отвечает за потребность в показе хода игры        
    if history:
        histories = games[current_user.email]['messages']
    else:
        histories = []

    return render_template('move.html', title='Ход игрока', form=form,
                           number=(len(games[current_user.email]['nums']) + 1),
                           message=message, history=histories)


# минимальная обработка ошибок сервера
@app.errorhandler(500)
def some_error(error):
    return render_template('move.html', title='Небольшие затруднения', form=MoveForm(),
                           number=0,
                           message="Что-то пошло не так, обновите страницу, пожалуйста",
                           history=[])


# конц игры (число угадано) запись игры в БД
@app.route('/end_game',  methods=['GET', 'POST'])
@login_required
def end_game():
    record = Record()
    db_sess = db_session.create_session()
    record.user_id = current_user.id
    record.user_name = current_user.name
    record.score = len(games[current_user.email]['nums'])
    record.secret_num = games[current_user.email]['secret']
    db_sess.add(record)
    db_sess.commit()    
    return redirect('/records_user')


# top 10
@app.route('/records10')
def records_top10():
    db_sess = db_session.create_session()
    records = db_sess.query(Record).order_by(Record.score).limit(10)
    return render_template("records.html", records=records, header="TOP-10")


# результаты игр текущего пользователя
@app.route('/records_user')
@login_required
def records_user():
    db_sess = db_session.create_session()
    records = db_sess.query(Record).order_by(Record.date.desc()).filter(Record.user_id == current_user.id)
    return render_template("records.html", records=records, header="Поздравляем! Ваши результаты")


# удаление записей об играх сроком больше OLD дней. Доступно только пользователям со статусом admin
@app.route('/remove_old_records')
@login_required
def remove_old_records():
    now = datetime.now()
    date_OLD_days_ago = now - timedelta(days=OLD)    
    db_sess = db_session.create_session()
    records = db_sess.query(Record).order_by(Record.date.desc()).filter(Record.date < date_OLD_days_ago)
    return render_template("remove.html", parent_template="records.html",
                           records=records, header="Эти записи игр будут удалены",
                           yes='/remove_records', no='/')


# окончательное удаление старых записей
@app.route('/remove_records')
@login_required
def remove_records():
    now = datetime.now()
    date_OLD_days_ago = now - timedelta(days=OLD)    
    db_sess = db_session.create_session()
    records = db_sess.query(Record).filter(Record.date < date_OLD_days_ago).delete()
    db_sess.commit()
    return redirect('/')


# удаление учетных записей игроков, зарегистрировавшихся ранее чем OLD_USER дней назад и
# не имеющих ни одной записанной игры (или не играл, или удалены за давность).
# Доступно только пользователям со статусом admin
@app.route('/remove_old_users')
@login_required
def remove_old_users():
    now = datetime.now()
    date_OLD_USER_days_ago = now - timedelta(days=OLD_USER)    
    db_sess = db_session.create_session()
    users = db_sess.query(User).join(Record, Record.user_id == User.id,
                                     isouter=True).filter(User.reg_date < date_OLD_USER_days_ago,
                                                          Record.id.is_(None)).distinct(User.email)
    return render_template("remove.html", parent_template="users.html",
                           users=users, header="Эти учетные записи будут удалены",
                           yes='/remove_users', no='/')


# окончательное удаление неактивных пользователей
@app.route('/remove_users')
@login_required
def remove_users():
    now = datetime.now()
    date_OLD_USER_days_ago = now - timedelta(days=OLD_USER)    
    db_sess = db_session.create_session()
    records = db_sess.query(Record).distinct(Record.user_id)    
    users = db_sess.query(User).join(Record, Record.user_id == User.id,
                                     isouter=True).filter(User.reg_date < date_OLD_USER_days_ago,
                                                          Record.id.is_(None)).distinct(User.email)
    removed_id = [user.id for user in users]
    print(removed_id)
    users = db_sess.query(User).filter(User.id.in_(removed_id)).delete(synchronize_session=False)
    db_sess.commit()
    return redirect('/')


# выгрузка статистики - количество зарегистрированных пользователей,
# завершенных игр, незавершенных игр по API запросу
@app.route('/stat',  methods=['GET', 'POST'])
def get_stat():
    db_sess = db_session.create_session()
    stat = {}
    stat["users"] = db_sess.query(User).count()
    stat["games_finished"] = db_sess.query(Record).count()
    stat["games_now"] = len(games)
    print("stat", stat)
    return jsonify(stat)

         
# выгрузка незавершенных игр по API запросу
@app.route('/get_games',  methods=['GET', 'POST'])
def get_games():
    if len(games) > 0:
        out_games = {c: games[c]['messages'] for c in games}
    else:
        out_games = {}
    return jsonify(out_games)      


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    if current_user.email in games:
        del games[current_user.email]
    logout_user()
    return redirect("/")


if __name__ == '__main__':
    games = {}
    app.run()
