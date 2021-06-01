from sqlalchemy import Column, Integer, String, Float, \
    ForeignKey, DateTime, TIMESTAMP
from sqlalchemy.orm import relationship, backref
from database import Base
from sqlalchemy.sql.schema import Table
from datetime import datetime

DELETE_ALL = "all, delete"


class User(Base):
    __tablename__ = "User"

    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)
    login_id = Column(String(36), nullable=True)

    wishlist = relationship("Wishlist", back_populates="user",
                            cascade=DELETE_ALL, passive_deletes=True)
    user_cart = relationship("Cart", back_populates="user",
                             cascade=DELETE_ALL, passive_deletes=True)

    products = relationship('Product', secondary='UserProduct')
    ratings = relationship('Product', secondary='RatingProduct')

    # role is 'basic' or 'admin'
    role = Column(String(6), default="basic")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    @property
    def is_authenticated(self):
        return self.login_id

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.login_id

    def get_role(self):
        return self.role


class Category(Base):
    __tablename__ = 'Category'

    id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False)

    product = relationship("Product", back_populates="category",
                           cascade=DELETE_ALL, passive_deletes=True)


class Product(Base):
    __tablename__ = 'Product'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    rating = Column(Float, nullable=True, default=0)

    category_id = Column(Integer, ForeignKey(
        'Category.id', ondelete="CASCADE"))
    category = relationship("Category", back_populates="product")

    photo = relationship("Photo", back_populates="product",
                         cascade=DELETE_ALL, passive_deletes=True)

    cart = relationship("Cart", back_populates="product",
                        cascade=DELETE_ALL, passive_deletes=True)

    wishlist = relationship("Wishlist", back_populates="product",
                            cascade=DELETE_ALL, passive_deletes=True)

    users = relationship('User', secondary='UserProduct')

    ratings = relationship('User', secondary='RatingProduct')


class Photo(Base):
    __tablename__ = 'Photo'

    id = Column(Integer, primary_key=True)
    address = Column(String(80), nullable=False)

    product_id = Column(Integer, ForeignKey(
        'Product.id', ondelete="CASCADE"))
    product = relationship("Product", back_populates="photo")


class Wishlist(Base):
    __tablename__ = 'Wishlist'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey(
        'Product.id', ondelete="CASCADE"))
    product = relationship("Product", back_populates="wishlist")

    user_id = Column(Integer, ForeignKey(
        'User.id', ondelete="CASCADE"))
    user = relationship("User", back_populates="wishlist")


class Cart(Base):
    __tablename__ = 'Cart'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey('Product.id', ondelete="CASCADE"))
    product_quantity = Column(Integer, default=1)
    product_total = Column(Float, default=0)
    subtotal = Column(Float, default=0)

    user = relationship("User", back_populates="user_cart")
    product = relationship("Product", back_populates="cart")


class Order(Base):
    __tablename__ = 'Order'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE"))
    first_name = Column(String(40), nullable=False)
    last_name = Column(String(40), nullable=False)
    email = Column(String(50), unique=False, nullable=False)
    phone_number = Column(String(10), unique=False, nullable=False)
    country = Column(String(35), unique=False, nullable=False)
    state = Column(String(35), unique=False, nullable=False)
    address1 = Column(String(100), unique=False, nullable=False)
    address2 = Column(String(100), unique=False, nullable=True)
    postal = Column(String(10), unique=False, nullable=False)
    company = Column(String(40), unique=False, nullable=True)
    date = Column(TIMESTAMP, nullable=False)


class UserProduct(Base):
    __tablename__ = 'UserProduct'

    user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
    product_id = Column(Integer, ForeignKey('Product.id'), primary_key=True)
    status = Column(Integer)

    user = relationship(User, backref=backref("products_assoc"))
    product = relationship(Product, backref=backref("users_assoc"))


class PromoCode(Base):
    __tablename__ = "PromoCode"

    id = Column(Integer, primary_key=True)
    discount = Column(Integer, nullable=False)
    code = Column(String(37), nullable=False)

    # p(percent) or a(absolute)
    code_type = Column(String(2), default="p")


class RatingProduct(Base):
    __tablename__ = 'RatingProduct'

    user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
    product_id = Column(Integer, ForeignKey('Product.id'), primary_key=True)
    rating = Column(Integer)

    user = relationship(User, backref=backref("rating_user_assoc"))
    product = relationship(Product, backref=backref("rating_product_assoc"))
    rating_comment = Column(String(120), nullable=True)
    rating_date = Column(DateTime, nullable=False, default=datetime.now())
