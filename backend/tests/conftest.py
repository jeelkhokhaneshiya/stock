import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.main import app
from app.api.deps import get_db

# Use an in-memory SQLite database for testing to avoid needing a real Postgres DB setup during initial phase validation
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

from app.models.user import User
from app.models.portfolio import Portfolio

@pytest.fixture
def test_user(db_session):
    user = User(id=1, email="testapi@test.com", password_hash="pw", is_active=True)
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_portfolio(db_session, test_user):
    portfolio = Portfolio(id=1, name="Test Portfolio API", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.commit()
    return portfolio

@pytest.fixture
def auth_headers(test_user):
    from app.core.security import create_access_token
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}
