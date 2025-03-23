from flask import Flask, render_template, redirect, request, url_for, flash, session, jsonify, flash, send_from_directory, send_file
import json
import os
import requests
import tempfile
import zipfile
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import shutil
from io import BytesIO
from datetime import datetime 


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
version = os.getenv('VERSION')

# Set up paths
alias = "vovastl"
HOME_DIR = os.path.expanduser("~")
FILES_PATH = os.path.join(HOME_DIR, "script_files", alias)
DATA_DIR = os.path.join(FILES_PATH, "data")
STL_DIR = os.path.join(FILES_PATH, "stl")
USERS_FILE = os.path.join(DATA_DIR, 'users.json')


# Ensure the directory exists
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STL_DIR, exist_ok=True)

@app.route('/stl_files/<path:filename>')
def stl_files(filename):
    return send_from_directory(STL_DIR, filename)

def is_root_registered():
    return bool(get_root_user())

def load_users():
    if not os.path.exists(USERS_FILE):
        # Create an empty list of users
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)
        return []

    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def add_user(username, password, role):
    users = load_users()
    password_hash = generate_password_hash(password)
    user_entry = {
        "user": username,
        "role": role,
        "password_hash": password_hash
    }
    if role == "user":
        user_entry["upload"] = "true"
    users.append(user_entry)
    save_users(users)

def remove_user(username):
    users = load_users()
    users = [u for u in users if u['user'] != username]
    save_users(users)

def find_user(username):
    users = load_users()
    return next((u for u in users if u['user'] == username), None)

@app.route('/update_user_upload', methods=['POST'])
def update_user_upload():
    if 'user_id' not in session or session['role'] != 'manager':
        return redirect(url_for('login'))

    users = load_users()
    updated = False

    for user in users:
        if user['role'] == 'user':
            key = f"upload_{user['user']}"
            new_value = "true" if key in request.form else "false"
            if user.get("upload") != new_value:
                user["upload"] = new_value
                updated = True

    if updated:
        save_users(users)
        flash("Upload settings updated successfully!", "success")
    else:
        flash("No changes made.", "info")

    return redirect(url_for('manager_dashboard'))


def get_root_user():
    users = load_users()
    return users[0] if users else None

def get_managers():
    users = load_users()
    return [u for u in users if u['role'] == 'manager']


def get_users(manager_username=None):
    users = load_users()
    return [u for u in users if u['role'] == 'user']


def save_root_user(username, password):
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    users = [{"root_user": username, "password_hash": password_hash}, {"users": []}]
    save_users(users)

def save_manager_user(username, password):
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    users = load_users()
    users[1]["users"].append({"manager_username": username, "password_hash": password_hash, "users": []})
    save_users(users)

def save_user(manager_username, username, password):
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    users = load_users()
    for manager in users[1]["users"]:
        if manager['manager_username'] == manager_username:
            manager['users'].append({'user': username, 'password_hash': password_hash})
            break
    save_users(users)

@app.route('/toggle_upload', methods=['POST'])
def toggle_upload():
    if 'user_id' not in session or session['role'] != 'manager':
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json()
    username = data.get('username')
    new_value = data.get('upload')

    if not username or new_value not in ['true', 'false']:
        return jsonify({"status": "invalid input"}), 400

    users = load_users()
    for user in users:
        if user['user'] == username and user['role'] == 'user':
            user['upload'] = new_value
            save_users(users)
            return jsonify({"status": "ok"})

    return jsonify({"status": "not found"}), 404


@app.route('/')
def index():
    if not is_root_registered():
        return redirect(url_for('register', role='root'))
    return redirect(url_for('login'))

@app.route('/remove_user', methods=['POST'])
def remove_user_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    manager_username = session['user_id']
    username = request.form['username']
    remove_user(username)
    flash('User removed successfully!', 'success')
    return redirect(url_for('manager_dashboard'))


@app.before_request
def check_root_user():
    if not is_root_registered():
        if request.endpoint not in ('register', 'static'):
            return redirect(url_for('register', role='root'))

