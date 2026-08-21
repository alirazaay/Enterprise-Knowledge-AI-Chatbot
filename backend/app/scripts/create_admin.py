"""Create the first administrator interactively.

Run with: python -m app.scripts.create_admin
"""

import getpass

from app.core.database import get_session_factory
from app.services.auth import create_admin_user


def main() -> int:
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        print("Passwords do not match.")
        return 1
    if not name or not email:
        print("Name and email are required.")
        return 1

    session = get_session_factory()()
    try:
        user = create_admin_user(session, name, email, password)
    except ValueError as exc:
        print(str(exc))
        return 1
    finally:
        session.close()

    print(f"Created admin user: {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
