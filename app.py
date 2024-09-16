from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from extensions import db  # 从extensions.py导入db实例
from models import Code, Icon, Layout, AppIcon  # 现在这里不会有循环导入问题
from werkzeug.utils import secure_filename
import mysql.connector
import hashlib
import time
import secrets
from mysql.connector import Error
import openai
import logging 
import pyads
import json
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/db_name'
db = SQLAlchemy()
app.secret_key = '123456'  # Ensure to replace with your actual secret key

# Mail server configuration
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'riskerasad@gmail.com'
app.config['MAIL_PASSWORD'] = 'iqmzuxopchoogpdu'

db_config = {
    'user': 'xixi',
    'password': 'Chenxi1213!',
    'host': 'localhost',
    'port': 3308,
    'database': 'userdb'
}

# 用您的OpenAI API密钥替换此处
openai.api_key = os.getenv('OPENAI_API_KEY')
# Initialize a global variable for the PLC connection
plc = None

PLCTYPE_MAP = {
    'BOOL': pyads.PLCTYPE_BOOL,
    'INT': pyads.PLCTYPE_INT,
    'REAL': pyads.PLCTYPE_REAL,
    'STRING': pyads.PLCTYPE_STRING,
    'WORD': pyads.PLCTYPE_WORD,
    # 根据需要添加更多映射
}

# Function to generate a unique reset token
def generate_reset_token(email):
    # Create a unique token using a combination of random bytes and the current timestamp
    random_string = secrets.token_hex(16)  # Generates a secure random string
    timestamp = str(int(time.time()))  # Get the current time as a string
    token = hashlib.sha256((email + random_string + timestamp).encode()).hexdigest()
    return token, timestamp

applications = [
    {"name": "3d-viewer", "icon": "/static/3d-viewer.jpg", "url": "/3d-viewer"},
    {"name": "add", "icon": "/static/add.jpg", "url": "/add"},
    {"name": "AI chat", "icon": "/static/AIchat.jpg", "url": "/AIchat"},
    {"name": "ai-mode", "icon": "/static/ai-mode.jpg", "url": "/ai-mode"},
    {"name": "application", "icon": "/static/application.jpg", "url": "/application"},
    {"name": "automatic", "icon": "/static/automatic.jpg", "url": "/automatic"},
    {"name": "back", "icon": "/static/back.jpg", "url": "/back"},
    {"name": "browser", "icon": "/static/browser.jpg", "url": "/browser"},
    {"name": "calculator", "icon": "/static/calculator.jpg", "url": "/calculator"},
    {"name": "calendar", "icon": "/static/calendar.jpg", "url": "/calendar"},
    {"name": "camera", "icon": "/static/camera.jpg", "url": "/camera"},
    {"name": "ci_note-edit", "icon": "/static/ci_note-edit.jpg", "url": "/ci_note-edit"},
    {"name": "cloud", "icon": "/static/cloud.jpg", "url": "/cloud"},
    {"name": "code", "icon": "/static/code.jpg", "url": "/code"},
    {"name": "collision", "icon": "/static/collision.jpg", "url": "/collision"},
    {"name": "community", "icon": "/static/community.jpg", "url": "/community"},
    {"name": "connection", "icon": "/static/connection.jpg", "url": "/connection"},
    {"name": "consumer_service", "icon": "/static/consumer_service.jpg", "url": "/consumer_service"},
    {"name": "copy", "icon": "/static/copy.jpg", "url": "/copy"},
    {"name": "cycle", "icon": "/static/cycle.jpg", "url": "/cycle"},
    {"name": "delete", "icon": "/static/delete.jpg", "url": "/delete"},
    {"name": "digital-twin", "icon": "/static/digital-twin.jpg", "url": "/digital-twin"},
    {"name": "file", "icon": "/static/file.jpg", "url": "/file"},
    {"name": "finance", "icon": "/static/finance.jpg", "url": "/finance"},
    {"name": "folder", "icon": "/static/folder.jpg", "url": "/folder"},
    {"name": "home", "icon": "/static/home.jpg", "url": "/home"},
    {"name": "kpi", "icon": "/static/kpi.jpg", "url": "/kpi"},
    {"name": "log", "icon": "/static/log.jpg", "url": "/log"},
    {"name": "maintenance", "icon": "/static/maintenance.jpg", "url": "/maintenance"},
    {"name": "manual", "icon": "/static/manual.jpg", "url": "/manual"},
    {"name": "manual-mode", "icon": "/static/manual-mode.jpg", "url": "/manual-mode"},
    {"name": "memo", "icon": "/static/memo.jpg", "url": "/memo"},
    {"name": "mode", "icon": "/static/mode.jpg", "url": "/mode"},
    {"name": "monitoring", "icon": "/static/monitoring.jpg", "url": "/monitoring"},
    {"name": "operations", "icon": "/static/operations.jpg", "url": "/operations"},
    {"name": "pc", "icon": "/static/pc.jpg", "url": "/pc"},
    {"name": "ph_question", "icon": "/static/ph_question.jpg", "url": "/ph_question"},
    {"name": "planning", "icon": "/static/planning.jpg", "url": "/planning"},
    {"name": "pre-processing", "icon": "/static/pre-processing.jpg", "url": "/pre-processing"},
    {"name": "record", "icon": "/static/record.jpg", "url": "/record"},
    {"name": "rename", "icon": "/static/rename.jpg", "url": "/rename"},
    {"name": "report", "icon": "/static/report.jpg", "url": "/report"},
    {"name": "search", "icon": "/static/search.jpg", "url": "/search"},
    {"name": "Servo-viewer", "icon": "/static/Servo-viewer.jpg", "url": "/Servo-viewer"},
    {"name": "setting", "icon": "/static/setting.jpg", "url": "/setting"},
    {"name": "shopping", "icon": "/static/shopping.jpg", "url": "/shopping"},
    {"name": "simulation", "icon": "/static/simulation.jpg", "url": "/simulation"},
    {"name": "team", "icon": "/static/team.jpg", "url": "/team"},
    {"name": "Tool-manager", "icon": "/static/Tool-manager.jpg", "url": "/Tool-manager"},
    {"name": "update", "icon": "/static/update.jpg", "url": "/update"},
    {"name": "user-info", "icon": "/static/user-info.jpg", "url": "/user-info"},
    {"name": "user-settings", "icon": "/static/user-settings.jpg", "url": "/user-settings"},
    {"name": "utility", "icon": "/static/utility.jpg", "url": "/utility"}
]