@app.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(request.url)

        existing = find_user(username)
        if existing:
            flash("User already exists", "danger")
            return redirect(request.url)

        add_user(username, password, role)
        flash(f"{role.capitalize()} user registered successfully!", "success")
        return redirect(url_for('login'))

    return render_template('register.html', role=role)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = find_user(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = username
            session['role'] = user['role']

            # Redirect based on role
            if user['role'] == 'root':
                return redirect(url_for('root_dashboard'))
            else:
                return redirect(url_for('main'))

        flash("Invalid username or password", "danger")

    return render_template('login.html', version=version)


@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']
    role = session.get('role', '')

    user_data = find_user(username)
    upload_enabled = user_data.get("upload") == "true" if user_data and role == "user" else True

    try:
        stl_folders = [
            f for f in os.listdir(STL_DIR)
            if os.path.isdir(os.path.join(STL_DIR, f))
        ]
    except FileNotFoundError:
        stl_folders = []

    return render_template(
        'main.html',
        username=username,
        role=role,
        stl_folders=stl_folders,
        upload_enabled=upload_enabled
    )



@app.route('/root_dashboard')
def root_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    managers = get_managers()
    return render_template('root_dashboard.html', managers=managers)

@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    manager_username = session['user_id']
    users = get_users(manager_username)

    subfolder = request.args.get('folder', '')

    stl_folders = list_stl_folders_only(subfolder)
    stl_root_folders = list_stl_root_folders()

    return render_template(
        'manager_dashboard.html',
        users=users,
        username=manager_username,
        role='manager',
        current_folder=subfolder,
        stl_folders=stl_folders,
        stl_root_folders=stl_root_folders
    )


@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']

    try:
        stl_folders = [
            f for f in os.listdir(STL_DIR)
            if os.path.isdir(os.path.join(STL_DIR, f))
        ]
    except FileNotFoundError:
        stl_folders = []

    return render_template('user_dashboard.html', username=username, role='user', stl_folders=stl_folders)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

def list_stl_folders_only(subfolder=""):
    path = os.path.join(STL_DIR, subfolder)
    path = os.path.normpath(path)

    if not path.startswith(STL_DIR):
        return []

    try:
        return [
            {
                "name": item,
                "subpath": os.path.relpath(os.path.join(subfolder, item), start=""),
            }
            for item in os.listdir(path)
            if os.path.isdir(os.path.join(path, item))
        ]
    except FileNotFoundError:
        return []

def list_stl_root_folders():
    try:
        return [
            item for item in os.listdir(STL_DIR)
            if os.path.isdir(os.path.join(STL_DIR, item))
        ]
    except FileNotFoundError:
        return []





@app.route('/upload_stl', methods=['POST'])
def upload_stl():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    selected_folder = request.form.get('folder')
    new_folder = request.form.get('new_folder', '').strip()
    file = request.files.get('file')

    folder = secure_filename(new_folder) if new_folder else selected_folder

    if not file or not folder:
        flash('Please select or enter a folder and choose a file.', 'danger')
        return redirect(url_for('upload_page'))

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.zip'):
        flash('Upload only ZIP files.', 'danger')
        return redirect(url_for('upload_page'))

    upload_path = os.path.join(STL_DIR, folder)
    os.makedirs(upload_path, exist_ok=True)

    zip_path = os.path.join(upload_path, filename)
    extract_folder_name = os.path.splitext(filename)[0]
    extract_path = os.path.join(upload_path, extract_folder_name)

    file.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            os.makedirs(extract_path, exist_ok=True)
            zip_ref.extractall(extract_path)

        # Save .inf file inside the extracted folder
        uploader = session['user_id']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info_path = os.path.join(extract_path, f"{extract_folder_name}.inf")
        with open(info_path, 'w', encoding='utf-8') as f:
            f.write(f"Uploader: {uploader}\n")
            f.write(f"Uploaded: {now}\n")

        os.remove(zip_path)
        flash(f'"{filename}" uploaded and extracted to folder "{folder}/{extract_folder_name}".', 'success')
    except zipfile.BadZipFile:
        os.remove(zip_path)
        flash('Invalid ZIP file. Upload failed.', 'danger')

    return redirect(url_for('main', username=session['user_id'], role=session['role']))

@app.route('/create_stl_folder', methods=['POST'])
def create_stl_folder():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash("Folder name cannot be empty.", "danger")
        return redirect(request.referrer or url_for('main'))

    safe_name = secure_filename(folder_name)
    new_folder_path = os.path.join(STL_DIR, safe_name)

    try:
        os.makedirs(new_folder_path, exist_ok=False)
        flash(f'Folder "{safe_name}" created successfully!', "success")
    except FileExistsError:
        flash(f'Folder "{safe_name}" already exists.', "danger")
    except Exception as e:
        flash(f'Error creating folder: {e}', "danger")

    return redirect(request.referrer or url_for('main'))

@app.route('/folder/<path:folder_name>')
def view_folder(folder_name):
    folder_path = os.path.join(STL_DIR, folder_name)
    folder_path = os.path.normpath(folder_path)

    if not folder_path.startswith(STL_DIR):
        flash("Invalid folder path.", "danger")
        return redirect(url_for('main'))

    folders_with_data = []

    username = session.get('user_id', '')

    try:
        subfolders = [
            f for f in os.listdir(folder_path)
            if os.path.isdir(os.path.join(folder_path, f))
        ]

        for sub in subfolders:
            subfolder_path = os.path.join(folder_path, sub)

            image_url = None
            # Recursively walk the subfolder tree
            for root, dirs, files in os.walk(subfolder_path):
                # First: look specifically for "1.*" image
                image_file = next((
                    f for f in files
                    if os.path.splitext(f)[0] == "1" and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                ), None)

                # Fallback: if no 1.*, look for any image
                if not image_file:
                    image_file = next((
                        f for f in files
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                    ), None)

                if image_file:
                    rel_path = os.path.relpath(os.path.join(root, image_file), STL_DIR)
                    image_url = url_for('stl_files', filename=rel_path)
                    break  # stop after finding the first image

            # Read README.txt in the top-level subfolder only
            readme_path = os.path.join(subfolder_path, "README.txt")
            description = ""
            if os.path.isfile(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f:
                    description = f.read().strip()

            # Read <sub>.inf file inside the subfolder
            inf_path = os.path.join(subfolder_path, f"{sub}.inf")
            upload_info = ""
            can_delete = False
            if os.path.isfile(inf_path):
                with open(inf_path, 'r', encoding='utf-8') as f:
                    upload_info = f.read().strip()
                    # Check if current user is the uploader
                    for line in upload_info.splitlines():
                        if line.startswith("Uploader:"):
                            uploader = line.split(":", 1)[1].strip()
                            if uploader == username:
                                can_delete = True

            folders_with_data.append({
                'name': sub,
                'image': image_url,
                'description': description,
                'upload_info': upload_info,
                'can_delete': can_delete
            })

    except FileNotFoundError:
        folders_with_data = []

    return render_template(
        'folder.html',
        current_folder=folder_name,
        folders=folders_with_data
    )

@app.route('/download_folder/<path:folder_path>')
def download_folder(folder_path):
    abs_path = os.path.normpath(os.path.join(STL_DIR, folder_path))

    if not abs_path.startswith(STL_DIR) or not os.path.isdir(abs_path):
        flash("Invalid folder path.", "danger")
        return redirect(url_for('main'))

    try:
        # Create a temporary directory to store the zip
        temp_dir = tempfile.mkdtemp()
        folder_name = os.path.basename(abs_path)
        zip_base = os.path.join(temp_dir, folder_name)

        # Create the zip file
        zip_path = shutil.make_archive(zip_base, 'zip', abs_path)

        # Send the zip file as download
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{folder_name}.zip",
            mimetype='application/zip'
        )

    except Exception as e:
        flash(f"Error creating zip: {e}", "danger")
        return redirect(url_for('main'))

@app.route('/upload')
def upload_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    stl_root_folders = list_stl_root_folders()

    return render_template(
        'upload.html',
        username=session['user_id'],
        role=session['role'],
        stl_root_folders=stl_root_folders
    )

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    folder = request.form.get('folder')
    subfolder = request.form.get('subfolder')

    full_path = os.path.normpath(os.path.join(STL_DIR, folder, subfolder))
    inf_file = os.path.normpath(os.path.join(STL_DIR, folder, f"{subfolder}.inf"))

    # Confirm the deletion is within the allowed directory
    if not full_path.startswith(os.path.join(STL_DIR, folder)):
        flash("Invalid folder path.", "danger")
        return redirect(url_for('view_folder', folder_name=folder))

    # Check if the user is allowed to delete
    if os.path.exists(inf_file):
        with open(inf_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("Uploader:"):
                    uploader = line.split(":", 1)[1].strip()
                    if uploader != session['user_id']:
                        flash("You can only delete folders you uploaded.", "danger")
                        return redirect(url_for('view_folder', folder_name=folder))
    try:
        shutil.rmtree(full_path)
        if os.path.exists(inf_file):
            os.remove(inf_file)
        flash(f'Folder "{subfolder}" deleted successfully.', "success")
    except Exception as e:
        flash(f"Error deleting folder: {e}", "danger")

    return redirect(url_for('view_folder', folder_name=folder))

@app.route('/show3d/<path:folder>/<subfolder>')


@app.route('/show3d/<path:folder>/<subfolder>')

def show_3d_gallery(folder, subfolder):
    subfolder_path = os.path.normpath(os.path.join(STL_DIR, folder, subfolder))

    if not subfolder_path.startswith(STL_DIR):
        flash("Invalid path.", "danger")
        return redirect(url_for('main'))

    images = []
    stl_files = []

    try:
        for root, dirs, files in os.walk(subfolder_path):
            for f in sorted(files):
                rel_path = os.path.relpath(os.path.join(root, f), STL_DIR)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    images.append(url_for('stl_files', filename=rel_path))
                elif f.lower().endswith('.stl'):
                    stl_files.append(url_for('stl_files', filename=rel_path))
    except Exception as e:
        flash(f"Error loading files: {e}", "danger")

    return render_template("show3d.html", folder=folder, subfolder=subfolder, images=images, stl_files=stl_files)



if __name__ == '__main__':
    app.run(debug=True, threaded=True)
