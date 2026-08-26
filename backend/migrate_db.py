import sqlite3


DB_PATH = "recovery.db"


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    return any(
        column[1] == column_name
        for column in columns
    )


def main():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    if not column_exists(
        cursor,
        "transactions",
        "recovery_outcome"
    ):
        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN recovery_outcome
            TEXT NOT NULL DEFAULT 'PENDING'
            """
        )

        print("Added recovery_outcome")

    else:
        print("recovery_outcome already exists")

    if not column_exists(
        cursor,
        "transactions",
        "recovered_amount"
    ):
        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN recovered_amount
            INTEGER NOT NULL DEFAULT 0
            """
        )

        print("Added recovered_amount")

    else:
        print("recovered_amount already exists")

    connection.commit()
    connection.close()

    print("Database migration complete.")


if __name__ == "__main__":
    main()