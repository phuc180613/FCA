import sqlite3
import os
from flask import Flask, render_template_string, request, session, redirect, g, send_from_directory, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import threading
import time

def run_localtunnel(port, subdomain):
    """Hàm này sẽ chạy lệnh lt trong nền"""
    # Đợi 3 giây để Flask khởi động hoàn toàn trước khi mở tunnel
    time.sleep(3)
    
    # Lệnh chạy localtunnel với subdomain bạn chọn
    # Nếu không muốn dùng subdomain cố định, hãy bỏ '--subdomain', subdomain
    cmd = f"lt --port {port} --subdomain {subdomain}"
    
    print(f"\n[Hệ thống] Đang khởi tạo tunnel tại port {port}...")
    # Chạy lệnh hệ thống
    process = subprocess.Popen(cmd, shell=True)
    
    # Giữ cho tiến trình sống
    process.wait()

# Cấu hình dự án của Phúc
PORT = 5000
MY_SUBDOMAIN = "FCA-vn" # Bạn có thể đổi tên này theo ý thích
app = Flask(__name__)
app.secret_key = 'phuc123' 
app.config.update(UPLOAD_FOLDER='uploads', DATABASE='slides.db')

# Tạo thư mục uploads nếu chưa có
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# 1. CẤU HÌNH DATABASE
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Tạo bảng users
        db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
        # Tạo bảng slides
        db.execute('''CREATE TABLE IF NOT EXISTS slides 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, subject TEXT, 
               grade TEXT, filename TEXT, author_id INTEGER, 
               views INTEGER DEFAULT 0, downloads INTEGER DEFAULT 0, 
               status INTEGER DEFAULT 1, lesson_number TEXT)''')
        # Tạo bảng comments
        db.execute('CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, slide_id INTEGER, author_name TEXT, content TEXT)')
        
        # Cập nhật cột mới nếu thiếu (tránh lỗi khi chạy lại trên db cũ)
        try:
            db.execute('ALTER TABLE slides ADD COLUMN lesson_number TEXT')
        except:
            pass
        db.commit()

# Gọi hàm tạo database ngay khi chạy code
init_db()

