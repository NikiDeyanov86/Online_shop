import uuid
import os

from flask import Flask
from flask import render_template, request, \
    redirect, make_response, url_for, jsonify, session

from functools import wraps

from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db_session, init_db
from login import login_manager
from models import User, Product, Category, Photo, Wishlist, Cart, Order, \
    UserProduct, RatingProduct, PromoCode

import recomendations
from flask_mail import Mail, Message

from datetime import datetime, timedelta

from config import SECRET_KEY, EMAIL, PASSWORD
from utils import validate_file_type, _send_email, \
    _send_email_to_all, _send_targeted_email
from flask.json import jsonify
import json

from pprint import pprint

app = Flask(__name__)

app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = './uploads'
app.permanent_session_lifetime = timedelta(days=1)

login_manager.init_app(app)
init_db()

app.add_url_rule('/uploads/<filename>', 'uploaded_file', build_only=True)
app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
    '/uploads': app.config['UPLOAD_FOLDER']
})

app.config.from_pyfile('email_config.cfg')

mail = Mail(app)


PRODUCT_EMAIL = "email_new_product.html"
PROMO_EMAIL = "email_promocode.html"


ADMIN = User.query.filter_by(email=EMAIL, role="admin").first()
if not ADMIN:
    ADMIN = User(email=EMAIL, password=PASSWORD, role="admin")

    db_session.add(ADMIN)
    db_session.commit()

    print("Super admin created")
else:
    print("Super admin already exists")


def get_rating_product(product_id):
    current_product_all_stars = 0
    current_product_all_people = 0
    rating_percentage = 0
    for row in RatingProduct.query.filter_by(product_id=product_id):
        current_product_all_stars += row.rating
        current_product_all_people += 1

    if current_product_all_stars and current_product_all_people:
        rating_percentage = current_product_all_stars / 5
        rating_percentage = rating_percentage * 100 / current_product_all_people

    return rating_percentage


# def get_cart_subtotal():
#     cart_subtotal = 0
#     for product in Cart.query.filter_by(user_id=current_user.id):
#         cart_subtotal += product.product_total
#     return cart_subtotal


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

    if 'login_id' in current_user.__dict__:
        return render_template('index.html', products=Product.query.all(),
                               cart=Cart.query.filter_by(
                                   user_id=current_user.id).all(),
                               db_session=db_session,
                               Photo=Photo, Product=Product, Cart=Cart, User=User, categories=Category.query.all(),
                               Category=Category, promos=PromoCode.query.all(), PromoCode=PromoCode)

    else:
        return render_template('index.html', products=Product.query.all(),
                               db_session=db_session, Photo=Photo,
                               Product=Product, Cart=Cart, User=User, categories=Category.query.all(), Category=Category, promos=PromoCode.query.all(), PromoCode=PromoCode)


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
            session.permanent = True

            return redirect(url_for('home'))
        else:
            error = 'Invalid credentials'
            return render_template("login.html", error=error)


def _add_category():
    name = request.form['category_name']

    if 'category_pic' in request.files and request.files['category_pic']:
        file = request.files['category_pic']
        filename = secure_filename(file.filename)
        print(filename)

        if validate_file_type(filename, ["jpeg", "jpg", "png"]):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_category = Category(name=name, address=f'/uploads/{filename}')

            db_session.add(new_category)

    db_session.commit()


def _add_product():
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

    return new_product


def _add_promo_code():
    discount = request.form['discount']
    code = request.form['code']
    code_type = request.form['code_type']

    auto_email_promo = 'automatic_email_promo'
    if auto_email_promo in request.form and request.form[auto_email_promo]:
        subject = "Discount"
        message = {'code': code, 'discount': discount,
                   'code_type': "лв." if code_type == 'a' else "%",
                   'hash': generate_password_hash}
        _send_email_to_all(User, mail, Message, jsonify,
                           subject, message, PROMO_EMAIL)

    promo = PromoCode(discount=discount, code=code, code_type=code_type)

    db_session.add(promo)
    db_session.commit()


def _targeted_email(product_id, subject, email_content):
    users = User.query.all()
    products = Product.query.all()

    user_products = {user.id: {product.id: 0 for product in products}
                     for user in users}

    u_products = UserProduct.query.all()

    for p in u_products:
        user_products[p.user_id][p.product_id] = p.status

    pprint(user_products)

    products = recomendations.transform_prefs(user_products)
    r = recomendations.get_recommendations(products, product_id)
    r = [p for p in r if p[0] > 0]
    pprint(r)

    users = [User.query.filter_by(id=rec[1]).first() for rec in r]

    pprint(users)

    try:
        message = {'product': Product.query.filter_by(
            id=product_id).first(), 'hash': hash}
        _send_targeted_email(users, mail, Message, jsonify,
                             subject, message, PRODUCT_EMAIL)
    except Exception:
        print("Email not send")