# 将原来的根路由重定向到登录页面
@app.route('/')
def root():
    return redirect(url_for('login'))

@app.errorhandler(Exception)
def handle_exception(e):
    # 可以根据不同的错误类型进行更详细的处理
    return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/profilelogin', methods=['GET', 'POST'])
def profile_login():
    # message = ''
    # if request.method == 'POST':
    #     username = request.form['username']
    #     conn = mysql.connector.connect(**db_config)
    #     cursor = conn.cursor(dictionary=True)
    #     cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    #     account = cursor.fetchone()
    #     cursor.close()
    #     conn.close()
    #     if account:
    #         session['loggedin'] = True
    #         session['id'] = account['id']
    #         session['username'] = account['username']
    #         return redirect(url_for('index'))
    #     else:
    #         message = 'An error occurred. Please try again.'
    # return render_template('profilelogin.html', message=message)
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = mysql.connector.connect(**db_config)  # Replace with your actual database config
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()  # Fetch the account from the database
        cursor.close()
        conn.close()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('index'))
        else:
            message = 'Incorrect password. Please try again.'
    return render_template('profilelogin.html', message=message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = mysql.connector.connect(**db_config)  # Replace with your actual database config
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()  # Fetch the account from the database
        cursor.close()
        conn.close()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            
            # Handle "Remember Me" functionality
            if 'remember-me' in request.form:
                response = make_response(redirect(url_for('index')))
                response.set_cookie('rememberMe', 'true', max_age=30*24*60*60)  # 30 days
                response.set_cookie('rememberedUser', username, max_age=30*24*60*60)  # 30 days
                return response
            else:
                response = make_response(redirect(url_for('index')))
                response.delete_cookie('rememberMe')
                response.delete_cookie('rememberedUser')
                return response
        else:
            message = 'Incorrect username or password. Please try again.'
    return render_template('login.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        email = request.form['email']
        try:
            with mysql.connector.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
                    account = cursor.fetchone()
                    if account:
                        message = 'Username or email already exists'
                    else:
                        cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
                        conn.commit()
                        message = 'You have successfully registered! You can now log in.'
        except mysql.connector.Error as e:
            message = f"Error connecting to the database: {e}"

    return render_template('register.html', message=message)

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    message = ''
    if request.method == 'POST':
        email = request.form['email']

        try:
            with mysql.connector.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                    account = cursor.fetchone()
                    if account:
                        # Generate a reset token and a timestamp
                        token, timestamp = generate_reset_token(email)

                        # Set an expiration time (e.g., 1 hour from now)
                        expiration_time = int(timestamp) + 3600

                        # Store the token and expiration time in the database
                        cursor.execute('UPDATE users SET reset_token = %s, token_expiry = %s WHERE email = %s', 
                                       (token, expiration_time, email))
                        conn.commit()

                        # Generate the reset link
                        reset_link = url_for('resetpassword', token=token, _external=True)

                        # Send the reset email
                        msg = Message('Password Reset Request', sender='your-email@example.com', recipients=[email])
                        msg.body = f'To Reset your Password, click the following link: {reset_link}'
                        data = {
                            'app_name': 'Kompaki',
                            'title': 'Password Reset Request',
                            'body' : msg.body,
                            'link': reset_link,
                        }
                        msg.html = render_template('email_template.html', data=data)
                        mail.send(msg)

                        message = 'A password reset link has been sent to your email.'
                    else:
                        message = 'Email address not found.'
        except mysql.connector.Error as e:
            message = f"Error connecting to the database: {e}"

    return render_template('forgotpassword.html', message=message)

@app.route('/resetpassword/<token>', methods=['GET', 'POST'])
def resetpassword(token):
    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                # Verify the token and check if it has expired
                cursor.execute('SELECT * FROM users WHERE reset_token = %s', (token,))
                user = cursor.fetchone()
                if not user or user['token_expiry'] < int(time.time()):
                    flash('Invalid or expired token.', 'error')
                    return redirect(url_for('index'))

                if request.method == 'POST':
                    password = request.form['password']
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute('UPDATE users SET password = %s, reset_token = NULL, token_expiry = NULL WHERE reset_token = %s', (hashed_password, token))
                    conn.commit()
                    flash('Your password has been reset.', 'success')
                    return redirect(url_for('login'))
    except mysql.connector.Error as e:
        flash(f"Error connecting to the database: {e}", 'error')

    return render_template('resetpassword.html', token=token)


@app.route('/choose_settings')
def choose_settings():
    if 'loggedin' in session:
        # 假设我们有一些用户设置信息，例如头像等
        profiles = [
            {'id': 1, 'name': 'Profile 1', 'avatar_url': 'url_to_avatar_1'},
            {'id': 2, 'name': 'Profile 2', 'avatar_url': 'url_to_avatar_2'},
            # 更多的头像
        ]
        return render_template('choose_settings.html', username=session['username'], profiles=profiles)
    return redirect(url_for('login'))

@app.route('/layouts')
def layouts():
    if 'loggedin' in session:
        profiles = [
            {'id': 1, 'name': 'Profile 1', 'avatar_url': 'url_to_avatar_1'},
            {'id': 2, 'name': 'Profile 2', 'avatar_url': 'url_to_avatar_2'},
        ]
        return render_template('layouts.html', username=session['username'], profiles=profiles)
    return redirect(url_for('login'))

@app.route('/set_profile', methods=['POST'])
def set_profile():
    if 'loggedin' in session:
        selected_profile_id = request.form.get('profile')
        # 在这里，您可以将用户的选择保存到数据库
        # ...
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/icons')
def icons():
    # 查询数据库获取所有的应用图标信息
    icons = Icon.query.all()
    return render_template('icons.html', icons=icons)

@app.route('/add-icon', methods=['POST'])
def add_icon():
    data = request.get_json()
    name = data['name']
    image_path = data['image_path']
    link_url = data['link_url']
    category = data['category']

    # 将应用图标数据保存到数据库中
    new_icon = AppIcon(name=name, image_path=image_path, link_url=link_url, category=category)
    db.session.add(new_icon)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Icon added successfully'})


@app.route('/save_layout', methods=['POST'])
def save_layout():
    data = request.json
    user_id = data.get('user_id')
    layout_config = data.get('layout_config')

    # 在这里将布局信息保存到数据库中，这取决于你的数据库模型和存储逻辑
    # 你需要根据自己的数据库结构来实现这部分逻辑

    # 假设你有一个名为Layout的模型来保存布局信息
    # 这里仅提供一个简单的示例
    for config in layout_config:
        src = config['src']
        alt = config['alt']
        label = config['label']
        href = config['href']
        container_id = config['containerId']

        # 这里假设你已经定义了一个 Layout 模型来存储布局信息
        new_layout = Layout(user_id=user_id, src=src, alt=alt, label=label, href=href, container_id=container_id)
        db.session.add(new_layout)

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Layout saved successfully'})

@app.route('/get_layout', methods=['GET'])
def get_layout():
    user_id = request.args.get('user_id')

    # 在这里从数据库中获取用户的布局信息
    # 假设你已经定义了一个 Layout 模型来存储布局信息
    layout_config = Layout.query.filter_by(user_id=user_id).all()

    # 将布局信息转换为字典列表
    layout_config_dict = []
    for layout in layout_config:
        layout_dict = {
            'src': layout.src,
            'alt': layout.alt,
            'label': layout.label,
            'href': layout.href,
            'containerId': layout.container_id
        }
        layout_config_dict.append(layout_dict)

    return jsonify({'layout_config': layout_config_dict})



@app.route('/index')
def index():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('index.html')
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/visitor')
def visitor():
    return render_template('visitorIndex.html')

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class App(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    icon_path = db.Column(db.String(100))
    link = db.Column(db.String(100))

class FolderApp(db.Model):
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('app.id'), primary_key=True)


# @app.route('/ask', methods=['POST'])
# def ask_gpt():
#     try:
#         question = request.json['question']
#         # Make a request to the OpenAI API to get a response from ChatGPT
#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "user", "content": question}
#             ]
#         )
#
#         if response.choices:
#             return jsonify({'response': response.choices[0].text.strip()})
#         else:
#             return jsonify({'error': 'No response from ChatGPT'}), 500
#
#     except Exception as e:
#         app.logger.error("Error occurred: %s", str(e))  # 使用 Flask 的日志系统记录异常信息
#         return jsonify({'error': str(e)}), 500
#


# 定义 ask_gpt 函数，输入问题，返回 GPT-3 的回答
def ask_gpt(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": question}
            ]
        )
        result = response['choices'][0]['message']['content'].strip()
        return result
    except Exception as e:
        print("Error occurred:", str(e))
        return "An error occurred while processing your request."

# 定义路由，处理 POST 请求
@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if request.method == 'POST':
        question = request.json['question']
        answer = ask_gpt(question)
        response = {
            'answer' : answer
        }
        return jsonify(response)
    else:
        return render_template('index.html')



@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error("An internal server error occurred: %s", e)
    return "Internal Server Error", 500

@app.route('/add_folder', methods=['POST'])
def add_folder():
    # Code to add a new folder to the database
    pass

@app.route('/add_app_to_folder', methods=['POST'])
def add_app_to_folder():
    # Code to add an app to a folder
    pass

@app.route('/get_apps_in_folder/<int:folder_id>', methods=['GET'])
def get_apps_in_folder(folder_id):
    # Code to get all apps in a folder
    pass

# pyads实现，twincat连接
@app.route('/open-port', methods=['POST'])
def open_port():
    global plc
    data = request.json
    ams_net_id = data['amsNetID']
    port = int(data['port'])  # Convert port to an integer
    try:
        if plc is None:  # 如果plc尚未初始化，则进行初始化
            plc = pyads.Connection(ams_net_id, port)
        if not plc.is_open:  # 如果连接尚未打开，则打开连接
            plc.open()
        return jsonify({'status': 'success', 'message': 'PLC connection opened successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/read-variable', methods=['POST'])
def read_variable():
    global plc
    data = request.json
    variable_name = data['variableName']
    data_type = data['dataType']
    try:
        plc_data_type = getattr(pyads, 'PLCTYPE_' + data_type.upper())
        value = plc.read_by_name(variable_name, plc_data_type)
        return jsonify({"status": "success", "value": value, "message": f"Variable {variable_name} read successfully"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/write-variable', methods=['POST'])
def write_variable():
    global plc
    data = request.json
    variable_name = data['variableName']
    value = data['value']
    data_type = data['dataType']
    try:
        if data_type in PLCTYPE_MAP:
            plc_data_type = PLCTYPE_MAP[data_type]
            # 针对BOOL和数字类型的值，你可能需要根据data_type进一步处理value的类型
            if data_type == 'BOOL':
                value = value.lower() in ('true', '1', 't')
            elif data_type in ['INT', 'REAL']:
                value = float(value) if data_type == 'REAL' else int(value)

            plc.write_by_name(variable_name, value, plc_data_type)
            return jsonify({'status': 'success', 'message': 'Variable written successfully'})
        else:
            return jsonify({'status': 'error', 'message': f'Unsupported data type: {data_type}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/subpage')
def subpage():
    return render_template('subpage.html')

@app.route('/Customized_Mode')
def customized_mode():
    # Code to get all apps in a folder
    return render_template('Customized_Mode.html')

@app.route('/service')
def service():
    return render_template('service.html')

@app.route('/aichat')
def aichat():
    return render_template('aichat.html')

@app.route('/setting')
def setting():
    return render_template('setting.html')

@app.route('/monitoring')
def monitoring():
    return render_template('monitoring.html')

@app.route('/userinfo')
def userinfo():
    if 'loggedin' in session:
        return render_template('userinfo.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/search')
def search():
    query = request.args.get('query', '').lower()
    results = [app for app in applications if query in app['name'].lower()]
    return jsonify(results)

@app.route('/connection')
def connection():
    return render_template('connection.html')

@app.route('/code')
def code():
    return render_template('code.html')

@app.route('/upload-code', methods=['POST'])
def upload_code():
    if 'codeFile' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})

    file = request.files['codeFile']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})

    filename = secure_filename(file.filename)
    file_content = file.read().decode('utf-8')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 插入代码数据到数据库
        cursor.execute('INSERT INTO code (code_name, code_content) VALUES (%s, %s)', (filename, file_content))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'codeName': filename})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def save_code_to_database(code_name, code_content):
    try:
        new_code = Code(code_name=code_name, code_content=code_content)
        db.session.add(new_code)
        db.session.commit()
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        app.logger.error(f'Failed to save code to database: {e}')  # Log the error
        # Handle the error, e.g., return an error response or raise an exception

