import uuid
import os


from flask import Flask
from flask import render_template, request,\
    redirect, make_response, url_for, jsonify

from functools import wraps


from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db_session, init_db
from login import login_manager
from models import User, Product, Category, Photo, Wishlist, Cart

from datetime import datetime

from config import SECRET_KEY, EMAIL, PASSWORD
from utils import validate_file_type
from flask.json import jsonify
import json

app = Flask(__name__)


app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = './uploads'

login_manager.init_app(app)
init_db()

app.add_url_rule('/uploads/<filename>', 'uploaded_file', build_only=True)
app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
    '/uploads':  app.config['UPLOAD_FOLDER']
})


ADMIN = User.query.filter_by(email=EMAIL, role="admin").first()
if not ADMIN:
    ADMIN = User(email=EMAIL, password=PASSWORD, role="admin")

    db_session.add(ADMIN)
    db_session.commit()

    print("Super admin created")
else:
    print("Super admin already exists")


def admin_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        role = current_user.get_role()
        if role != "admin":
            return login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


@app.teardown_appcontext
def shutdown_context(exception=None):
    db_session.remove()


@app.route('/')
def home():
    return render_template('index.html', products=Product.query.all(),
                           db_session=db_session, Photo=Photo, Product=Product)
    # TODO ask boyko is this ok


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template("register.html")
    else:
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(email=email, password=password)

        db_session.add(user)
        db_session.commit()

        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('login.html')
    else:
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter(User.email == email).first()

        if user and check_password_hash(user.password, password):
            user.login_id = str(uuid.uuid4())
            db_session.commit()
            login_user(user)

            return redirect(url_for('home'))


@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin():
    if request.method == 'GET':
        # Nothing special will happen here
        pass

    elif request.form['Submit'] == 'Category':
        name = request.form['category_name']
        new_category = Category(name=name)

        db_session.add(new_category)
        db_session.commit()
    else:
        name = request.form['product_name']
        description = request.form['product_description']
        category = request.form['product_category']
        price = request.form['product_price']

        category_id = Category.query.filter_by(name=category).first().id

        new_product = Product(name=name, description=description,
                              price=price, category_id=category_id)

        db_session.add(new_product)
        db_session.commit()

        new_product = Product.query.filter_by(
            name=name, description=description,
            price=price, category_id=category_id).first()

        if 'product_pic' in request.files and request.files['product_pic']:
            file = request.files['product_pic']
            filename = secure_filename(file.filename)

            if validate_file_type(filename, ["jpeg", "jpg", "png"]):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                print(new_product.id)

                photo = Photo(
                    address=f'/uploads/{filename}', product_id=new_product.id)

                db_session.add(photo)

        db_session.commit()

    categories = Category.query.all()
    products = Product.query.all()

    return render_template(
        'admin.html', categories=categories, products=products,
        db_session=db_session, Product=Product, Photo=Photo)


@app.route('/admin/register', methods=['GET', 'POST'])
@admin_login_required
def admin_register():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template("admin_register.html")
    else:
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(email=email, password=password, role="admin")

        db_session.add(user)
        db_session.commit()

        return redirect(url_for('admin'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('admin_login.html')
    else:
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, role="admin").first()

        if user and check_password_hash(user.password, password):
            user.login_id = str(uuid.uuid4())
            db_session.commit()
            login_user(user)

            return redirect(url_for('admin'))
        else:
            # Invalid
            pass


@app.route('/admin/product/<int:product_id>')
@admin_login_required
def admin_product_details(product_id):
    product = Product.query.filter_by(id=product_id).first()

    return render_template(
        "admin_product_details.html", product=product,
        db_session=db_session, Product=Product, Photo=Photo)


@app.route('/logout')
@login_required
def logout():
    current_user.login_id = None
    db_session.commit()
    logout_user()

    return redirect(url_for('home'))


@app.route('/cart')
@login_required
def cart():
    return render_template(
        'cart.html', cart=Cart.query.filter_by(
            user_id=current_user.id).all(), db_session=db_session,
        Product=Product, Photo=Photo, Cart=Cart)


@app.route('/_add_to_cart')
@login_required
def _add_to_cart():
    product_id = request.args.get('product_id', type=int)

    cart = Cart(product_id=product_id, user_id=current_user.id)

    db_session.add(cart)
    db_session.commit()

    return jsonify(result="Success")


@app.route('/_remove_from_cart')
@login_required
def _remove_from_cart():
    product_id = request.args.get('product_id', type=int)

    cart = Cart.query.filter_by(
        product_id=product_id, user_id=current_user.id).first()

    db_session.delete(cart)
    db_session.commit()

    return jsonify(result="Deleted")


@app.route('/wishlist')
def wishlist():
    return render_template(
        'wishlist.html', wishlist=Wishlist.query.filter_by(
            user_id=current_user.id).all(), db_session=db_session,
        Product=Product, Photo=Photo, Wishlist=Wishlist)


@app.route('/_add_to_wishlist')
@login_required
def add_to_wishlist():
    product_id = request.args.get('product_id', type=int)
    user_id = current_user.id

    wish = Wishlist(product_id=product_id, user_id=user_id)

    db_session.add(wish)
    db_session.commit()

    return jsonify(result="Success")


@app.route('/_remove_from_wishlist')
@login_required
def _remove_from_wishlist():
    product_id = request.args.get('product_id', type=int)

    wish = Wishlist.query.filter_by(product_id=product_id,
                                    user_id=current_user.id).first()

    db_session.delete(wish)
    db_session.commit()

    return jsonify(result="Deleted")


@ app.route('/shop_grid')
def shop_grid():
    return render_template('shop-grid.html')


@ app.route('/checkout')
def checkout():
    return render_template('checkout.html')


@ app.route('/contact')
def contact():
    return render_template('contact.html')


@ app.route('/blog_single_sidebar')
def blog_single_sidebar():
    return render_template('blog-single-sidebar.html')


@app.route('/_livesearch')
def livesearch():
    text = request.args.get('text', type=str)

    search = f"%{text}%"
    print(search)
    products_by_name = Product.query.filter(Product.name.like(search)).all()
    products_by_desc = Product.query.filter(
        Product.description.like(search)).all()

    result_by_name = {product for product in products_by_name}
    result_by_desc = {product for product in products_by_desc}

    result = result_by_name.union(result_by_desc)

    class JsonProduct:
        def __init__(self, id, name, description, price, rating, rated):
            self.id = id
            self.name = name
            self.description = description
            self.price = price
            self.rating = rating
            self.rated = rated

        def to_json(self):
            return self.__dict__

    result = [JsonProduct(
        r.id, r.name, r.description,
        r.price, r.rating, r.rated).to_json() for r in result]

    print(result)

    return jsonify(result)
