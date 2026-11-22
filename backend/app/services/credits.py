"""t158: same existing user counter, atomic reservations and persistent operation keys.
No historical conversion. Reserved operations are held across process failure for review.
"""
from datetime import datetime
import json
from sqlalchemy import Table, Column, Integer, String, DateTime, Text, MetaData, text, select
metadata = MetaData()
events = Table('hb_credit_events', metadata,
    Column('operation_key', String(160), primary_key=True),
    Column('user_id', Integer, nullable=False, index=True),
    Column('amount', Integer, nullable=False),
    Column('state', String(20), nullable=False),
    Column('period_end', DateTime), Column('result_json', Text),
    Column('created_at', DateTime, nullable=False), Column('updated_at', DateTime, nullable=False),
    mysql_engine='InnoDB')
class InsufficientCredits(Exception): pass

def _user_lock(db, uid):
    if db.bind.dialect.name == 'sqlite':
        db.execute(text('UPDATE hb_users SET api_quota_used=api_quota_used WHERE id=:id'), {'id':uid})
        suffix = ''
    else: suffix = ' FOR UPDATE'
    row = db.execute(text('SELECT api_quota_total,api_quota_used,api_quota_reset_at FROM hb_users WHERE id=:id'+suffix), {'id':uid}).mappings().one()
    return dict(row)

def _date(v):
    return datetime.fromisoformat(v) if isinstance(v,str) else v

def reserve(db, uid, key, amount):
    if amount not in (1,2) or not key.startswith(str(uid)+':') or len(key)>160:
        raise ValueError('Invalid credit operation')
    try:
        row = _user_lock(db,uid)
        existing = db.execute(select(events).where(events.c.operation_key==key)).mappings().first()
        if existing:
            if existing['user_id'] != uid or existing['amount'] != amount: raise ValueError('Operation collision')
            db.commit(); return {**dict(existing), "_existing": True}
        now = datetime.utcnow(); end = _date(row['api_quota_reset_at']); used = row['api_quota_used'] or 0
        # Null reset timestamp must NOT erase an existing balance/history.
        if end is None or now >= end:
            if end is not None: used = 0
            end = datetime(now.year+1,1,1) if now.month==12 else datetime(now.year,now.month+1,1)
        if (row['api_quota_total'] or 0)-used < amount: raise InsufficientCredits()
        db.execute(text('UPDATE hb_users SET api_quota_used=:used,api_quota_reset_at=:end WHERE id=:id'), {'used':used+amount,'end':end,'id':uid})
        result = dict(operation_key=key,user_id=uid,amount=amount,state='reserved',period_end=end,result_json=None,created_at=now,updated_at=now)
        db.execute(events.insert().values(**result)); db.commit(); return result
    except Exception:
        db.rollback(); raise

def finish(db, uid, key, success, result=None):
    try:
        row=_user_lock(db,uid)
        op=db.execute(select(events).where(events.c.operation_key==key)).mappings().one()
        if op['user_id'] != uid: raise ValueError('Operation owner mismatch')
        if op['state'] != 'reserved': db.commit(); return op['state']
        # Never refund an old reservation against a new month's counter.
        if not success and _date(op['period_end']) == _date(row['api_quota_reset_at']):
            db.execute(text('UPDATE hb_users SET api_quota_used=CASE WHEN api_quota_used>=:n THEN api_quota_used-:n ELSE 0 END WHERE id=:id'), {'n':op['amount'],'id':uid})
        state='committed' if success else 'released'
        db.execute(events.update().where(events.c.operation_key==key).values(state=state,updated_at=datetime.utcnow(),result_json=json.dumps(result,ensure_ascii=False) if success and result is not None else None))
        db.commit(); return state
    except Exception:
        db.rollback(); raise

def deliver(db, uid, key, send, retry_delay=5):
    """One operation per recipient, including a single transport retry.
    Unexpected interruption keeps its reservation held instead of blind refund/replay.
    """
    try: op = reserve(db, uid, key, 1)
    except InsufficientCredits: return False
    if op['state'] == 'committed': return True
    if op['state'] != 'reserved' or op.get('_existing'): return False
    ok = send()
    if not ok:
        if retry_delay:
            import time
            time.sleep(retry_delay)
        ok = send()
    finish(db, uid, key, bool(ok))
    return bool(ok)

def balance(db, user):
    held = db.execute(text("SELECT COALESCE(SUM(amount),0) FROM hb_credit_events WHERE user_id=:id AND state='reserved' AND period_end=:end"), {'id':user.id,'end':user.api_quota_reset_at}).scalar() or 0
    total=user.api_quota_total or 0; occupied=user.api_quota_used or 0
    return dict(total=total,used=max(0,occupied-held),reserved=int(held),remaining=max(0,total-occupied),reset_at=user.api_quota_reset_at.isoformat() if user.api_quota_reset_at else None,percent=round(occupied/total*100,1) if total else 0)
