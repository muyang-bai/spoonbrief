"""t160 recipient policy: authenticated account primary + explicitly added extras.
Historical mismatching primary records are retained in storage, never re-labelled.
Verification evidence is scoped to both this user id AND this exact mailbox.
"""
from types import SimpleNamespace
from app.models.email_address import EmailAddress


def normalize_email(value):
    return (value or '').strip().lower()


def effective_email_rows(user, rows):
    rows = sorted((r for r in rows if r.user_id == user.id), key=lambda r: r.id)
    account = normalize_email(user.email)
    matching = [r for r in rows if normalize_email(r.email) == account]
    proof = next((r for r in matching if r.is_verified), matching[0] if matching else None)
    result = [SimpleNamespace(id=proof.id if proof else 0, user_id=user.id,
              email=user.email.strip(), is_primary=True,
              is_verified=bool(proof and proof.is_verified))]
    grouped = {}
    for row in rows:
        key = normalize_email(row.email)
        if row.is_primary or not key or key == account:
            continue
        if key not in grouped or (row.is_verified and not grouped[key].is_verified):
            grouped[key] = row
    result.extend(SimpleNamespace(id=r.id,user_id=user.id,email=r.email.strip(),
                  is_primary=False,is_verified=bool(r.is_verified)) for r in grouped.values())
    return result


def list_effective_emails(db, user):
    rows = db.query(EmailAddress).filter(EmailAddress.user_id == user.id).all()
    return effective_email_rows(user, rows)


def delivery_emails(db, user):
    return [r.email for r in list_effective_emails(db, user) if r.is_verified]


def verification_target(db, user, email_id):
    # id 0 is a virtual account row; GET never creates or modifies account data.
    if email_id == 0:
        return list_effective_emails(db,user)[0]
    return db.query(EmailAddress).filter(EmailAddress.id == email_id,
                                       EmailAddress.user_id == user.id).first()