# 2. GIAO DIỆN HTML (Đã được gộp và làm sạch, giữ nguyên Style)
html = '''
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Foundation of Creative App</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<style>
/* --- PHẦN STYLE GỐC CỦA BẠN (Đã gộp) --- */
:root { 
    --primary: #4361ee;
    --secondary: #7209b7;
    --accent: #4cc9f0;
    --bg: #f8f9fa;
    --vang: #ffc107; 
    --do: #ff4444;
    --nen-toi: #121212; 
    --nen-card: #1e1e1e;
    --chu-trang: #ffffff; 
}

body { background-color: var(--bg); font-family: 'Inter', 'Segoe UI', sans-serif; color: #2b2d42; transition: background-color 0.3s, color 0.3s; padding-top: 20px;}

/* NAVBAR */
.navbar, .navbar-custom {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 15px 25px;
    margin-bottom: 30px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    z-index: 1000;
}


/* SEARCH HERO */
.search-hero-wrapper {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    padding: 60px 20px;
    border-radius: 30px;
    margin-bottom: 40px;
    color: white;
    text-align: center;
}

/* INPUT VÀ SELECT */
input, select, textarea, .form-control, .form-select {
    height: 45px;
    border-radius: 8px !important;
}


/* --- DARK MODE --- */
body.dark-mode {
    background-color: var(--nen-toi) !important;
    color: var(--chu-trang) !important;
}
body.dark-mode .navbar-custom, 
body.dark-mode .card, 
body.dark-mode .slide-card,
body.dark-mode .bai-popup-window,
body.dark-mode .comment-box {
    background-color: var(--nen-card) !important;
    color: var(--chu-trang) !important;
    border-color: #333 !important;
}

/* Chữ trong Dark Mode */
body.dark-mode h1, body.dark-mode h2, body.dark-mode h3, body.dark-mode h4,
body.dark-mode label, body.dark-mode p, body.dark-mode span, 
body.dark-mode .text-dark {
    color: #FFFFFF !important;
}
body.dark-mode .text-muted { color: #aaa !important; }

/* Input trong Dark Mode (Giữ nền trắng chữ đen như yêu cầu) */
body.dark-mode input, body.dark-mode select, body.dark-mode textarea, 
body.dark-mode .form-control, body.dark-mode .form-select {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 1px solid #ced4da !important;
}
body.dark-mode input::placeholder { color: #6c757d !important; }


/* Link Footer */
.footer-link, .btn-release {
    color: inherit; text-decoration: none; display: inline-block; padding: 5px 10px; border: 1px solid currentColor; border-radius: 20px; transition: 0.3s;
}
body.dark-mode .btn-release, body.dark-mode .footer-link { color: white !important; border-color: white !important; }
body.dark-mode .btn-release:hover { background: white !important; color: black !important; }

@keyframes bounceIn {
    0% { opacity: 0; transform: scale(0.3) translateY(-20px); }
    70% { transform: scale(1.05); }
    100% { opacity: 1; transform: scale(1); }
}
</style>
</head>
<body>

<div class="container">
    <div class="navbar-custom shadow-sm d-flex justify-content-between align-items-center">
        <h2 class="m-0 fw-bold text-primary">Foundation <span class="text-secondary"> of</span><class="m-0 fw-bold text-primary"> Creative App</h2>
        <div class="d-flex align-items-center gap-3">
            {% if session.get('logged_in') %}
                <a href="/" class="btn btn-link text-decoration-none">Trang chủ</a>
<span class="d-none d-md-block text-dark">CĐTFSVN:</span>
        <a href="/ideas" class="btn btn-link text-decoration-none">Ý tưởng & Chuẩn bị</a>
        <a href="/updates" class="btn btn-link text-decoration-none">Cập nhật</a>
        <a href="/collection" class="btn btn-link text-decoration-none">Bộ sưu tập</a>
                        <span class="d-none d-md-block text-dark">👨‍🏫 Chào, <b>{{ session.username }}</b></span>
                        <a href="/logout" class="btn btn-outline-danger btn-modern">Đăng xuất</a>
            {% else %}
<a href="/" class="btn btn-link text-decoration-none">Trang chủ</a>
<span class="d-none d-md-block text-dark">CĐTFSVN:</span>
        <a href="/ideas" class="btn btn-link text-decoration-none">Ý tưởng & Chuẩn bị</a>
        <a href="/updates" class="btn btn-link text-decoration-none">Cập nhật</a>
        <a href="/collection" class="btn btn-link text-decoration-none">Bộ sưu tập</a>
                <span class="d-none d-md-block text-muted small"></span>
                <a href="/login" class="btn btn-primary btn-modern shadow-sm">Đăng nhập</a>
                <a href="/register" class="btn btn-link text-decoration-none fw-bold">Đăng ký</a>
            {% endif %}
        </div>
    </div>  

    <div class="search-hero-wrapper">
        <h1 class="display-4 fw-bold mb-3">Trang web chính thức của Foundation of Creative App</h1>
    </div>
    <span class="d-none d-md-block text-dark">Trang web này được Trần Hồ Bảo Phúc (Coder) làm ra để thể hiện quá trình development của Ứng dụng CĐTFSVN.</span>
    <footer class="mt-5 pt-5 pb-4 text-center border-top">
        <p class="text-muted small">Chế độ sáng/tối</p>
        <button id="darkModeBtn" class="dark-mode-toggle me-2 btn btn-sm btn-outline-dark rounded-circle" style="width:40px;height:40px;">
            <i class="fa-solid fa-moon"></i>
        </button>
        <footer class="mt-5 pt-5 pb-4 text-center border-top">
        <div class="mt-4">
            <a href="https://heylink.me/phuc180613/" class="footer-link m-1">Liên hệ Trần Hồ Bảo Phúc</a>
            <a href="https://heylink.me/FoundationofCreativeApp/" class="footer-link m-1">Liên hệ Foundation of Creative App</a>
        <footer class="mt-5 pt-5 pb-4 text-center border-top">  
            <a href="https://drive.google.com/file/d/19IW_2BBA_3etU-vnBCQjxMjQe5qDJgn-/view?usp=sharing" class="footer-link m-1">ĐKDV& ĐKSD Foundation of Creative App</a>
                    <footer class="mt-5 pt-5 pb-4 text-center border-top">  
            <a href="/release-notes" class="btn-release m-1">Phiên bản 0.1 beta 1 (000001)</a>
        </div>
        <p class="text-muted small mt-3"> © 2026 Trần Hồ Bảo Phúc | © 2026 Foundation of Creative App</p>
    </footer>

</div>

<script>

    // DARK MODE
    const darkModeBtn = document.getElementById('darkModeBtn');
    const body = document.body;

    function applyDarkMode() {
        body.classList.add('dark-mode');
        darkModeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
        darkModeBtn.classList.replace('btn-outline-dark', 'btn-outline-light');
    }

    function removeDarkMode() {
        body.classList.remove('dark-mode');
        darkModeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
        darkModeBtn.classList.replace('btn-outline-light', 'btn-outline-dark');
    }

    if (localStorage.getItem('dark-mode') === 'enabled') {
        applyDarkMode();
    }

    darkModeBtn.onclick = function() {
        if (body.classList.contains('dark-mode')) {
            removeDarkMode();
            localStorage.setItem('dark-mode', 'disabled');
        } else {
            applyDarkMode();
            localStorage.setItem('dark-mode', 'enabled');
        }
    }
</script>
</body>
</html>
'''



