import os
import io
import zipfile
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file, abort
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db
from docxtpl import DocxTemplate

# 1. СОЗДАЕМ ПРИЛОЖЕНИЕ
app = Flask(__name__)

# Настройка папки для загрузки сканов паспортов
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку uploads, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Инициализируем БД при старте
init_db()


# 2. ОПИСЫВАЕМ МАРШРУТЫ

# Главный экран (Картотека)
@app.route('/')
def index():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    return render_template('index.html', students=students)


# Экран «Добавление»
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


# Маршрут для отдачи загруженных файлов (сканов паспортов)
@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], name)


# Экран «Карточка студента»
@app.route('/student/<int:student_id>')
def student_profile(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()

    if student is None:
        abort(404, description="Студент не найден")

    return render_template('student.html', student=student)


# Генерация Word документа (Требование №8)
@app.route('/generate_word/<int:student_id>')
def generate_word(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()

    if student is None:
        abort(404, description="Студент не найден")

    # Безопасный абсолютный путь к шаблону в корне проекта
    template_path = os.path.join(app.root_path, 'template.docx')

    if not os.path.exists(template_path):
        abort(500, description="Файл шаблона 'template.docx' не найден в корне проекта!")

    # Загружаем шаблон
    doc = DocxTemplate(template_path)

    # Словарь с данными для замены заглушек в Word
    context = {
        'ФИО_РУС': student['full_name_ru'],
        'ФИО_КИТ': student['full_name_zh'] if student['full_name_zh'] else '—',
        'ПАСПОРТ': student['passport'],
        'АДРЕС': student['address'] if student['address'] else '—',
        'ПРОГРАММА': student['program']
    }

    doc.render(context)

    # Сохраняем документ в оперативную память
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    # Формируем имя файла (заменяем пробелы на подчеркивания)
    filename = f"Досье_{student['full_name_ru'].replace(' ', '_')}.docx"

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


# Система Бэкапа (Требование №10)
@app.route('/backup')
def backup():
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Добавляем базу данных
        if os.path.exists('crm.db'):
            zf.write('crm.db', 'crm.db')

        # Добавляем папку со сканами
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Сохраняем относительный путь внутри архива, чтобы структура папок не ломалась
                    arcname = os.path.relpath(file_path, start='.')
                    zf.write(file_path, arcname)

    memory_file.seek(0)
    return send_file(
        memory_file,
        as_attachment=True,
        download_name='crm_backup.zip',
        mimetype='application/zip'
    )


# 3. ЗАПУСКАЕМ ПРИЛОЖЕНИЕ
if __name__ == '__main__':
    app.run(debug=True, port=5000)