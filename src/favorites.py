from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import UserPregaoFavorite

def toggle_favorite(user_id: int, pregao_id: int) -> bool:
    """
    Toggles the favorite status needed. 
    Returns True if now favorited, False if unfavorited.
    """
    db: Session = SessionLocal()
    try:
        existing = db.query(UserPregaoFavorite).filter(
            UserPregaoFavorite.user_id == user_id,
            UserPregaoFavorite.pregao_id == pregao_id
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            return False
        else:
            new_fav = UserPregaoFavorite(user_id=user_id, pregao_id=pregao_id)
            db.add(new_fav)
            db.commit()
            return True
    except Exception as e:
        db.rollback()
        print(f"Error toggling favorite: {e}")
        return False
    finally:
        db.close()

def get_user_favorites(user_id: int):
    """
    Returns a list of pregao_ids that are favorited by the user.
    """
    db: Session = SessionLocal()
    try:
        favs = db.query(UserPregaoFavorite.pregao_id).filter(
            UserPregaoFavorite.user_id == user_id
        ).all()
        # Extract ID from tuple
        return [f[0] for f in favs]
    finally:
        db.close()