# 4. CÁC ROUTE CHỨC NĂNG

@app.route('/')
def index():
    db = get_db()
    current_user_id = None
    if session.get('logged_in'):
        user = db.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
        if user: current_user_id = user['id']

    query = request.args.get('search', '')
    sql = "SELECT slides.*, users.username as author_name FROM slides JOIN users ON slides.author_id = users.id"
    params = []
    
    if query:
        sql += " WHERE slides.title LIKE ? OR slides.subject LIKE ? OR slides.lesson_number LIKE ?"
        params.extend(['%'+query+'%', '%'+query+'%', '%'+query+'%'])
    
    rows = db.execute(sql + " ORDER BY slides.id DESC", params).fetchall()
    
    # Xử lý định dạng file và màu sắc
    slides = []
    for row in rows:
        s = dict(row)
        ext = os.path.splitext(s['filename'])[1].lower()
        if ext in ['.pptx', '.ppt']:
            s['file_type'], s['file_color'] = '📊 PowerPoint', 'bg-danger'
        elif ext in ['.docx', '.doc']:
            s['file_type'], s['file_color'] = '📄 Word', 'bg-primary'
        elif ext in ['.xlsx', '.xls']:
            s['file_type'], s['file_color'] = '📈 Excel', 'bg-success'
        elif ext in ['.mp3', '.mp4']:
            s['file_type'], s['file_color'] = '📸 Video', 'bg-warning'
        elif ext in ['.jpg', '.png']:
            s['file_type'], s['file_color'] = '🖼️ Ảnh', 'bg-warning'
        elif ext in ['.pdf']:
            s['file_type'], s['file_color'] = '📄 Tài liệu PDF', 'bg-dark'
        elif ext in ['.url']:
            s['file_type'], s['file_color'] = '🌐 Trang web', 'bg-secondary'
        else:
             s['file_type'], s['file_color'] = '📄 File', 'bg-secondary'
        slides.append(s)

    comments = db.execute('SELECT * FROM comments').fetchall()
    return render_template_string(html, slides=slides, comments=comments, current_user_id=current_user_id, search_query=query)

@app.route('/download/<int:id>')
def download(id):
    db = get_db()
    slide = db.execute('SELECT * FROM slides WHERE id = ?', (id,)).fetchone()
    if slide:
        db.execute('UPDATE slides SET downloads = downloads + 1, views = views + 1 WHERE id = ?', (id,))
        db.commit()
        return send_from_directory(app.config['UPLOAD_FOLDER'], slide['filename'])
    return redirect('/')

