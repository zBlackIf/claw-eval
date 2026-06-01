"""Novel models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class BasicInfo(Base):
    __tablename__ = "basic_infos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    intro = Column(Text, nullable=True)
    content_path = Column(String(512), nullable=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)
    status = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, nullable=False, index=True)
    novel_introduce = Column(Text, nullable=True)
    novel_content = Column(Text, nullable=True)


class RecommendQuestion(Base):
    __tablename__ = "recommend_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, nullable=False, index=True)
    question = Column(String(512), nullable=False)
    answer = Column(Text, nullable=True)
