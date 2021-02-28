from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "User"

    id = Column(Integer, primary_key=True)
    #username = Column(String(80), unique=True, nullable=False)
    email = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)
    login_id = Column(String(36), nullable=True)

    # role is 'basic' or 'admin'
    role = Column(String(6), default="basic")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    @property
    def is_authenticated(self):
        return self.login_id != 0

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
