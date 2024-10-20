from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import subprocess  # For managing the stream (start/stop)
import os  # To handle paths

app = Flask(__name__)

# Secret key for session management
app.secret_key = '1a2b3c4d5e6d7g8h9i10'

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'  # Replace with your MySQL password
app.config['MYSQL_DB'] = 'loginapp'

# Initialize MySQL
mysql = MySQL(app)

# Global variable for stream process
ffmpeg_process = None

# ------------------- Login/Registration Code -------------------

@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            flash("Incorrect username/password!", "danger")
    return render_template('auth/login.html', title="Login")

@app.route('/pythonlogin/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM accounts WHERE username LIKE %s", [username])
        account = cursor.fetchone()
        if account:
            flash("Account already exists!", "danger")
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash("Invalid email address!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash("Username must contain only characters and numbers!", "danger")
        elif not username or not password or not email:
            flash("Incorrect username/password!", "danger")
        else:
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, email, password))
            mysql.connection.commit()
            flash("You have successfully registered!", "success")
            return redirect(url_for('login'))
    elif request.method == 'POST':
        flash("Please fill out the form!", "danger")
    return render_template('auth/register.html', title="Register")

@app.route('/')
def home():
    if 'loggedin' in session:
        return render_template('home/home.html', username=session['username'], title="Home")
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        return render_template('auth/profile.html', username=session['username'], title="Profile")
    return redirect(url_for('login'))

# ------------------- Streaming Functionality -------------------

def start_ffmpeg():
    global ffmpeg_process
    # Define the FFmpeg command
    command = [
        'ffmpeg',
        '-re',
        '-i', '-',  # Read from stdin
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-maxrate', '3000k',
        '-bufsize', '6000k',
        '-pix_fmt', 'yuv420p',
        '-g', '50',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-f', 'flv',
        'rtmp://srs-aws.zehntech.net/live/stream'  # Replace with your RTMP URL
    ]

    # Start the FFmpeg process with stdin as input
    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE)

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global ffmpeg_process

    if 'loggedin' not in session:
        return redirect(url_for('login'))  # Ensure user is logged in before streaming

    if ffmpeg_process is None:
        start_ffmpeg()

    # Read video chunk from request
    video_chunk = request.files['video_chunk'].read()

    if ffmpeg_process:
        ffmpeg_process.stdin.write(video_chunk)  # Pipe video chunk to ffmpeg

    return jsonify({'message': 'Video chunk received'})

# ------------------- Stream Host and Watch Pages -------------------

@app.route('/host_stream')
def host_stream():
    if 'loggedin' in session:
        return render_template('stream/host.html', username=session['username'], title="Host Stream")
    return redirect(url_for('login'))

@app.route('/watch_stream')
def watch_stream():
    return render_template('stream/watcher.html', title="Watch Stream")

# ------------------- Run App -------------------
if __name__ == '__main__':
    app.run(debug=True)