def _promote_product(product):
    subject = product.name
    message = {'product': product, 'hash': generate_password_hash}
    _send_email_to_all(User, mail, Message, jsonify,
                       subject, message, PRODUCT_EMAIL)


@app.route('/admin', methods=['GET', 'POST'])
@admin_login_required
def admin():
    if request.method == 'GET':
        # Nothing special will happen here
        pass

    elif request.form['Submit'] == 'Category':
        _add_category()
    elif request.form['Submit'] == 'Product':
        product = _add_product()

        if 'automatic_email' in request.form and request.form['automatic_email']:
            _promote_product(product)
    elif request.form['Submit'] == 'PromoCode':
        _add_promo_code()
    elif request.form['Submit'] == 'PromoteCategory':
        category_id = request.form['category_id']

        products = Product.query.filter_by(category_id=category_id).all()
        user_ids = []
        for product in products:
            if product is not None:
                cart = Cart.query.filter_by(product_id=product.id).first()
                if cart is not None:
                    user_ids.append(cart.user_id)
        users = [User.query.filter_by(id=user_id).first() for user_id in user_ids]

        category = Category.query.filter_by(id=category_id).first()
        subject = category.name
        message = {'product': category, 'hash': generate_password_hash}

        _send_targeted_email(users, mail, Message, jsonify, subject, message, PRODUCT_EMAIL)
    else:
        subject = request.form['subject']
        email_content = request.form['email_content']

        if request.form['Submit'] == "toAll":
            _send_email_to_all(
                User, mail, Message, jsonify,
                subject, email_content, render_template)
        elif request.form['Submit'] == "targeted":
            product_id = int(request.form['product_id'])

            _targeted_email(product_id, subject, email_content)
        else:
            _send_email(User, EMAIL, Message, mail,
                        jsonify, subject, email_content)

    categories = Category.query.all()
    products = Product.query.all()
    codes = PromoCode.query.all()

    return render_template(
        'admin.html', categories=categories, products=products, str=str,
        db_session=db_session, Product=Product, Photo=Photo, codes=codes)


@app.route('/admin/delete_product/<int:product_id>', methods=['GET', 'POST'])
@admin_login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id).first()
    
    if request.method == 'POST':
        pass
    else:
        db_session.delete(product)
        db_session.commit()

    return redirect(url_for('admin', categories=Category.query.all(), products=Product.query.all(), str=str,
        db_session=db_session, Product=Product, Photo=Photo, codes=PromoCode.query.all()))


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
            session.permanent = True

            return redirect(url_for('admin'))
        else:
            error = 'Invalid credentials'
            return render_template("admin_login.html", error=error)


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
    session.pop('code', None)

    return redirect(url_for('home'))


@app.route('/_remove_code')
@admin_login_required
def remove_code():
    code_id = request.args.get('code_id', type=int)

    code = PromoCode.query.filter_by(id=code_id).first()

    db_session.delete(code)
    db_session.commit()

    return jsonify(result="Deleted")


@app.route('/cart')
@login_required
def cart():
    return render_template('cart.html',
                           cart=Cart.query.filter_by(
                               user_id=current_user.id).all(),
                           db_session=db_session,
                           Product=Product, Photo=Photo, Cart=Cart, User=User)


@app.route('/_add_to_cart')
@login_required
def _add_to_cart():
    product_id = request.args.get('product_id', type=int)
    cart = Cart.query.filter_by(user_id=current_user.id,
                                product_id=product_id).first()
    if cart:
        cart.product_quantity += 1
    else:
        cart = Cart(product_id=product_id, user_id=current_user.id,
                    product_quantity=1, product_total=0)

    product = Product.query.filter_by(id=product_id).first()
    pprint(cart.__dict__)
    cart.product_total = cart.product_quantity * product.price
    user_product = UserProduct.query.filter_by(
        user=current_user, product=product).first()

    if user_product is None:
        user_product = UserProduct(
            user=current_user, product=product, status=2)
    else:
        user_product.status = 2

    db_session.add(user_product)
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
        Product=Product, Photo=Photo, Wishlist=Wishlist, Cart=Cart,
        cart=Cart.query.filter_by(user_id=current_user.id).all())


