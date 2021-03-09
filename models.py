from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


DELETE_ALL = "all, delete"


class User(Base):
    __tablename__ = "User"

    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)
    login_id = Column(String(36), nullable=True)

    wishlist = relationship("Wishlist", back_populates="user",
                            cascade=DELETE_ALL, passive_deletes=True)
    cart = relationship("Cart", back_populates="user",
                        cascade=DELETE_ALL, passive_deletes=True)

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
    rating = Column(Float, default=0)
    # Counts the times the product was rated
    rated = Column(Integer, default=0)

    category_id = Column(Integer, ForeignKey(
        'Category.id', ondelete="CASCADE"))
    category = relationship("Category", back_populates="product")

    photo = relationship("Photo", back_populates="product",
                         cascade=DELETE_ALL, passive_deletes=True)

    cart = relationship("Cart", back_populates="product",
                        cascade=DELETE_ALL, passive_deletes=True)

    wishlist = relationship("Wishlist", back_populates="product",
                            cascade="all, delete", passive_deletes=True)


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

    user = relationship("User", back_populates="cart")
    product = relationship("Product", back_populates="cart")


class Order(Base):
    __tablename__ = 'Order'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE"))