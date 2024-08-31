from sqlmodel import SQLModel, create_engine, Session, select, Field, UniqueConstraint
from sfnx.security import derive_key, encrypt, decrypt
from sqlmodel import SQLModel, Field
from typing import Optional
import os

db_file = "sfnx.db"
db_url = f"sqlite:///{db_file}"

engine = create_engine(db_url, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

class Secrets(SQLModel, table=True):
    service: str = Field(nullable=False, max_length=64, primary_key=True)
    username: Optional[str] = Field(nullable=True, max_length=64, primary_key=True)
    password: bytes = Field(nullable=False, max_length=255)
    salt: bytes = Field(nullable=False)

def configure(master_password: str, verification_secret: str) -> bytes:
    init_db()
    salt = os.urandom(16)
    reference = encrypt(derive_key(master_password, salt), verification_secret)
    configuration = Secrets(
        service="sfnx_secret",
        username=verification_secret,
        password=reference,
        salt=salt
    )
    with Session(engine) as session:
        session.add(configuration)
        session.commit()

def check_exists() -> bool:
    with Session(engine) as session:
        statement = select(Secrets).where(Secrets.service == "sfnx_secret")
        result = session.exec(statement).first()

        return result is not None

def check_db_exists():
    db_path = "sfnx.db"
    
    if os.path.isfile(db_path):
        return True
    else:
        return False

def verify_user_master_password(master_password_attempt: str) -> bool:
    with Session(engine) as session:
        statement = select(Secrets).where(Secrets.service == "sfnx_secret")
        result = session.exec(statement).first()

        if result is None:
            return False
        
        encrypted_secret = getattr(result, "password")
        verification_secret = getattr(result, "username")
        salt = getattr(result, "salt")
        key = derive_key(master_password_attempt, salt)
        try:
            decrypted_secret = decrypt(key, encrypted_secret)
        except ValueError:
            print("Wrong master password.")
            return False

        return decrypted_secret == verification_secret

def get_user_name(master_password_attempt: str) -> str:
    with Session(engine) as session:
        if check_exists():
            statement = select(Secrets).where(Secrets.service == "sfnx_secret")
            result = session.exec(statement).first()
            
            verification_secret = getattr(result, "username")
            encrypted_secret = getattr(result, "password")
            salt = getattr(result, "salt")
            key = derive_key(master_password_attempt, salt)

            try:
                decrypted_secret = decrypt(key, encrypted_secret)
            except ValueError:
                return ""
            
            if decrypted_secret == verification_secret:
                return decrypted_secret
            else:
                return ""

def add_password(master_password_attempt: str, service: str, username: Optional[str], password: str):
    if verify_user_master_password(master_password_attempt) and not service == "sfnx_secret":
        with Session(engine) as session:
            salt = os.urandom(16)
            key = derive_key(master_password_attempt, salt)
            s_password = encrypt(key, password)
            secret = Secrets(
                service=service,
                username=username,
                password=s_password,
                salt=salt
            )
            session.add(secret)
            session.commit()

def delete_password(master_password_attempt: str, service: str, username: str):
    if verify_user_master_password(master_password_attempt):
        with Session(engine) as session:
            statement = select(Secrets).where(Secrets.service == service).where(Secrets.username == username)
            result = session.exec(statement).first()
            if result:
                session.delete(result)
                session.commit()

def retrieve_password(master_password_attempt: str, service: str):
    if verify_user_master_password(master_password_attempt):
        with Session(engine) as session:
            statement = select(Secrets).where(Secrets.service == service).where(Secrets.username == username)
            results = session.exec(statement).all()

            if results:
                for result in results:
                    username = result.username
                    key = derive_key(master_password_attempt, result.salt)
                    try: 
                        password = decrypt(key, result.password)
                    except ValueError:
                        password = None

                    print(f"Username: {username}, Password: {decrypted_password}")
            else:
                print("No records found for this service.")