@app.route('/get-code')
def get_code():
    code_name = request.args.get('name')
    if not code_name:
        return jsonify({'error': 'Missing code name parameter'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)
        cursor.execute('SELECT code_content FROM code WHERE code_name = %s', (code_name,))
        code = cursor.fetchone()
        cursor.close()
        conn.close()
        if code:
            return jsonify({'code_content': code[0]})
        else:
            return jsonify({'error': 'Code not found'}), 404
    except mysql.connector.Error as e:
        app.logger.error(f'Database error: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/get-all-codes')
def get_all_codes():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('SELECT code_name FROM code')
        codes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([code[0] for code in codes])  # 返回所有代码名称的列表
    except mysql.connector.Error as e:
        app.logger.error(f'Database error: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/delete-code', methods=['POST'])
def delete_code():
    try:
        code_name = request.form['name']  # 从表单数据中获取代码名称
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM code WHERE code_name = %s', (code_name,))
        conn.commit()  # 提交更改
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Code deleted successfully'})
    except mysql.connector.Error as e:
        app.logger.error(f'Database error: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/save-code', methods=['POST'])
def save_code():
    code_name = request.args.get('name')
    new_content = request.json.get('new_content')  # 从请求体中获取新的代码内容
    if not code_name or new_content is None:
        return jsonify({'error': 'Missing data'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # 更新代码内容
        cursor.execute('UPDATE code SET code_content = %s WHERE code_name = %s', (new_content, code_name,))
        conn.commit()  # 提交事务以保存更改
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Code updated successfully'})
    except mysql.connector.Error as e:
        app.logger.error(f'Database error: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/rename-code', methods=['POST'])
def rename_code():
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 更新数据库中的代码名称
        cursor.execute('UPDATE code SET code_name = %s WHERE code_name = %s', (new_name, old_name))
        conn.commit()

        # 检查是否有行受影响
        if cursor.rowcount == 0:
            return jsonify(success=False, error="Old file does not exist in database.")
        
        cursor.close()
        conn.close()
        return jsonify(success=True)
    except mysql.connector.Error as e:
        app.logger.error(f'Database error: {e}')
        return jsonify(success=False, error=str(e))



# 创建数据库连接
def create_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

# 读取应用图标信息
@app.route('/get-icons', methods=['GET'])
def get_icons():
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name, image_path, link_url FROM icons")
    icons = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(icons)

# 添加应用图标信息
# @app.route('/add-icon', methods=['POST'])
# def add_icon():
#     connection = create_db_connection()
#     cursor = connection.cursor()
#     data = request.get_json()
#     query = "INSERT INTO icons (name, image_path, link_url) VALUES (%s, %s, %s)"
#     cursor.execute(query, (data['name'], data['image_path'], data['link_url']))
#     connection.commit()
#     cursor.close()
#     connection.close()
#     return jsonify({'status': 'success', 'message': 'Icon added'})

# 删除应用图标信息
@app.route('/delete-icon/<int:icon_id>', methods=['DELETE'])
def delete_icon(icon_id):
    connection = create_db_connection()
    cursor = connection.cursor()
    query = "DELETE FROM icons WHERE id = %s"
    cursor.execute(query, (icon_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({'status': 'success', 'message': 'Icon deleted'})

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@app.route('/log')
def log():
    return render_template('log.html')

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/PC operation')
def PC_operation():
    return render_template('PC operation.html')

@app.route('/task')
def task():
    return render_template('task.html')

@app.route('/Tool manager')
def Tool_manager():
    return render_template('Tool manager.html')

@app.route('/Calendar')
def Calendar():
    return render_template('Calendar.html')

@app.route('/File manager')
def File_manager():
    return render_template('File manager.html')

@app.route('/Cycle time estimation')
def Cycle_time_estimation():
    return render_template('Cycle time estimation.html')

@app.route('/Digital twin')
def Digital_twin():
    return render_template('Digital twin.html')

@app.route('/3D viewer')
def viewer():
    return render_template('3D viewer.html')

@app.route('/NC operation')
def NC_operation():
    return render_template('NC operation.html')

@app.route('/Collision advance')
def Collision_advance():
    return render_template('Collision advance')

@app.route('/Data logger')
def Data_logger():
    return render_template('Data logger.html')

@app.route('/Maintenance manager')
def Maintenance_manager():
    return render_template('Maintenance manager.html')

@app.route('/Servo viewer')
def Servo_viewer():
    return render_template('Servo viewer.html')

@app.route('/KPI')
def KPI():
    return render_template('KPI.html')

@app.route('/team board')
def team_board():
    return render_template('team board.html')

@app.route('/cloud')
def cloud():
    return render_template('cloud.html')

@app.route('/finance')
def finance():
    return render_template('finance.html')

@app.route('/update')
def update():
    return render_template('update.html')

@app.route('/consumer_service')
def consumer_service():
    return render_template('consumer_service.html')

@app.route('/shopping')
def shopping():
    return render_template('shopping.html')

@app.route('/manual')
def manual():
    return render_template('manual.html')

@app.route('/memo')
def memo():
    return render_template('memo.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/browser')
def browser():
    return render_template('browser.html')

@app.route('/setting1')
def setting1():
    return render_template('setting1.html')

@app.route('/maintenance')
def maintenance():
    return render_template('maintenance.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0', port=5000, debug=True)
