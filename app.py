import sqlite3

import streamlit as st

DATABASE = "barterhub.db"


def connect_db():
    return sqlite3.connect(DATABASE)


def setup_database():
    with connect_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                offered TEXT NOT NULL,
                wanted TEXT NOT NULL,
                user_id INTEGER,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )

        # Add these columns if the database was made with the earlier version.
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(listings)")
        }
        future_columns = {
            "user_id": "INTEGER",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }

        for column, definition in future_columns.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE listings ADD COLUMN {column} {definition}"
                )

        # Give existing rows a creation time during this one-time upgrade.
        connection.execute(
            """
            UPDATE listings
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at = ''
            """
        )


def save_listing(title, description, category, offered, wanted):
    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO listings
                (title, description, category, offered, wanted,
                 user_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, 'active', CURRENT_TIMESTAMP)
            """,
            (title, description, category, offered, wanted),
        )


def find_listings(search_text=""):
    pattern = f"%{search_text}%"

    with connect_db() as connection:
        return connection.execute(
            """
            SELECT title, description, category, offered, wanted, created_at
            FROM listings
            WHERE status = 'active'
              AND (
                  title LIKE ?
                  OR description LIKE ?
                  OR category LIKE ?
                  OR offered LIKE ?
                  OR wanted LIKE ?
              )
            ORDER BY id DESC
            """,
            (pattern, pattern, pattern, pattern, pattern),
        ).fetchall()


st.set_page_config(page_title="BarterHub", page_icon="🔄")
setup_database()

st.title("BarterHub")
st.write("Exchange useful items and skills with your community—without money.")

st.subheader("Post a listing")

with st.form("listing_form"):
    title = st.text_input("Listing title", placeholder="e.g. Intro to Python tutoring")
    description = st.text_area(
        "Description",
        placeholder="Describe the item or service and its condition or details.",
    )
    category = st.selectbox(
        "Category",
        ["Books", "Electronics", "Home", "Services", "Other"],
    )
    offered = st.text_input(
        "What are you offering?",
        placeholder="e.g. Python tutoring",
    )
    wanted = st.text_input(
        "What do you want in exchange?",
        placeholder="e.g. a statistics textbook",
    )
    submitted = st.form_submit_button("Post listing")

if submitted:
    if all(value.strip() for value in (title, description, offered, wanted)):
        save_listing(
            title.strip(),
            description.strip(),
            category,
            offered.strip(),
            wanted.strip(),
        )
        st.success("Listing posted.")
    else:
        st.error("Please fill in the title, description, offer, and exchange request.")

st.subheader("Find a listing")
search_text = st.text_input(
    "Search by title, description, category, offer, or want",
    placeholder="Try books, tutoring, or gardening",
)

listings = find_listings(search_text.strip())

if listings:
    for title, description, category, offered, wanted, created_at in listings:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.caption(f"{category} · Posted {created_at}")
            st.write(description)
            st.write(f"**Offering:** {offered}")
            st.write(f"**Looking for:** {wanted}")
else:
    st.info("No listings found. Post one above to get started.")