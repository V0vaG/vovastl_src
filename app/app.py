from flask import Flask, render_template, redirect, request, url_for, flash, session, jsonify, flash, send_from_directory, send_file, Response
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
import random
import math

# Try to import CadQuery for model generation
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
version = os.getenv('VERSION', 'N/A')
branch = os.getenv('BRANCH','N/A')

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

@app.route('/add_stl_file/<folder>/<subfolder>', methods=['POST'])
def add_stl_file(folder, subfolder):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    file = request.files.get('stl_file')
    if not file or not file.filename.lower().endswith('.stl'):
        flash('Only .stl files are allowed.', 'danger')
        return redirect(url_for('item_detail', folder=folder, subfolder=subfolder))

    base_path = os.path.normpath(os.path.join(STL_DIR, folder, subfolder))
    if not base_path.startswith(STL_DIR) or not os.path.isdir(base_path):
        flash("Invalid folder path.", "danger")
        return redirect(url_for('item_detail', folder=folder, subfolder=subfolder))

    try:
        # Ensure files/ folder exists
        files_path = os.path.join(base_path, 'files')
        os.makedirs(files_path, exist_ok=True)

        # Save STL file to files/
        filename = secure_filename(file.filename)
        stl_path = os.path.join(files_path, filename)
        file.save(stl_path)

        # Regenerate ZIP
        zip_output = os.path.join(base_path, f"{subfolder}.zip")
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.zip'):
                        continue  # skip existing zip
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_path)
                    zipf.write(full_path, rel_path)

        flash(f"STL file '{filename}' added and ZIP updated.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for('item_detail', folder=folder, subfolder=subfolder))


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

    return render_template('login.html', version=version, branch=branch)

@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session['user_id']
    role = session.get('role', '')
    user_data = find_user(username)
    upload_enabled = user_data.get("upload") == "true" if user_data and role == "user" else True

    stl_folders = build_folder_cards()
    latest_items = get_latest_uploaded_items()

    return render_template(
        'main.html',
        username=username,
        role=role,
        stl_folders=stl_folders,
        upload_enabled=upload_enabled,
        latest_items=latest_items
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
    subfolder_name_input = request.form.get('subfolder_name', '').strip()
    extract_folder_name = secure_filename(subfolder_name_input) if subfolder_name_input else os.path.splitext(filename)[0]
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

    return redirect(url_for('save_stl', folder=folder, subfolder=extract_folder_name))


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

@app.route('/save_stl/<folder>/<subfolder>', methods=['GET', 'POST'])
def save_stl(folder, subfolder):
    base_path = os.path.join(STL_DIR, folder, subfolder)
    base_path = os.path.normpath(base_path)

    if not base_path.startswith(STL_DIR):
        flash("Invalid path.", "danger")
        return redirect(url_for('main'))

    readme_path = os.path.join(base_path, "README.txt")

    if request.method == 'POST':
        # Save the updated README content
        new_desc = request.form.get('description', '').strip()

        # Handle renaming the subfolder
        new_subfolder = secure_filename(request.form.get('new_subfolder', '').strip())
        if new_subfolder and new_subfolder != subfolder:
            new_path = os.path.join(STL_DIR, folder, new_subfolder)
            try:
                os.rename(base_path, new_path)

                # Rename the .inf file as well
                old_inf_path = os.path.join(new_path, f"{subfolder}.inf")
                new_inf_path = os.path.join(new_path, f"{new_subfolder}.inf")
                if os.path.isfile(old_inf_path):
                    os.rename(old_inf_path, new_inf_path)

                flash(f"Folder renamed to {new_subfolder}.", "success")
                # Update path variables
                base_path = new_path
                subfolder = new_subfolder
                readme_path = os.path.join(base_path, "README.txt")
            except Exception as e:
                flash(f"Failed to rename folder: {e}", "danger")
                return redirect(url_for('save_stl', folder=folder, subfolder=subfolder))

        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_desc)
            flash("Description saved successfully.", "success")
        except Exception as e:
            flash(f"Failed to save description: {e}", "danger")

        return redirect(url_for('item_detail', folder=folder, subfolder=subfolder))

    # Gather all image files in the subfolder
    images = []
    main_image = None
    if os.path.isdir(base_path):
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    rel_path = os.path.relpath(os.path.join(root, file), STL_DIR)
                    img_data = {
                        'filename': file,
                        'url': url_for('stl_files', filename=rel_path)
                    }

                    if os.path.splitext(file)[0] == '1' and main_image is None:
                        main_image = img_data
                    else:
                        images.append(img_data)

    # Load README.txt content if available
    description = ""
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                description = f.read().strip()
        except Exception as e:
            flash(f"Failed to load description: {e}", "warning")

    return render_template(
        'save_stl.html',
        folder=folder,
        subfolder=subfolder,
        description=description,
        images=images,
        main_image=main_image
    )


@app.route('/set_main_image', methods=['POST'])
def set_main_image():
    data = request.json
    folder = data.get('folder')
    subfolder = data.get('subfolder')
    filename = data.get('filename')

    ext = os.path.splitext(filename)[1].lower()
    base_path = os.path.join(STL_DIR, folder, subfolder)

    if not base_path.startswith(STL_DIR):
        return jsonify({'status': 'error', 'message': 'Invalid path'}), 400

    # Recursively search for the image
    image_path = None
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file == filename:
                image_path = os.path.join(root, file)
                break
        if image_path:
            break

    if not image_path or not os.path.isfile(image_path):
        return jsonify({'status': 'error', 'message': 'Image file not found'}), 404

    try:
        # Remove existing "1.*" in base directory
        for file in os.listdir(base_path):
            if os.path.splitext(file)[0] == '1' and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                os.remove(os.path.join(base_path, file))

        # Move the image to base folder as 1.*
        new_main_path = os.path.join(base_path, f'1{ext}')
        shutil.copy(image_path, new_main_path)

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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

@app.route('/item/<folder>/<subfolder>')
def item_detail(folder, subfolder):
    base_path = os.path.join(STL_DIR, folder, subfolder)
    base_path = os.path.normpath(base_path)

    if not base_path.startswith(STL_DIR) or not os.path.exists(base_path):
        flash("Invalid item path.", "danger")
        return redirect(url_for('main'))

    # Gather all image files
    image_urls = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                rel_path = os.path.relpath(os.path.join(root, file), STL_DIR)
                image_urls.append(url_for('stl_files', filename=rel_path))

    readme_path = os.path.join(base_path, "README.txt")
    description = ""
    if os.path.isfile(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            description = f.read().strip()

    inf_path = os.path.join(base_path, f"{subfolder}.inf")
    upload_info = ""
    can_delete = False
    if os.path.isfile(inf_path):
        with open(inf_path, 'r', encoding='utf-8') as f:
            upload_info = f.read().strip()
            for line in upload_info.splitlines():
                if line.startswith("Uploader:"):
                    uploader = line.split(":", 1)[1].strip()
                    if session.get('user_id') == uploader:
                        can_delete = True

    return render_template(
        'item.html',
        folder=folder,
        subfolder=subfolder,
        images=image_urls,
        description=description,
        upload_info=upload_info,
        can_delete=can_delete
    )

@app.route('/cancel_upload/<folder>/<subfolder>', methods=['POST'])
def cancel_upload(folder, subfolder):
    path = os.path.normpath(os.path.join(STL_DIR, folder, subfolder))
    if path.startswith(STL_DIR) and os.path.isdir(path):
        shutil.rmtree(path)
        flash(f"Upload canceled and folder '{subfolder}' deleted.", "info")
    return redirect(url_for('main'))


def build_folder_cards():
    folder_cards = []
    for folder in os.listdir(STL_DIR):
        folder_path = os.path.join(STL_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        images = []
        for subfolder in os.listdir(folder_path):
            subfolder_path = os.path.join(folder_path, subfolder)
            if not os.path.isdir(subfolder_path):
                continue
            for file in os.listdir(subfolder_path):
                if os.path.splitext(file)[0] == "1" and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    rel_path = os.path.relpath(os.path.join(subfolder_path, file), STL_DIR)
                    images.append(url_for('stl_files', filename=rel_path))

        image = random.choice(images) if images else None
        folder_cards.append({"name": folder, "image": image})

    return folder_cards

def get_latest_uploaded_items(limit=10):
    items = []

    for folder in os.listdir(STL_DIR):
        folder_path = os.path.join(STL_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        for subfolder in os.listdir(folder_path):
            subfolder_path = os.path.join(folder_path, subfolder)
            if not os.path.isdir(subfolder_path):
                continue

            inf_path = os.path.join(subfolder_path, f"{subfolder}.inf")
            if os.path.exists(inf_path):
                with open(inf_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    uploader = ""
                    uploaded = ""

                    for line in content.splitlines():
                        if line.startswith("Uploader:"):
                            uploader = line.split(":", 1)[1].strip()
                        elif line.startswith("Uploaded:"):
                            uploaded = line.split(":", 1)[1].strip()

                    try:
                        timestamp = datetime.strptime(uploaded, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue

                    # Find thumbnail image
                    image = None
                    for file in os.listdir(subfolder_path):
                        if os.path.splitext(file)[0] == "1" and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            rel_path = os.path.relpath(os.path.join(subfolder_path, file), STL_DIR)
                            image = url_for('stl_files', filename=rel_path)
                            break

                    items.append({
                        "folder": folder,
                        "subfolder": subfolder,
                        "uploader": uploader,
                        "uploaded": uploaded,
                        "timestamp": timestamp,
                        "image": image
                    })

    # Sort by latest timestamp
    items.sort(key=lambda x: x['timestamp'], reverse=True)
    return items[:limit]

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip().lower()
    results = []

    if query:
        for folder in os.listdir(STL_DIR):
            folder_path = os.path.join(STL_DIR, folder)
            if not os.path.isdir(folder_path):
                continue

            for subfolder in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder)
                if not os.path.isdir(subfolder_path):
                    continue

                readme_path = os.path.join(subfolder_path, "README.txt")
                description = ""
                if os.path.exists(readme_path):
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        description = f.read().strip()

                if query in subfolder.lower() or query in description.lower():
                    thumbnail = None
                    for file in os.listdir(subfolder_path):
                        if os.path.splitext(file)[0] == "1" and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            rel_path = os.path.relpath(os.path.join(subfolder_path, file), STL_DIR)
                            thumbnail = url_for('stl_files', filename=rel_path)
                            break

                    results.append({
                        "folder": folder,
                        "subfolder": subfolder,
                        "description": description,
                        "thumbnail": thumbnail
                    })

    return render_template("search.html", query=query, results=results)

# -----------------------------
# CadQuery modeling functions (if available)
# -----------------------------

def make_simple_hollow_box(inner_len, inner_wid, inner_h, wall=3.0, floor=3.0, corner_fillet=4.0, rim_height=6.0):
    """
    Creates a simple hollow box for preview - no bosses, tongue, or other features
    Just a basic hollow box to show the interior space clearly
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h = floor + inner_h + rim_height  # Include rim height for accurate preview

    # Outer body
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # Hollow out - just basic hollowing
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, inner_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    return body

def make_bottom_box(
    inner_len, inner_wid, inner_h,
    wall=3.0, floor=3.0,
    corner_fillet=4.0,
    rim_height=6.0,
    tongue_height=2.2,
    tongue_clearance=0.2,
    screw_d=3.2,
    screw_csink_d=6.0,
    screw_csink_angle=82,
    boss_outer_d=2.0,  # Much smaller bosses
    boss_h=3.0,        # Much shorter bosses
    boss_core_d=1.0,   # Much smaller pilot holes
    ribs=False,
    rib_thickness=2.0,
    rib_pitch=20.0,
):
    """
    Creates the bottom box with all features
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    outer_len = inner_len + 2 * wall
    outer_wid = inner_wid + 2 * wall
    outer_h   = floor + inner_h + rim_height

    # Outer body
    body = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, outer_h, centered=(True, True, False))
    )
    if corner_fillet > 0:
        body = body.edges("|Z").fillet(corner_fillet)

    # Hollow out - leave floor + walls + upper rim
    cavity_h = inner_h + rim_height
    inner = (
        cq.Workplane("XY")
        .box(inner_len, inner_wid, cavity_h, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = body.cut(inner)

    # Sealing tongue (tongue) - protrudes from rim inward
    # Only add tongue for larger boxes to preserve interior space
    if inner_len > 60 and inner_wid > 40:
        tongue_len = inner_len - 2 * tongue_clearance
        tongue_wid = inner_wid - 2 * tongue_clearance
        tongue = (
            cq.Workplane("XY")
            .box(tongue_len, tongue_wid, tongue_height, centered=(True, True, False))
            .translate((0, 0, floor + inner_h))  # at top of inner cavity
        )
        # Break corners slightly on tongue to prevent friction
        tongue = tongue.edges("|Z").fillet(min(0.6, max(0.0, corner_fillet/4)))
        body = body.union(tongue)

    # Bosses for corners (bottom): four bosses at inner corners, with pilot hole
    # Make bosses smaller and position them better to preserve interior space
    boss_offset_x = inner_len/2 - 8  # Closer to walls but still safe
    boss_offset_y = inner_wid/2 - 8
    boss_centers = [
        (+boss_offset_x, +boss_offset_y),
        (+boss_offset_x, -boss_offset_y),
        (-boss_offset_x, +boss_offset_y),
        (-boss_offset_x, -boss_offset_y),
    ]
    
    # Only add bosses if the box is large enough
    if inner_len > 80 and inner_wid > 60:
        bosses = cq.Workplane("XY")
        for (x, y) in boss_centers:
            bosses = bosses.union(
                cq.Workplane("XY")
                .workplane(offset=floor)
                .center(x, y)
                .cylinder(boss_h, boss_outer_d/2.0)
            )
        body = body.union(bosses)

        # Pilot holes in bosses (for M3 plastic threading or hot insert after drilling)
        for (x, y) in boss_centers:
            pilot_hole = (
                cq.Workplane("XY")
                .workplane(offset=floor)
                .center(x, y)
                .cylinder(boss_h+1, boss_core_d/2.0)
            )
            body = body.cut(pilot_hole)

    # Optional strengthening ribs on floor
    if ribs:
        # Rib grid along X and Y
        # Along X
        y = -inner_wid/2 + rib_pitch
        while y < inner_wid/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(0, y)
                .rect(inner_len - 2*8, rib_thickness)
                .extrude( min(8.0, inner_h/3) )
            )
            body = body.union(rib)
            y += rib_pitch
        # Along Y
        x = -inner_len/2 + rib_pitch
        while x < inner_len/2 - rib_pitch/2:
            rib = (
                cq.Workplane("XY")
                .workplane(offset=floor + 0.01)
                .center(x, 0)
                .rect(rib_thickness, inner_wid - 2*8)
                .extrude( min(8.0, inner_h/3) )
            )
            body = body.union(rib)
            x += rib_pitch

    return body

def make_lid(
    inner_len, inner_wid,
    wall=3.0, lid_thickness=4.0,
    overhang=2.0,            # "rim" that covers the bottom's wall
    corner_fillet=4.0,
    groove_depth=2.4,        # seal groove depth
    groove_clearance=0.25,   # clearance between bottom tongue and lid groove
    screw_d=3.2,             # screw hole in lid (clearance)
    screw_csink_d=6.0,       # countersink diameter
    screw_csink_angle=82,    # countersink angle
):
    """
    Creates the lid with sealing groove and screw holes
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    outer_len = inner_len + 2 * (wall + overhang)
    outer_wid = inner_wid + 2 * (wall + overhang)
    height    = lid_thickness + wall  # including margin for seal groove

    lid = (
        cq.Workplane("XY")
        .box(outer_len, outer_wid, height, centered=(True, True, False))
    )
    if corner_fillet > 0:
        lid = lid.edges("|Z").fillet(corner_fillet)

    # Hollow out to create "cap" - that sits on box walls
    inner_cap_len = inner_len + 2 * wall + 0.3  # small tolerance
    inner_cap_wid = inner_wid + 2 * wall + 0.3
    inner_cap_h   = height - lid_thickness + 0.2

    cavity = (
        cq.Workplane("XY")
        .box(inner_cap_len, inner_cap_wid, inner_cap_h, centered=(True, True, False))
        .translate((0, 0, lid_thickness))  # leave top plate with lid_thickness thickness
    )
    lid = lid.cut(cavity)

    # Seal groove - slightly larger than bottom tongue
    groove_len = inner_len - 2 * groove_clearance
    groove_wid = inner_wid - 2 * groove_clearance
    groove = (
        cq.Workplane("XY")
        .box(groove_len, groove_wid, groove_depth, centered=(True, True, False))
        .translate((0, 0, lid_thickness - groove_depth + 0.2))
    )
    lid = lid.cut(groove)

    # Countersunk screw holes (4 corners)
    # Set positions relative to lid rim
    hole_offset_x = (inner_len/2) + wall - 8
    hole_offset_y = (inner_wid/2) + wall - 8
    hole_centers = [
        (+hole_offset_x, +hole_offset_y),
        (+hole_offset_x, -hole_offset_y),
        (-hole_offset_x, +hole_offset_y),
        (-hole_offset_x, -hole_offset_y),
    ]

    # Holes through entire lid
    for (x, y) in hole_centers:
        lid = (
            lid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .center(x, y)
            .cskHole(screw_d, screw_csink_d, screw_csink_angle, depth=height+1)
        )

    return lid

def export_stl_bytes(solid, tol=0.02, ang=0.2) -> bytes:
    """
    Export CadQuery solid to STL bytes
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")
        
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Export to temporary file
        cq.exporters.export(solid, tmp_path, exportType='STL', tolerance=tol, angularTolerance=ang)
        
        # Read the file content
        with open(tmp_path, 'rb') as f:
            data = f.read()
        
        return data
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.route('/model_generator')
def model_generator():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('model_generator.html', username=session['user_id'], role=session['role'], cadquery_available=CADQUERY_AVAILABLE)

@app.route('/model_generator/preview')
def model_generator_preview():
    """Generate STL for preview (not download) - simplified for better visualization"""
    if not CADQUERY_AVAILABLE:
        return Response("CadQuery not available. Please install cadquery to use the model generator.", status=500)
        
    try:
        # Basic dimensions
        L = float(request.args.get('L', 160))
        W = float(request.args.get('W', 100))
        H = float(request.args.get('H', 60))
        part = request.args.get('part', 'bottom')
        
        # Wall and structure parameters
        wall = float(request.args.get('wall', 3.0))
        floor = float(request.args.get('floor', 3.0))
        corner_fillet = float(request.args.get('corner_fillet', 4.0))
        
        # Sealing parameters
        rim_height = float(request.args.get('rim_height', 6.0))
        tongue_height = float(request.args.get('tongue_height', 2.2))
        tongue_clearance = float(request.args.get('tongue_clearance', 0.2))
        groove_depth = float(request.args.get('groove_depth', 2.4))
        
        # Lid parameters
        lid_thickness = float(request.args.get('lid_thickness', 4.0))
        overhang = float(request.args.get('overhang', 2.0))
        
        # Advanced options
        ribs = request.args.get('ribs') == 'true'
        
        # Validate basic parameters
        if L <= 0 or W <= 0 or H <= 0:
            return Response("Dimensions must be positive", status=400)
        if L > 1000 or W > 1000 or H > 1000:
            return Response("Dimensions too large (max 1000mm)", status=400)
        if part not in ['bottom', 'lid']:
            return Response("Part must be 'bottom' or 'lid'", status=400)
            
    except ValueError as e:
        return Response(f"Invalid parameters: {str(e)}", status=400)
    except Exception as e:
        return Response(f"Parameter error: {str(e)}", status=400)

    try:
        if part == 'bottom':
            # Create simplified preview version - just basic hollow box
            solid = make_simple_hollow_box(L, W, H, wall, floor, corner_fillet, rim_height)
        elif part == 'lid':
            solid = make_lid(
                L, W,
                wall=wall,
                lid_thickness=lid_thickness,
                overhang=overhang,
                corner_fillet=corner_fillet,
                groove_depth=groove_depth,
                groove_clearance=tongue_clearance
            )
        else:
            return Response("Part must be 'bottom' or 'lid'", status=400)

        # Export with lower resolution for faster preview
        data = export_stl_bytes(solid, tol=0.02, ang=0.1)
        return send_file(BytesIO(data), mimetype='application/sla')
        
    except Exception as e:
        return Response(f"STL generation failed: {str(e)}", status=500)

@app.route('/model_generator/generate')
def model_generator_generate():
    """Generate full STL file for download"""
    if not CADQUERY_AVAILABLE:
        return Response("CadQuery not available. Please install cadquery to use the model generator.", status=500)
        
    try:
        # Basic dimensions
        L = float(request.args.get('L', 160))
        W = float(request.args.get('W', 100))
        H = float(request.args.get('H', 60))
        part = request.args.get('part', 'bottom')
        
        # Wall and structure parameters
        wall = float(request.args.get('wall', 3.0))
        floor = float(request.args.get('floor', 3.0))
        corner_fillet = float(request.args.get('corner_fillet', 4.0))
        
        # Sealing parameters
        rim_height = float(request.args.get('rim_height', 6.0))
        tongue_height = float(request.args.get('tongue_height', 2.2))
        tongue_clearance = float(request.args.get('tongue_clearance', 0.2))
        groove_depth = float(request.args.get('groove_depth', 2.4))
        
        # Lid parameters
        lid_thickness = float(request.args.get('lid_thickness', 4.0))
        overhang = float(request.args.get('overhang', 2.0))
        
        # Advanced options
        ribs = request.args.get('ribs') == 'true'
        
        # Validate basic parameters
        if L <= 0 or W <= 0 or H <= 0:
            return Response("Dimensions must be positive", status=400)
        if L > 1000 or W > 1000 or H > 1000:
            return Response("Dimensions too large (max 1000mm)", status=400)
        if part not in ['bottom', 'lid']:
            return Response("Part must be 'bottom' or 'lid'", status=400)
            
    except ValueError as e:
        return Response(f"Invalid parameters: {str(e)}", status=400)
    except Exception as e:
        return Response(f"Parameter error: {str(e)}", status=400)

    try:
        if part == 'bottom':
            solid = make_bottom_box(
                L, W, H,
                wall=wall,
                floor=floor,
                corner_fillet=corner_fillet,
                rim_height=rim_height,
                tongue_height=tongue_height,
                tongue_clearance=tongue_clearance,
                ribs=ribs
            )
        elif part == 'lid':
            solid = make_lid(
                L, W,
                wall=wall,
                lid_thickness=lid_thickness,
                overhang=overhang,
                corner_fillet=corner_fillet,
                groove_depth=groove_depth,
                groove_clearance=tongue_clearance
            )
        else:
            return Response("Part must be 'bottom' or 'lid'", status=400)

        data = export_stl_bytes(solid)
        fname = f"rugged_box_{part}.stl"
        return send_file(BytesIO(data), as_attachment=True, download_name=fname, mimetype='application/sla')
        
    except Exception as e:
        return Response(f"STL generation failed: {str(e)}", status=500)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
