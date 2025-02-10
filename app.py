import os
import json
from flask import Flask, redirect, request, render_template, url_for, jsonify
from datetime import date, datetime, timedelta
from flask_mail import Mail, Message
from twilio.rest import Client
from flask import session
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Secret key for session management

# APScheduler-ის ინიციალიზაცია
scheduler = BackgroundScheduler()

# CORS კონფიგურაცია
CORS(app)  # ეს გაძლევთ CORS-ის პოვებას ნებისმიერი დომენისგან


# Flask-Mail კონფიგურაცია
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = print(os.getenv('PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  

mail = Mail(app)

# Twilio კონფიგურაცია
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
client = Client(account_sid, auth_token)

# JSON ფაილის სახელია tasks.json
filename = 'users.json'

# დრო
datetoday = date.today().strftime("%m_%d_%y")

# JSON ფაილის შექმნა, თუ ის არ არსებობს
if not os.path.exists(filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=4)


def get_users():
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []  # თუ ფაილი არ არსებობს, დავაბრუნოთ ცარიელი სია


def save_users(tasklist):
    """შეინახავს ახლანდელ tasklist-ს JSON ფაილში"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tasklist, f, ensure_ascii=False, indent=4)
        print("Saved task list:", tasklist)  # print statement


def updatetasklist(tasklist):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(tasklist, f, indent=4)

################## როუტების ფუნქცია #########################

@app.route('/')
def login_sigup():
    tasklist = get_users()  # no need to pass 'users' anymore
    return render_template('login_signup.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=tasklist, l=len(tasklist))

# ახალი ტასკის დამატება
@app.route('/addtask', methods=['POST'])
def add_task():
    user = request.form.get('user')
    project = request.form.get('project')
    deadline = request.form.get('deadline')
    user_email = request.form.get('email')  # დაამატეთ email
    user_phone = request.form.get('phone')  # დაამატეთ phone

    new_task = {
        "user": user,
        "project": project,
        "deadline": deadline,
        "email": user_email,  # Email-ის დამატება
        "phone": user_phone   # ტელეფონის ნომრის დამატება
    }
    
    tasklist = get_users()  # get_users() no longer requires 'users'
    tasklist.append(new_task)
    updatetasklist(tasklist)

    # 24 საათით ადრე გაგზავნის დროს შეგვიძლია დავაყენოთ
    reminder_time = datetime.strptime(deadline, '%Y-%m-%d') - timedelta(days=1)
    # დროის გადაწევა, რომ შემოწმება მოხდეს უფრო სწრაფად
    reminder_time = reminder_time - timedelta(minutes=10)  

    # დაგეგმეთ მეილის გაგზავნა
    scheduler.add_job(send_reminder_email, 'date', run_date=reminder_time, args=[user_email, project, deadline])

    return render_template('home.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=tasklist, l=len(tasklist), message="დედლაინი წარმატებით გაიგზავნა!")

# 24 საათით ადრე ელექტრონული ფოსტის გაგზავნა
def send_reminder_email(user_email, project, deadline):
    subject = f"პროექტის დედლაინი {project}"
    body = f"მოგესალმებით,\n\nთქვენ მიერ შერჩეული პროექტის დედლაინი მოახლოვდა. გთხოვთ გაითვალისწინოთ, რომ პროექტზე '{project}' რეგისტრაცია სრულდება: {deadline}.\n წარმატებები!"
    
    send_email(user_email, subject, body)  # Email გაგზავნა

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], sender='')
    msg.body = body
    mail.send(msg)

def send_sms(to, body):
    message = client.messages.create(
        body=body,
        from_=twilio_phone_number,
        to=to
    )

# ტესტის ელ-ფოსტა
@app.route("/send_test_email")
def send_test_email():
    msg = Message("Hello from Flask", 
                  sender="",  
                  recipients=[""])
    msg.body = "This is a test email sent from Flask."
    mail.send(msg)
    return "Test email sent!"

# ტასკის წაშლა
@app.route('/deltask', methods=['GET'])
def remove_task():
    task_index = int(request.args.get('deltaskid'))
    tasklist = get_users()
    if 0 <= task_index < len(tasklist):
        tasklist.pop(task_index)
        save_users(tasklist)
    return render_template('home.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=tasklist, l=len(tasklist))

# სიის გასუფთავება
@app.route('/clear')
def clear_list():
    save_users([])  # სიის გასუფთავება
    return render_template('home.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=[], l=0)

@app.route('/register', methods=['POST'])
def handle_sign_up():
    fullname = request.form.get('fullname', 'Default Full Name')
    age = request.form.get('age')
    phone = request.form.get('phone')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    # დაჟინებული შემოწმება, რომ პაროლები ემთხვევა
    if password != confirm_password:
        return jsonify({"success": False, "message": "პაროლები არ ემთხვევა"})

    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(password)

    # მომხმარებლის მონაცემების შენახვა
    user_data = {
        "fullname": fullname,
        "age": age,
        "phone": phone,
        "email": email,
        "password": hashed_password,  # პაროლი ჰეშირებულია
    }

    # JSON ფაილში შენახვა
    users = get_users()  # get_users() now works without passing an argument
    users.append(user_data)  # დაამატეთ ახალი მომხმარებელი
    save_users(users)  # შეინახეთ განახლებული მონაცემები
    return jsonify({"success": True, "message": "რეგისტრაცია წარმატებით განხორციელდა!"})


@app.route('/login_signup')
def login_signup():
    return render_template('login_signup.html')


@app.route('/logo_animation')
def logo_animation():
    return render_template('logo_animation.html')


# Route to display the Login page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/tutorials')
def tutorials():
    return render_template('tutorials.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

# Route to handle Login form submission
@app.route('/login', methods=['POST'])
def handle_login():
    email = request.form.get('email')  # .get() ფუფუნებას გთავაზობს
    password = request.form.get('password')

    if not email or not password:
        return "Missing email or password", 400

    # შენიშვნა: ამ ლოგიკას შეუძლია ვალიდაცია და სხვა რეაქციები
    return f"Email: {email}, Password: {password}"
        
@app.route('/save-user', methods=['POST'])
def save_user():
    data = request.json  # მიიღე მონაცემები JSON ფორმატში
    try:
        with open('users.json', 'a') as file:
            json.dump(data, file)
            file.write('\n')  # ახალი მონაცემი ახალი ხაზით
        return jsonify({"status": "success", "message": "User data saved"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query')
    return jsonify({"message": f"Searching for: {query}"})



if __name__ == '__main__':
    try:
        # APScheduler-ის დაწყება Flask-ის დაწყებამდე
        scheduler.start()
        # Flask აპლიკაციის გაშვება
        app.run(debug=True, port=5000)
    except (KeyboardInterrupt, SystemExit):
        # APScheduler შეწყვეტა Flask-ის გაჩერებისას
        scheduler.shutdown()  # APScheduler-ის შეწყვეტა
