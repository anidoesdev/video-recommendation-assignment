# app/models.py

import sqlalchemy
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Table,
    Text,
    Float
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Association Table for the Many-to-Many relationship between Posts and Tags
post_tags = Table('post_tags', Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class User(Base):
    """Represents a user, who can be an owner of a post or a topic."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    name = Column(String) # Full name
    picture_url = Column(String)
    user_type = Column(String, nullable=True)
    has_evm_wallet = Column(Boolean, default=False)
    has_solana_wallet = Column(Boolean, default=False)

    # Relationships
    posts = relationship("Post", back_populates="owner")
    topics = relationship("Topic", back_populates="owner")

    def __repr__(self):
        return f"<User(username='{self.username}')>"

class Category(Base):
    """Represents a category that a post can belong to."""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    count = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)

    # Relationship
    posts = relationship("Post", back_populates="category")
    
    def __repr__(self):
        return f"<Category(name='{self.name}')>"

class Topic(Base):
    """Represents a topic that a post is associated with."""
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    slug = Column(String, unique=True, nullable=False)
    is_public = Column(Boolean, default=True)
    project_code = Column(String, index=True)
    posts_count = Column(Integer, default=0)
    language = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="topics")
    posts = relationship("Post", back_populates="topic")

    def __repr__(self):
        return f"<Topic(name='{self.name}', project_code='{self.project_code}')>"

class Token(Base):
    """Represents a blockchain base token associated with a post."""
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True)
    address = Column(String, unique=True, index=True)
    name = Column(String)
    symbol = Column(String)
    image_url = Column(String, nullable=True)
    
    # Relationship
    posts = relationship("Post", back_populates="base_token")
    
    def __repr__(self):
        return f"<Token(symbol='{self.symbol}', address='{self.address}')>"

class Tag(Base):
    """Represents a single tag that can be applied to many posts."""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # Relationship
    posts = relationship("Post", secondary=post_tags, back_populates="tags")
    
    def __repr__(self):
        return f"<Tag(name='{self.name}')>"

class Post(Base):
    """The central model representing a video post."""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    identifier = Column(String, unique=True, index=True)
    
    # Content URLs
    video_link = Column(String)
    thumbnail_url = Column(String)
    gif_thumbnail_url = Column(String)
    
    # Status fields
    is_available_in_public_feed = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    
    # Counts and Metrics
    comment_count = Column(Integer, default=0)
    upvote_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    exit_count = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0) # Using Float for more precision
    share_count = Column(Integer, default=0)
    bookmark_count = Column(Integer, default=0)
    
    # Blockchain related fields
    contract_address = Column(String, nullable=True)
    chain_id = Column(String, nullable=True)
    chart_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign Keys
    owner_id = Column(Integer, ForeignKey('users.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    topic_id = Column(Integer, ForeignKey('topics.id'))
    base_token_id = Column(Integer, ForeignKey('tokens.id'), nullable=True)
    
    # SQLAlchemy Relationships
    owner = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    topic = relationship("Topic", back_populates="posts")
    base_token = relationship("Token", back_populates="posts")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"