import html

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
        db.execute(
            """CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (listing_id, user_id))"""
        )


def query(sql, params=()):
    with connect_db() as db:
        return db.execute(sql, params).fetchall()


def run(sql, params=()):
    with connect_db() as db:
        return db.execute(sql, params).rowcount


LISTING = """SELECT l.id, l.title, l.description, l.offered, l.wanted,
                    l.created_at, u.name
             FROM listings l LEFT JOIN users u ON l.user_id = u.id"""


def find_listings(user_id, text=""):
    return query(
        LISTING
        + """ WHERE l.status = 'active' AND l.user_id != ?
              AND instr(lower(l.title || ' ' || l.description
                              || ' ' || l.offered || ' ' || l.wanted), lower(?)) > 0
              AND NOT EXISTS (SELECT 1 FROM offers o
                              WHERE o.listing_id = l.id AND o.user_id = ?)
              ORDER BY l.id DESC""",
        (user_id, text, user_id),
    )


def my_listings(user_id):
    return query(LISTING + " WHERE l.user_id = ? AND l.status = 'active' ORDER BY l.id DESC", (user_id,))


def my_offers(user_id):
    return query(
        """SELECT o.id, l.title, o.message, o.status, u.name, u.email
           FROM offers o JOIN listings l ON o.listing_id = l.id
           LEFT JOIN users u ON l.user_id = u.id
           WHERE o.user_id = ? ORDER BY o.id DESC""",
        (user_id,),
    )


def incoming_offers(user_id):
    return query(
        """SELECT o.id, l.title, o.message, o.status, u.name, u.email
           FROM offers o JOIN listings l ON o.listing_id = l.id
           JOIN users u ON o.user_id = u.id
           WHERE l.user_id = ? ORDER BY (o.status = 'pending') DESC, o.id DESC""",
        (user_id,),
    )


# ───────────── BARTER ACTIONS (button callbacks) ─────────────

def propose(listing_id):
    message = st.session_state.get(f"offer_{listing_id}", "").strip()
    if not message:
        st.toast("Describe what you would trade first.", icon="⚠️")
        return
    saved = run(
        """INSERT OR IGNORE INTO offers (listing_id, user_id, message)
           SELECT id, ?, ? FROM listings
           WHERE id = ? AND status = 'active' AND user_id != ?""",
        (st.session_state.user_id, message, listing_id, st.session_state.user_id),
    )
    st.toast("Barter proposed!" if saved else "That listing is no longer available.", icon="🔄")
    st.session_state.card_animation = "from-left"


def skip(listing_id):
    st.session_state.dismissed.add(listing_id)
    st.session_state.card_animation = "from-right"


def withdraw(offer_id):
    run("DELETE FROM offers WHERE id = ? AND user_id = ? AND status = 'pending'",
        (offer_id, st.session_state.user_id))


def respond(offer_id, accept):
    with connect_db() as db:
        row = db.execute(
            """SELECT o.listing_id FROM offers o JOIN listings l ON o.listing_id = l.id
               WHERE o.id = ? AND l.user_id = ? AND o.status = 'pending'
                 AND l.status = 'active'""",
            (offer_id, st.session_state.user_id),
        ).fetchone()
        if not row:
            return
        db.execute("UPDATE offers SET status = ? WHERE id = ?",
                   ("accepted" if accept else "declined", offer_id))
        if accept:
            db.execute("UPDATE listings SET status = 'traded' WHERE id = ?", row)
            db.execute("UPDATE offers SET status = 'declined' WHERE listing_id = ? AND status = 'pending'", row)


def remove_listing(listing_id):
    with connect_db() as db:
        if db.execute("UPDATE listings SET status = 'removed' WHERE id = ? AND user_id = ? AND status = 'active'",
                      (listing_id, st.session_state.user_id)).rowcount:
            db.execute("UPDATE offers SET status = 'declined' WHERE listing_id = ? AND status = 'pending'", (listing_id,))


def logout():
    st.session_state.clear()


# ───────────── UI HELPERS ─────────────

def card(listing, animation=""):
    _, title, desc, offered, wanted, created, owner = (html.escape(str(v or "")) for v in listing)
    st.markdown(
        f"""<div class="listing-card {animation}">
        <h2>{title}</h2><p>{desc}</p>
        <div class="listing-detail"><strong>Offering</strong><br>{offered}</div>
        <div class="listing-detail"><strong>Looking for</strong><br>{wanted}</div>
        <div class="listing-date">Posted by <strong>{owner or "Unknown"}</strong> on {created[:10]}</div>
        </div>""",
        unsafe_allow_html=True,
    )


BADGE = {"pending": "⏳ Pending", "accepted": "✅ Accepted", "declined": "❌ Declined"}

