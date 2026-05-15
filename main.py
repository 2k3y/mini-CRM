import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('index.html', students=students)

@app.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        full_name_ru = request.form['full_name_ru']
        full_name_zh = request.form['full_name_zh']
        passport = request.form['passport']
        address = request.form['address']
        program = request.form['program']

        file = request.files.get('document')
        filename = ''
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO students (full_name_ru, full_name_zh, passport, address, program, document_filename)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (full_name_ru, full_name_zh, passport, address, program, filename))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