@app.route('/_add_to_wishlist')
@login_required
def add_to_wishlist():
    product_id = request.args.get('product_id', type=int)
    user_id = current_user.id

    wish = Wishlist(product_id=product_id, user_id=user_id)
    product = Product.query.filter_by(id=product_id).first()

    if 'login_id' in current_user.__dict__:
        user_product = UserProduct.query.filter_by(
            user=current_user, product=product).first()

        if user_product is None:
            user_product = UserProduct(
                user=current_user, product=product, status=2)
        else:
            user_product.status = 2

        db_session.add(user_product)

        db_session.commit()

    db_session.add(wish)
    db_session.commit()

    return jsonify(result="Success")


@app.route('/_remove_from_wishlist')
@login_required
def _remove_from_wishlist():
    product_id = request.args.get('product_id', type=int)

    wish = Wishlist.query.filter_by(product_id=product_id,
                                    user_id=current_user.id).first()

    product = Product.query.filter_by(id=product_id)

    if 'login_id' in current_user.__dict__:
        user_product = UserProduct.query.filter_by(
            user=current_user, product=product).first()

        user_product.status = 1

        db_session.add(user_product)

        db_session.commit()

    db_session.delete(wish)
    db_session.commit()

    return jsonify(result="Deleted")


@app.route('/shop_grid')
def shop_grid():
    if 'login_id' in current_user.__dict__:
        r = []
        # Get Recomendations
        users = User.query.all()
        products = Product.query.all()

        user_products = {user.id: {product.id: 0 for product in products}
                         for user in users}

        u_products = UserProduct.query.all()

        for p in u_products:
            user_products[p.user_id][p.product_id] = p.status

        pprint(user_products)

        r = recomendations.get_recommendations(user_products, current_user.id)

        pprint(r)
        # TODO rating
        return render_template('shop-grid.html', products=Product.query.all(), categories=Category.query.all(),
                               db_session=db_session, recomendations=r[:5], Photo=Photo, Product=Product,
                               cart=Cart.query.filter_by(
                                   user_id=current_user.id).all(),
                               Cart=Cart, Category=Category, User=User,
                               RatingProduct=RatingProduct)

    else:
        return render_template('shop-grid.html', products=Product.query.all(),
                               db_session=db_session, Photo=Photo,
                               Product=Product, Cart=Cart, User=User, Category=Category,
                               categories=Category.query.all())


@app.route('/shop_list/<int:category_id>')
def shop_list(category_id):
    category = Category.query.filter_by(id=category_id).first()
    products = Product.query.filter_by(category_id=category_id)
    ''''
    r = []
    # Get Recomendations
    users = User.query.all()
    products = Product.query.all()

    user_products = {user.id: {product.id: 0 for product in products}
                        for user in users}

    u_products = UserProduct.query.all()

    for p in u_products:
        user_products[p.user_id][p.product_id] = p.status

    pprint(user_products)

    r = recomendations.get_recommendations(user_products, current_user.id)

    pprint(r)
    '''

    return render_template('shop-list.html', products=products, categories=Category.query.all(),
                           db_session=db_session, Photo=Photo, Product=Product,
                           Cart=Cart, Category=Category, User=User,
                           cart=Cart.query.filter_by(user_id=current_user.id).all())


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'GET':
        return render_template('checkout.html', db_session=db_session, User=User,
                               cart=Cart.query.filter_by(
                                   user_id=current_user.id).all(),
                               orders=Order.query.filter_by(user_id=current_user.id).all(), Order=Order, Cart=Cart,
                               Photo=Photo, Product=Product)
    else:
        if request.form['SubmitAddress'] == "submit-address":
            user_id = current_user.id
            first_name = first_name = request.form.get("name")
            last_name = request.form.get("lastname")
            email = request.form.get("email")
            phone_number = request.form.get("phone_number")
            country = request.form.get("country_name")
            state = request.form.get("state-province")
            address1 = request.form.get("address1")
            address2 = request.form.get("address2")
            postal = request.form.get("postal")
            company = request.form.get("company_name")
            now = datetime.now()
            date = datetime.timestamp(now)
            # now = now + datetime.timedelta(days=5, hours=1)

            order = Order(user_id=user_id, first_name=first_name,
                          last_name=last_name, email=email,
                          phone_number=phone_number,
                          country=country, state=state, address1=address1,
                          address2=address2, postal=postal, company=company, date=now)

            db_session.add(order)
            db_session.commit()

            return redirect(url_for('checkout'))
        else:
            option = request.form['options']

            order = Order.query.filter_by(id=option).first()

            pprint(order)

            return redirect(url_for('checkout'))


