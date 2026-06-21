from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from app.core.database import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], pk_name: str = "id"):
        self.model = model
        self.pk_name = pk_name

    def get(self, db: Session, id_val: any) -> Optional[T]:
        return db.query(self.model).filter(getattr(self.model, self.pk_name) == id_val).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj: T) -> T:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: T, obj_in: dict) -> T:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id_val: any) -> Optional[T]:
        db_obj = self.get(db, id_val)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj
