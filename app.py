import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from order_book import OrderBook, Trade
from market_maker import MarketMaker
from random_trader import RandomTrader

st.set_page_config(layout="wide")

if "order_book" not in st.session_state:
    st.session_state.order_book = OrderBook()

if "market_participants" not in st.session_state:
    st.session_state.market_participants = [
        MarketMaker(name="MM1"),
        RandomTrader(
            name="AggressiveTrader",
            mean_time_between_trades=3.0,
            market_order_probability=0.4,
            max_order_size=30,
            price_range_bps=30,
        ),
        RandomTrader(
            name="PassiveTrader",
            mean_time_between_trades=8.0,
            market_order_probability=0.2,
            max_order_size=20,
            price_range_bps=15,
        ),
        RandomTrader(
            name="SmallTrader",
            mean_time_between_trades=2.0,
            market_order_probability=0.8,
            max_order_size=10,
            price_range_bps=10,
        ),
    ]


if "last_bot_update" not in st.session_state:
    st.session_state.last_bot_update = time.time()


st.title("Order Book Simulation")
order_book = st.session_state.order_book


placeholder = st.empty()
trades_placeholder = st.empty()

with placeholder.container():
    main_col, trades_col = st.columns([0.8, 0.2])

    with main_col:
        current_time = time.time()
        if current_time - st.session_state.last_bot_update >= 1:
            for participant in st.session_state.market_participants:
                participant.act(st.session_state.order_book)
            st.session_state.last_bot_update = current_time

        st.sidebar.header("Place Order")
        side = st.sidebar.selectbox("Side", ["BUY", "SELL"])
        order_type = st.sidebar.selectbox("Order Type", ["MARKET","LIMIT"])
        price = st.sidebar.number_input(
            "Price", 
            min_value=1, 
            max_value=1000, 
            value=100,
            step=1, 
            disabled=order_type == "MARKET"
        )
        quantity = st.sidebar.number_input("Quantity", min_value=1, max_value=100, step=1)

        if st.sidebar.button("Submit Order"):
            success, order_id = order_book.add_order_api(
                side=side,
                price=price if order_type == "LIMIT" else 0,
                quantity=quantity,
                order_type=order_type,
                participant_name="User",
            )

            if success:
                st.sidebar.success(f"Order Placed! Order ID: {order_id}")
                time.sleep(0.1)
            else:
                st.sidebar.error(
                    "Order rejected - no matching orders available for market order"
                )

        bids, asks = order_book.get_order_book()

        # First show the price chart
        if order_book.trades:
            st.subheader("Price Chart")

            trades_df = pd.DataFrame(
                [(t.timestamp, t.price, t.quantity) for t in order_book.trades],
                columns=["timestamp", "price", "quantity"],
            )
            
            trades_df["formatted_time"] = pd.to_datetime(trades_df["timestamp"], unit='s').dt.strftime('%H:%M:%S')

            fig = make_subplots(
                rows=2,
                cols=1,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.05,
                shared_xaxes=True,
            )

            fig.add_trace(
                go.Scatter(
                    x=trades_df["formatted_time"],  
                    y=trades_df["price"],
                    mode="lines",
                    name="Price",
                    line=dict(color="blue"),
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Bar(
                    x=trades_df["formatted_time"],  
                    y=trades_df["quantity"],
                    name="Volume",
                    marker_color="lightblue",
                ),
                row=2,
                col=1,
            )

            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )

            fig.update_xaxes(title_text="Time", row=2, col=1)
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Order Book")
        book_col1, book_col2 = st.columns(2)

        with book_col1:
            st.write("### Buy Orders")
            bid_df = pd.DataFrame(bids, columns=["Price", "Quantity"])
            st.table(bid_df)

        with book_col2:
            st.write("### Sell Orders")
            ask_df = pd.DataFrame(asks, columns=["Price", "Quantity"])
            st.table(ask_df)

    with trades_col:
        if order_book.trades:
            st.subheader("Recent Trades")
            recent_trades = order_book.trades[-10:][::-1] 
            trade_df = pd.DataFrame(
                [(t.quantity, t.price, "BUY" if t.side == "BUY" else "SELL") for t in recent_trades],
                columns=["Quantity", "Price", "Side"],
            )
            st.table(trade_df)

st.empty()
time.sleep(1)
st.rerun()