@app.route('/order_confirmation', methods=['POST'])
@login_required
def order_confirm():
    order = Order.query.filter_by(id=request.form['options']).first()

    return render_template('order_confirmation.html', order=order,
                           Order=Order, db_session=db_session,
                           cart=Cart.query.filter_by(user_id=current_user.id).all(),
                           Cart=Cart, Photo=Photo, Product=Product)


@app.route('/contact')
def contact():
    return render_template('contact.html', Cart=Cart, cart=Cart.query.filter_by(user_id=current_user.id).all(),
                           db_session=db_session, Photo=Photo, Product=Product)


@app.route('/blog_single_sidebar')
def blog_single_sidebar():
    return render_template('blog-single-sidebar.html', Cart=Cart, cart=Cart.query.filter_by(user_id=current_user.id).all(),
                           db_session=db_session, Photo=Photo, Product=Product)


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


@app.route('/_quantity')
def quantity():
    curr = request.args.get('curr', type=int)
    product_id = request.args.get('product_id', type=int)

    product = Product.query.filter_by(product_id=product_id).first()
    if (product is None):
        return jsonify("error")

    print(curr)
    print(product_id)

    return jsonify(curr)


@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.filter_by(id=product_id).first()

    r = []

    # TODO rating

    if 'login_id' in current_user.__dict__:
        user_product = UserProduct.query.filter_by(
            user=current_user, product=product).first()

        if user_product is None:
            user_product = UserProduct(
                user=current_user, product=product, status=1)
        elif user_product.status < 1:
            user_product.status = 1

        db_session.add(user_product)

        db_session.commit()

        # Get Recomendations
        users = User.query.all()
        products = Product.query.all()

        user_products = {user.id: {product.id: 0 for product in products}
                         for user in users}

        u_products = UserProduct.query.all()

        for p in u_products:
            user_products[p.user_id][p.product_id] = p.status

        pprint(user_products)

        r = recomendations.get_recommendations(user_products, current_user.id)

        pprint(r)

        products = recomendations.transform_prefs(user_products)
        r = recomendations.top_matches(products, product_id)
        r = [p for p in r if p[0] > 0]
        pprint(r)

        # Get Comments
        comments = RatingProduct.query.filter(
            RatingProduct.product_id == product_id,
            RatingProduct.rating_comment != "").all()

        print("Comments")
        pprint([comment.__dict__ for comment in comments])

    return render_template(
        "product_details.html", product=product, recomendations=r[:5],
        db_session=db_session, Product=Product, Photo=Photo,
        Cart=Cart, User=User, comments=comments[:3], cart=Cart.query.filter_by(user_id=current_user.id).all())


@app.route('/product/<int:product_id>/_add_rating', methods=['POST'])
@login_required
def _add_rating(product_id):
    stars = request.form.get("star")
    rating_comment = request.form.get("rating_comment")
    product = Product.query.filter_by(id=product_id).first()
    rating = RatingProduct.query.filter_by(user_id=current_user.id,
                                           product_id=product_id).first()
    if not rating:
        rating = RatingProduct(user_id=current_user.id, product_id=product_id,
                               rating=stars, rating_comment=rating_comment)
    else:
        rating.rating = stars
        rating.rating_comment = rating_comment

    db_session.add(rating)
    db_session.commit()
    product.rating = get_rating_product(product_id)
    db_session.add(product)
    db_session.commit()

    return redirect(url_for('product_details', product_id=product_id))


@app.route('/cart/_apply_promo', methods=['POST'])
@login_required
def _apply_promo():
    user_code = request.form['coupon']
    code = PromoCode.query.filter_by(code=user_code).first()

    if code:
        session['code'] = {
            'code_type': code.code_type,
            'discount': code.discount
        }
    return redirect(url_for("cart",
                            cart=Cart.query.filter_by(
                                user_id=current_user.id).all(),
                            db_session=db_session, Product=Product,
                            Photo=Photo, Cart=Cart, User=User))


@app.route('/unsubscribe/<int:user_id>/<key>', methods=['GET'])
def _unsubscribe(user_id, key):
    if check_password_hash(key, str(user_id)):
        user = User.query.filter_by(id=user_id).first()

        if user and user.subscribed:
            user.subscribed = 0

            db_session.add(user)
            db_session.commit()

            return "Successfully unsubscribed!"
        else:
            return "Invalid link"