@app.route('/comment/<int:id>', methods=['POST'])
def comment(id):
    if session.get('logged_in'):
        db = get_db()
        db.execute('INSERT INTO comments (slide_id, author_name, content) VALUES (?,?,?)', (id, session['username'], request.form['content']))
        db.commit()
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not session.get('logged_in'): return redirect('/login')
    
    if request.method == 'POST':
        f = request.files['file']
        if f:
            name = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
            db = get_db()
            user = db.execute('SELECT id FROM users WHERE username = ?', (session['username'],)).fetchone()
            db.execute('INSERT INTO slides (title, subject, grade, filename, author_id, lesson_number, status) VALUES (?,?,?,?,?,?,1)',
             (request.form['title'], request.form['subject'], request.form['grade'], name, user['id'], request.form.get('lesson_number', '')))
            db.commit()
            return redirect('/')
    
    return render_template_string('''<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><div class="container mt-5" style="max-width:400px"><form method="post" enctype="multipart/form-data" class="card p-4 shadow-lg border-0" style="border-radius:25px;"><h3>📤 Đăng bài giảng mới</h3><input name="title" class="form-control mb-3" placeholder="Tiêu đề" required><input name="subject" class="form-control mb-3" placeholder="Môn học"><input name="lesson_number" class="form-control mb-3" placeholder="Số bài (Ví dụ: Bài 1)"><select name="grade" class="form-select mb-3">{% for i in range(1,13) %}<option value="{{i}}">Lớp {{i}}</option>{% endfor %}</select><input type="file" name="file" class="form-control mb-4" required><button class="btn btn-success w-100 py-2 fw-bold">Đăng ngay</button><a href="/" class="btn btn-link w-100 mt-2 text-muted">Hủy</a></form></div>''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
        if user and check_password_hash(user['password'], request.form['password']):
            session['logged_in'] = True
            session['username'] = user['username']
            return redirect('/')
        else:
            return "Sai tên đăng nhập hoặc mật khẩu! <a href='/login'>Thử lại</a>"
            
    return render_template_string('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><div class="container mt-5" style="max-width:400px"><form method="post" class="card p-4 shadow-lg border-0" style="border-radius:25px;"><h3>🔐 Đăng nhập</h3><input name="username" class="form-control mb-3" placeholder="Tên đăng nhập" required><input type="password" name="password" class="form-control mb-3" placeholder="Mật khẩu" required><button class="btn btn-primary w-100 py-2 fw-bold">Đăng nhập</button><a href="/register" class="btn btn-link w-100 mt-2 text-decoration-none">Chưa có tài khoản? Đăng ký</a></form></div>')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        try:
            hashed_pw = generate_password_hash(request.form['password'])
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (request.form['username'], hashed_pw))
            db.commit()
            return redirect('/login')
        except:
            return "Tên đăng nhập đã tồn tại! <a href='/register'>Quay lại</a>"
            
    return render_template_string('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><div class="container mt-5" style="max-width:400px"><form method="post" class="card p-4 shadow-lg border-0" style="border-radius:25px;"><h3>📝 Đăng ký tài khoản</h3><input name="username" class="form-control mb-3" placeholder="Tên đăng nhập" required><input type="password" name="password" class="form-control mb-3" placeholder="Mật khẩu" required><button class="btn btn-success w-100 py-2 fw-bold">Đăng ký ngay</button><a href="/login" class="btn btn-link w-100 mt-2 text-decoration-none">Đã có tài khoản? Đăng nhập</a></form></div>')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE slides SET title=?, subject=?, grade=?, lesson_number=? WHERE id=?',
         (request.form['title'], request.form['subject'], request.form['grade'], request.form.get('lesson_number',''), id))
        db.commit()
        return redirect('/')
    
    slide = db.execute('SELECT * FROM slides WHERE id = ?', (id,)).fetchone()
    if not slide:
        return "Không tìm thấy bài giảng!"
    return render_template_string(edit_page_html, slide=slide, str=str)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if session.get('logged_in'):
        db = get_db()
        db.execute('DELETE FROM slides WHERE id = ?', (id,))
        db.commit()
    return redirect('/')

@app.route('/release-notes')
def release_notes():
    return render_template_string('''<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><div class="container mt-5"><a href="/" class="btn btn-secondary mb-3">← Quay lại</a><h1>Phiên bản 0.1</ul></div>''')
# --- CÁC TRANG MỚI BẠN YÊU CẦU ---

@app.route('/ideas')
def ideas():
    # Trang Ý tưởng & Chuẩn bị
    return render_template_string(''' 
        <title>Ý tưởng và chuẩn bị</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <div class="container mt-5">
            <a href="/" class="btn btn-secondary mb-3">← Quay lại</a>
            <div class="card p-4 shadow border-0" style="border-radius:20px;">
                <h2 class="text-primary"><i class="fa-solid fa-lightbulb"></i> Ý tưởng & Chuẩn bị</h2>
                <hr>
                <p>Nơi lưu trữ các ý tưởng sơ khai và kế hoạch phát triển ứng dụng CĐTFSVN.</p>
                <ul>
                    <li>Các bạn biết hoặc không biết thì Anh Long (Trong server Discord Cộng đồng TFS Việt Nam của Nhân đây và Hoyunna- hay HoyuFS) đã kick ra khỏi server discord đó chỉ vì ... chưa đủ 16 tuổi =)
                    Mình đã rất tức và rồi nghĩ ra một cái: Tạo thẳng app cho riêng mình!
                    Mặc dù mình hiểu mỗi lứa tuổi khác nhau sẽ không hợp và gây ra xích mích, nhưng thôi, chuyện cũ mình bỏ qua, bây giờ, mình chỉ muốn build một app thật là đẹp, đẹp hơn cái server đó nữa =)
                    Mình cũng đã xin phép Nhân đây và Hoyuuna- HoyuFS lấy ý tưởng rồi nhé ! =) </li>
                </ul>
            </div>
        </div>
    ''')

@app.route('/collection')
def collection():
    # Trang Bộ sưu tập
    return render_template_string('''
                <title>Bộ sưu tập</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <div class="container mt-5">
            <a href="/" class="btn btn-secondary mb-3">← Quay lại</a>
            <h2 class="mb-4">🖼️ Bộ sưu tập dự án</h2>
            <div class="row">
                <div class="col-md-4 mb-3"><div class="card bg-light p-5 text-center"></div></div>
                <div class="col-md-4 mb-3"><div class="card bg-light p-5 text-center"></div></div>
                <div class="col-md-4 mb-3"><div class="card bg-light p-5 text-center"></div></div>
            </div>
        </div>
    ''')

@app.route('/updates')
def updates():
    # Trang Cập nhật kèm Popup Beta
    return render_template_string('''
                <title>Cập nhật</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <div class="container mt-5">
            <a href="/" class="btn btn-secondary mb-3">← Quay lại</a>
            <h1>Lịch sử cập nhật</h1>
            <div class="list-group mt-4">
                <div class="list-group-item">
                    <h5>Phiên bản 1.0 beta 7</h5>
                </div>
            </div>
        </div>

        <div class="modal fade show" id="betaModal" style="display:block; background: rgba(0,0,0,0.5);">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="border-radius:20px; border:none;">
              <div class="modal-header border-0">
                <h5 class="modal-title fw-bold text-primary">🚀 Thông báo Beta</h5>
                <button type="button" class="btn-close" onclick="document.getElementById('betaModal').style.display='none'"></button>
              </div>
              <div class="modal-body">
            Hiện tại rất xin lỗi về việc Ứng dụng CĐTFSVN bị delay liên tục, tin tốt là nó ra mắt trước GTA 6 =)
              </div>
              <div class="modal-footer border-0">
                <button type="button" class="btn btn-primary w-100" style="border-radius:10px;" onclick="document.getElementById('betaModal').style.display='none'">Oke</button>
              </div>
            </div>
          </div>
        </div>
    ''')

# ================= MAIN =================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT, debug=True, use_reloader=False)