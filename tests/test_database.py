from database import (
    initialize_database,
)


def test_database_initialization():
    initialize_database()

    print(
        "Database initialized successfully."
    )