CSS = """<style>
.listing-card{max-width:680px;margin:12px auto 20px;padding:28px;border:1px solid #d9e2ec;
 border-radius:18px;background:white;color:#14213d;box-shadow:0 8px 24px rgba(20,40,60,.10)}
.listing-card h2{margin:8px 0 12px;color:#14213d}.listing-card p{color:#14213d}
.listing-detail{margin-top:14px;padding:12px 14px;border-radius:10px;background:#f4f7fa;color:#14213d;line-height:1.6}
.listing-date{margin-top:16px;color:#667085;font-size:.8rem}.listing-date strong{color:#14213d}
@keyframes inL{from{opacity:0;transform:translateX(-90px) rotate(-3deg)}to{opacity:1;transform:none}}
@keyframes inR{from{opacity:0;transform:translateX(90px) rotate(3deg)}to{opacity:1;transform:none}}
.from-left{animation:inL .35s ease-out}.from-right{animation:inR .35s ease-out}
</style>"""


# ───────────── PAGE ─────────────

st.set_page_config(page_title="BarterHub", page_icon="🔄")
setup_database()

if not st.session_state.get("logged_in"):
    auth_page()
    st.stop()

uid = st.session_state.user_id
st.session_state.setdefault("dismissed", set())
st.session_state.setdefault("card_animation", "")
st.markdown(CSS, unsafe_allow_html=True)

head, out = st.columns([5, 1])
head.title("🔄 BarterHub")
head.write(f"Hi {st.session_state.user_name}! Swap items and services with your community.")
out.write("")
out.write("")
out.button("Logout", on_click=logout)

discover_tab, offers_tab, sell_tab = st.tabs(["🔎 Discover", "🔄 My Offers", "＋ Sell"])

# ── Discover ──
with discover_tab:
    st.subheader("Discover listings")
    text = st.text_input("Search BarterHub", placeholder="Search items, services, or what people want").strip()

    queue = [l for l in find_listings(uid, text) if l[0] not in st.session_state.dismissed]
    if queue:
        current = queue[0]
        card(current, st.session_state.card_animation)
        st.session_state.card_animation = ""
        st.text_input("What will you trade for this?", placeholder=f"e.g. {current[4]}", key=f"offer_{current[0]}")
        a, b = st.columns(2)
        a.button("🔄 Propose barter", key=f"yes_{current[0]}", on_click=propose, args=(current[0],), use_container_width=True)
        b.button("✕ Skip", key=f"no_{current[0]}", on_click=skip, args=(current[0],), use_container_width=True)
        st.caption(f"{len(queue)} listing(s) left to discover.")
    else:
        st.info("You’ve reached the end of these listings. Try another search.")

# ── My Offers (as buyer) ──
with offers_tab:
    st.subheader("Barters you proposed")
    st.caption("No payment is made here. Contact details appear once the owner accepts.")
    mine = my_offers(uid)
    for oid, title, message, status, owner, email in mine:
        with st.container(border=True):
            st.markdown(f"**{title}** — {BADGE[status]}")
            st.write(f"You offered: {message}")
            if status == "accepted":
                st.success(f"Deal! Contact {owner} at {email} to arrange the swap.")
            elif status == "pending":
                st.button("Withdraw", key=f"w_{oid}", on_click=withdraw, args=(oid,))
    if not mine:
        st.info("Barters you propose in Discover will appear here.")

# ── Sell ──
with sell_tab:
    st.subheader("Post a listing")
    with st.form("listing_form", clear_on_submit=True):
        title = st.text_input("Name of item or service", placeholder="e.g. Intro to Python tutoring")
        description = st.text_area("Relevant information", placeholder="Describe the item or service, its condition, or useful details.")
        offered = st.text_input("What are you offering?", placeholder="e.g. Python tutoring")
        wanted = st.text_input("What would you like in exchange?", placeholder="e.g. a statistics textbook")
        submitted = st.form_submit_button("Post listing")

    if submitted:
        values = [v.strip() for v in (title, description, offered, wanted)]
        if all(values):
            t, d, o, w = values
            run("INSERT INTO listings (title, description, offered, wanted, user_id) VALUES (?, ?, ?, ?, ?)",
                (t, d, o, w, uid))
            st.success("Your listing is now available in Discover.")
        else:
            st.error("Fill in the item name, information, offer, and what you want.")

    st.subheader("Requests on your listings")
    requests = incoming_offers(uid)
    for oid, title, message, status, name, email in requests:
        with st.container(border=True):
            st.markdown(f"**{title}** — {BADGE[status]}")
            st.write(f"{name} offers: {message}")
            if status == "pending":
                x, y = st.columns(2)
                x.button("Accept", key=f"a_{oid}", on_click=respond, args=(oid, True), use_container_width=True)
                y.button("Decline", key=f"d_{oid}", on_click=respond, args=(oid, False), use_container_width=True)
            elif status == "accepted":
                st.success(f"Deal! Contact {name} at {email} to arrange the swap.")
    if not requests:
        st.caption("No requests yet.")

    st.subheader("Your active listings")
    active = my_listings(uid)
    for listing in active:
        with st.container(border=True):
            st.markdown(f"**{listing[1]}**  \nOffering {listing[3]} → wants {listing[4]}")
            st.button("Remove", key=f"rm_{listing[0]}", on_click=remove_listing, args=(listing[0],))
    if not active:
        st.caption("You have no active listings.")