import html
import sqlite3

import streamlit as st

from auth import auth_page, connect_db, setup_auth_database

# ───────────── DATABASE ─────────────

def setup_database():
    setup_auth_database()
    with connect_db() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, description TEXT NOT NULL,
                offered TEXT NOT NULL, wanted TEXT NOT NULL,
                user_id INTEGER, status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
        )

        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(listings)")
        }
        needed_columns = {
            "user_id": "INTEGER",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }

        for column, definition in needed_columns.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE listings ADD COLUMN {column} {definition}"
                )

        connection.execute(
            """
            UPDATE listings
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at = ''
            """
        )


def query(sql, params=()):
    with connect_db() as db:
        return db.execute(sql, params).fetchall()


def find_listings(search_text="", category_filter="All", sort_order="Newest first"):
    pattern = f"%{search_text}%"
    sort_direction = "ASC" if sort_order == "Oldest first" else "DESC"

    with connect_db() as connection:
        return connection.execute(
            f"""
            SELECT id, title, description, category, offered, wanted, created_at
            FROM listings
            WHERE status = 'active'
              AND (? = 'All' OR category = ?)
              AND (
                  title LIKE ?
                  OR description LIKE ?
                  OR category LIKE ?
                  OR offered LIKE ?
                  OR wanted LIKE ?
              )
            ORDER BY id {sort_direction}
            """,
            (
                category_filter,
                category_filter,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
            ),
        ).fetchall()


def show_listing_card(listing, animation=""):
    _, title, description, category, offered, wanted, created_at = listing

    safe_title = html.escape(title)
    safe_description = html.escape(description)
    safe_category = html.escape(category)
    safe_offered = html.escape(offered)
    safe_wanted = html.escape(wanted)
    safe_created_at = html.escape(created_at)

    st.markdown(
        f"""
        <div class="listing-card {animation}">
            <div class="listing-category">{safe_category}</div>
            <h2>{safe_title}</h2>
            <p>{safe_description}</p>
            <div class="listing-detail">
                <strong>Offering</strong><br>{safe_offered}
            </div>
            <div class="listing-detail">
                <strong>Looking for</strong><br>{safe_wanted}
            </div>
            <div class="listing-date">Posted {safe_created_at}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="BarterHub", page_icon="🔄")
setup_database()

st.markdown(
    """
    <style>
    .listing-card {
        max-width: 680px;
        margin: 12px auto 20px auto;
        padding: 28px;
        border: 1px solid #d9e2ec;
        border-radius: 18px;
        background: white;
        box-shadow: 0 8px 24px rgba(20, 40, 60, 0.10);
    }

    .listing-card h2 {
        margin: 8px 0 12px 0;
        color: #14213d;
    }

    .listing-category {
        color: #167d69;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.8rem;
    }

    .listing-detail {
        margin-top: 14px;
        padding: 12px 14px;
        border-radius: 10px;
        background: #f4f7fa;
        line-height: 1.6;
    }

    .listing-date {
        margin-top: 16px;
        color: #667085;
        font-size: 0.8rem;
    }

    @keyframes enterFromLeft {
        from { opacity: 0; transform: translateX(-90px) rotate(-3deg); }
        to   { opacity: 1; transform: translateX(0) rotate(0); }
    }

    @keyframes enterFromRight {
        from { opacity: 0; transform: translateX(90px) rotate(3deg); }
        to   { opacity: 1; transform: translateX(0) rotate(0); }
    }

    .from-left {
        animation: enterFromLeft 0.35s ease-out;
    }

    .from-right {
        animation: enterFromRight 0.35s ease-out;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔄 BarterHub")
st.write("Discover useful things and exchange items or services with your community.")

if "buy_listings" not in st.session_state:
    st.session_state.buy_listings = set()

if "dismissed_listings" not in st.session_state:
    st.session_state.dismissed_listings = set()

if "card_animation" not in st.session_state:
    st.session_state.card_animation = ""

discover_tab, buy_tab, sell_tab = st.tabs(["🔎 Discover", "🛒 Buy", "＋ Sell"])

with discover_tab:
    st.subheader("Discover listings")

    search_text = st.text_input(
        "Search BarterHub",
        placeholder="Search items, services, or what people want",
        key="discover_search",
    )

    filter_col, sort_col = st.columns(2)

    with filter_col:
        category_filter = st.selectbox(
            "Category",
            ["All", "Books", "Electronics", "Home", "Services", "Other"],
        )

    with sort_col:
        sort_order = st.selectbox(
            "Sort by",
            ["Newest first", "Oldest first"],
        )

    listings = find_listings(
        search_text.strip(),
        category_filter,
        sort_order,
    )

    unseen_listings = [
        listing
        for listing in listings
        if listing[0] not in st.session_state.buy_listings
        and listing[0] not in st.session_state.dismissed_listings
    ]

    if unseen_listings:
        current_listing = unseen_listings[0]
        listing_id = current_listing[0]

        show_listing_card(current_listing, st.session_state.card_animation)
        st.session_state.card_animation = ""

        interested_col, skip_col = st.columns(2)

        with interested_col:
            if st.button(
                "🛒 Interested",
                key=f"interested_{listing_id}",
                use_container_width=True,
            ):
                st.session_state.buy_listings.add(listing_id)
                st.session_state.card_animation = "from-left"
                st.rerun()

        with skip_col:
            if st.button(
                "✕ Not interested",
                key=f"skip_{listing_id}",
                use_container_width=True,
            ):
                st.session_state.dismissed_listings.add(listing_id)
                st.session_state.card_animation = "from-right"
                st.rerun()

        st.caption(f"{len(unseen_listings)} listing(s) left to discover.")
    else:
        st.info("You’ve reached the end of these listings. Try another search or category.")

with buy_tab:
    st.subheader("Your interested list")
    st.caption("These are listings you may want to barter for. No payment is made here.")

    all_listings = find_listings()
    interested_listings = [
        listing for listing in all_listings
        if listing[0] in st.session_state.buy_listings
    ]

    if interested_listings:
        for listing in interested_listings:
            listing_id = listing[0]
            show_listing_card(listing)

            if st.button(
                "Remove from list",
                key=f"remove_{listing_id}",
            ):
                st.session_state.buy_listings.remove(listing_id)
                st.rerun()
    else:
        st.info("Listings you mark as Interested will appear here.")

with sell_tab:
    st.subheader("Post a listing")

    with st.form("listing_form", clear_on_submit=True):
        title = st.text_input(
            "Name of item or service",
            placeholder="e.g. Intro to Python tutoring",
        )
        description = st.text_area(
            "Relevant information",
            placeholder="Describe the item or service, its condition, or useful details.",
        )
        category = st.selectbox(
            "Category",
            ["Books", "Electronics", "Home", "Services", "Other"],
            key="sell_category",
        )
        offered = st.text_input(
            "What are you offering?",
            placeholder="e.g. Python tutoring",
        )
        wanted = st.text_input(
            "What would you like in exchange?",
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
            st.success("Your listing is now available in Discover.")
            st.rerun()
        else:
            st.error("Fill in the item name, information, offer, and what you want.")
