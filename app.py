from flask import Flask, request, session, render_template, redirect, url_for
from flask_socketio import SocketIO, Namespace, join_room, leave_room, disconnect, emit
from functools import wraps
from dotenv import load_dotenv
from urllib.parse import parse_qs
from scipy.optimize import linprog
from model import *

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret_key"
socketio = SocketIO(app, cors_allowed_origins='*', manage_session=False)

room_manager = RoomManager()

def linprog_to_graph(in_data, in_linprog, demand, marketPrice):
    cur_width = 0
    xList = []
    widthBar = []
    barHeight = []
    colors = []
    players = []
    costs = []
    assets = []
    rand_color = get_random_rgba()
    for index, p in enumerate(in_data):
        if in_linprog[index] > 0 and in_linprog[index] < p["quantity"]:
            # Line intersects bar
            assets.append(p["asset"])
            barHeight.append(p["price"])
            xList.append(in_linprog[index] / 2 + cur_width)
            widthBar.append(in_linprog[index])
            # colors.append(f'rgba({rand_color[0]}, {rand_color[1]}, {rand_color[2]}, 1)')
            colors.append(f'rgba({p["color"][0]}, {p["color"][1]}, {p["color"][2]}, 1)')
            players.append(p["player"])
            costs.append(p["generation"])
            cur_width += in_linprog[index]
            assets.append(p["asset"])
            barHeight.append(p["price"])
            xList.append(((p["quantity"] - in_linprog[index]) / 2 + cur_width))
            widthBar.append(p["quantity"] - in_linprog[index])
            # colors.append(f'rgba({rand_color[0]}, {rand_color[1]}, {rand_color[2]}, 0.25)')
            colors.append(f'rgba({p["color"][0]}, {p["color"][1]}, {p["color"][2]}, 0.25)')
            players.append(p["player"])
            costs.append(p["generation"])
            cur_width += p["quantity"] - in_linprog[index]
        else:
            assets.append(p["asset"])
            barHeight.append(p["price"])
            xList.append(p["quantity"] / 2 + cur_width)
            widthBar.append(p["quantity"])
            players.append(p["player"])
            costs.append(p["generation"])
            cur_width += p["quantity"]
            if in_linprog[index] == 0:
                # colors.append(f'rgba({rand_color[0]}, {rand_color[1]}, {rand_color[2]}, 0.25)')
                colors.append(f'rgba({p["color"][0]}, {p["color"][1]}, {p["color"][2]}, 0.25)')
            else:
                # colors.append(f'rgba({rand_color[0]}, {rand_color[1]}, {rand_color[2]}, 1)')
                colors.append(f'rgba({p["color"][0]}, {p["color"][1]}, {p["color"][2]}, 1)')
    return  {
                "barHeight": barHeight,
                "xList": xList,
                "widthBar": widthBar,
                "colors": colors,
                "demand": demand,
                "marketPrice": marketPrice,
                "players": players,
                "costs": costs,
                "assets": assets
            }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        room = session.get("room")
        name = session.get("name")
        
        current_room = room_manager.get_room(room)
        if room is None or name is None or current_room is None:  # Check if user is in session
            if request.endpoint != "index":
                print("Redirect to index")
                return redirect(url_for("index"))  # Redirect to login if not logged in
            
        elif not current_room.get_room_status(): # Check if game is still in lobby
            if request.endpoint != "lobby":
                print("Redirect to lobby")
                return redirect(url_for("lobby"))
            
        elif current_room.get_room_status():
            if request.endpoint != "game":
                print("Redirect to game")
                return redirect(url_for("game"))
    
        return f(*args, **kwargs)  # Otherwise, proceed to the game
    return decorated_function

@app.route("/logout")
def logout():
    session.pop("name", None)  
    return redirect(url_for("index"))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        action = request.form.get('action')

        if not username or username.strip() == "":
            context = { "err": True, "msg": "Enter a valid username" }
            return render_template('index.html', ctx=context)
        if action == "Create Room":
            room_code = room_manager.create_room(username)
            session["room"] = room_code
            session["name"] = username

            print("Create Room")
            return redirect(url_for('lobby'))
        elif action == "Join Room":
            code = request.form.get('join-code')
            joining_room = room_manager.get_room(code)

            if joining_room is not None and joining_room.get_room_status():
                context = { "err": True, "msg": "Game Started" }
                return render_template('index.html', ctx=context)
            
            if joining_room is not None:
                player_usernames = [player.username for player in room_manager.get_username_from_players_room(code)]
                admin_username = room_manager.get_room(code).admin.username
                if username in player_usernames or username == admin_username: # Ensure usernames are unique
                    context = { "err": True, "msg": "Enter an Unused Username" }
                    return render_template('index.html', ctx=context)
                else:
                    session["room"] = code
                    session["name"] = username

                return redirect(url_for('lobby'))
            else: 
                context = { "err": True, "msg": "Room does not exist" }
                return render_template('index.html', ctx=context)
    context = { "err": False, "msg": "" }
    return render_template('index.html', ctx=context)

@app.route('/lobby', methods=['GET', 'POST'])
@login_required
def lobby():
    room = session.get("room")
    name = session.get("name")
    
    if request.method == "POST":
        action = request.form.get('action')

        if action == 'leave': 
            return redirect(url_for('logout'))
    
    lobby_room = room_manager.get_room(room)

    context = { "room": room, "is_admin": name == lobby_room.get_admin(), "admin": lobby_room.get_admin() }

    return render_template('lobby.html', ctx=context)

@app.route('/game', methods=['GET', 'POST'])
@login_required
def game():
    room = session.get("room")
    name = session.get("name")
    game_room = room_manager.get_room(room)

    if game_room is None:
        return redirect(url_for("index"))
    
    context={ "room": game_room.get_json_room(), "is_admin": name == game_room.get_admin() }
    return render_template('game.html', ctx=context)

class LobbyNamespace(Namespace):
    def on_connect(self):
        room = session.get("room")
        name = session.get("name")
        print(f"{name} joined room {room}")
        lobby_room = room_manager.get_room(room)

        if lobby_room is not None and name:
            print(f"User {name} joined room {room}")
            join_room(room)

            if lobby_room.get_admin() != name:
                lobby_room.add_player(name)

            socketio.emit("user_change", lobby_room.get_json_room(), namespace='/lobby', to=room)
        else:
            socketio.emit("player_left", {'msg': "gone"}, namespace='/lobby', to=request.sid)

    def on_disconnect(self, reason):
        room = session.get("room")
        name = session.get("name")
        lobby_room = room_manager.get_room(room)

        print(f"User {name} left room {room}")
        leave_room(room)

        if lobby_room is None or lobby_room.get_room_status():
            return
        
        if lobby_room.get_admin() == name:
            print(f"Delete room {room}")
            socketio.emit("player_left", {'msg': "gone"}, namespace='/lobby', to=room)
            room_manager.delete_room(room)
            return

        lobby_room.remove_player(name)

        socketio.emit("user_change", lobby_room.get_json_room(), namespace='/lobby', to=room)

    def on_start_game(self, data):
        room = session.get("room")
        lobby_room = room_manager.get_room(room)
        
        lobby_room.create_players_data()
        lobby_room.set_room_status(True)
        
        socketio.emit('game_start', {'message': 'Game is starting!'}, namespace='/lobby', to=room)

class GameNamespace(Namespace):
    def on_connect(self):
        room = session.get("room")
        name = session.get("name")
        sid = request.sid

        join_room(room)
        game_room = room_manager.get_room(room)

        if game_room is not None:
            print(f"User {name} SID updated: {sid}")
            game_room.set_sid_from_players(name, sid)
        else:
            disconnect()

    def on_disconnect(self, reason):
        room = session.get("room")
        leave_room(room)
        print("Game Disconnect")
    
    def on_get_stats(self):
        room = session.get("room")
        name = session.get("name")
        game_room = room_manager.get_room(room)

        if game_room.get_admin() == name:
            return
        
        data = game_room.get_player_data(name)
        player_sid = game_room.get_sid_from_players(name)

        data["currentRound"] = game_room.get_current_round()
        
        socketio.emit('send_stats', data, namespace='/game', to=player_sid)
        print(f"Sent Stats {data} to {name}")

    def on_start_next_round(self):
        print("Start Next Round event received")
        room = session.get("room")
        game_room = room_manager.get_room(room)
        players = game_room.get_json_room()["players"]
        for p in players:
            name = p["username"]
            if not game_room.get_player_bid_status(name): # havent bid yet
                    game_room.get_player_data_object(name).set_bid_status(True)
                    game_room.get_player_data_object(name).get_player_single_bid().set_price_quantity(0.0, 0.0)
                    socketio.emit('bid_status', {'message': 'Bid successful!'}, namespace='/game', to=game_room.get_sid_from_players(name))

                    marketUnits = 0
                    allBid = game_room.has_all_players_bid()
                    if allBid:
                        marketUnits = game_room.get_total_bid_units()

                    # Get list of asset names and the bid prices
                    all_bids = game_room.get_json_all_bids()
                    asset_names = []
                    bid_prices = []
                    for bid in all_bids:
                        asset_names.append(bid["asset"])
                        bid_prices.append(bid["price"])

                    print(f"Submit Bid id: {game_room.get_player_data_object(name).get_id()}")
                    data = {
                        "allBid": allBid,
                        "name": name,
                        "player_id": game_room.get_player_data_object(name).get_id(),
                        "marketUnits": marketUnits,
                        "assetNames": asset_names,
                        "bidPrices": bid_prices
                    }
                    print(f"Send data to room: {data}")
                    socketio.emit('all_bids_status', data, namespace='/game', to=room)
            
                    print(f"{name} submit data: 0 quantity and price")


    def on_submit_bid(self, data):
        print("Submit Bid")
        room = session.get("room")
        name = session.get("name")
        game_room = room_manager.get_room(room)

        if game_room is None:
            disconnect()

        parsed_data = parse_qs(data.get('data', ''))
        parsed_data_clean = {}

        for key, values in parsed_data.items():
            try:
                # Try converting the value to an int
                parsed_data_clean[key] = int(values[0])
            except ValueError:
                try:
                    # If that fails, try converting the value to a float
                    parsed_data_clean[key] = float(values[0])
                except ValueError:
                    # If both conversions fail, keep it as original type
                    parsed_data_clean[key] = values[0]
        
        # Have They Already Placed a Bid
        if game_room.get_player_bid_status(name):
            socketio.emit('bid_status', {'message': 'Already placed bid. Wait till next round!'}, namespace='/game', to=game_room.get_sid_from_players(name))
            return

        if 'default_quantity' in parsed_data_clean:
            player_bid = game_room.get_player_data_object(name).get_player_single_bid()
            player_bid.set_price_quantity(player_bid.get_generation(), player_bid.get_units())
        else:
            # Error Check data
            if 'quantity' not in parsed_data:
                socketio.emit('bid_status', {'message': f'Enter a Quantity!'}, namespace='/game', to=game_room.get_sid_from_players(name))
                return
        
            if 'price' not in parsed_data:
                socketio.emit('bid_status', {'message': f'Enter a Price!'}, namespace='/game', to=game_room.get_sid_from_players(name))
                return

            # Check price is valid and dosen't exceed market price
            if (parsed_data_clean["price"] < 0 or parsed_data_clean["price"] > market_cap):
                socketio.emit('bid_status', {'message': 'Enter a different price (ensure it is non-negative number below the market cap)'}, namespace='/game', to=game_room.get_sid_from_players(name))
                return
            
            player_quantity = game_room.get_player_data_object(name).get_all_player_units()
            if (parsed_data_clean["quantity"] < 0 or parsed_data_clean["quantity"] > player_quantity):
                socketio.emit('bid_status', {'message': f'Enter a different quantity (ensure it is non-negative number below the number of units you have ({player_quantity})'}, namespace='/game', to=game_room.get_sid_from_players(name))
                return
            
            game_room.get_player_data_object(name).get_player_single_bid().set_price_quantity(float(parsed_data_clean["price"]), float(parsed_data_clean["quantity"]))
        
        game_room.get_player_data_object(name).set_bid_status(True)
        
        socketio.emit('bid_status', {'message': 'Bid successful!'}, namespace='/game', to=game_room.get_sid_from_players(name))

        marketUnits = 0
        allBid = game_room.has_all_players_bid()
        if allBid:
            marketUnits = game_room.get_total_bid_units()

        # Get list of asset names and the bid prices
        all_bids = game_room.get_json_all_bids()
        asset_names = []
        bid_prices = []
        for bid in all_bids:
            asset_names.append(bid["asset"])
            bid_prices.append(bid["price"])

        print(f"Submit Bid id: {game_room.get_player_data_object(name).get_id()}")
        data = {
            "allBid": allBid,
            "name": name,
            "player_id": game_room.get_player_data_object(name).get_id(),
            "marketUnits": marketUnits,
            "assetNames": asset_names,
            "bidPrices": bid_prices
        }
        print(f"Send data to room: {data}")
        socketio.emit('all_bids_status', data, namespace='/game', to=room)
 
        print(f"{name} submit data: {parsed_data_clean}")

    def on_run_round(self, data):
        print("Run Round")
        room = session.get("room")
        name = session.get("name")
        game_room = room_manager.get_room(room)

        if game_room.get_admin() != name:
            return

        # Check if everyone has voted
        if not game_room.has_all_players_bid():
            socketio.emit('bid_status', {'message': f'Not everyone has voted!'}, namespace='/game', to=game_room.get_admin_sid())
            return
        
        parsed_data = parse_qs(data.get('data', ''))
        parsed_data_clean = {}

        multi_value_keys = {"assets", "bids"}

        for key, values in parsed_data.items():
            if key in multi_value_keys:
                if key == "bids":
                    # Convert to list of ints
                    parsed_data_clean[key] = [float(v) for v in values]
                else:
                    parsed_data_clean[key] = values  # always a list
            else:
                # single value, try conversions
                val = values[0]
                try:
                    parsed_data_clean[key] = int(val)
                except ValueError:
                    try:
                        parsed_data_clean[key] = float(val)
                    except ValueError:
                        parsed_data_clean[key] = val

        event = parsed_data_clean["event"]

        all_bids = game_room.get_json_all_bids()
        sorted_bids = sorted(all_bids, key=lambda x: (x["price"], x["asset"]))

        prices = []
        quantities = []
        for bid in sorted_bids:
            prices.append(bid["price"])
            quantities.append(bid["quantity"])
        demand = parsed_data_clean["slider"]

        c = prices #prices
        u = quantities #quantities of each good
        b_eq = [demand, 0]

        #l = [0]*len(c)
        A_eq = [[1]*len(c), [0]*len(c)]
        bounds = []
        for upper_bound in u:
            bounds.append((0, upper_bound))

        #define the quantities cleared and market price  USING MAGIC
        if sum(u) >= demand:
            res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
            print(f"The marginal returned from LinProg: {res.eqlin['marginals']}")
            print(f"The vector x returned from LinProg{res.x}\n\n")
            market_price = res.eqlin["marginals"][0]
            x = res.x
        else:
            market_price = max(c)
            x = u

        graphData = linprog_to_graph(sorted_bids, x, demand, market_price)
        # TODO REDEFINE so that the bids are taken out at the lowest level (directly from the stuff passed back from the front end) Then put back more print statments
        player_profits = []
        player_gains = []
        for index, bid in enumerate(sorted_bids):
            gain = (market_price - bid["generation"]) * x[index]
            player_profit = (market_price - bid["generation"]) * x[index]
            player_gains.append({"player": bid["player"], "gain": gain})
            player_profits.append({"player": bid["player"], "id": bid["id"], "total": bid["data"].get_profit() + player_profit})

        sorted_player_profits = sorted(player_profits, key=lambda x: x["total"], reverse=True)
        sorted_player_gains_before_event = sorted(player_gains, key=lambda x: x["gain"], reverse=True)

        # sorted_player_gains_post_event
        data_before_event =  {
                    "graphData": graphData,
                    "playerProfits": sorted_player_profits,
                    "playerGainsBeforeEvent": sorted_player_gains_before_event,
                    "roundNumber": game_room.get_current_round() + 1
                }
        
        print(f"the marketUnits: {parsed_data_clean['marketUnits']}")

        # get list of assets and bids selected
        selected_assets = parsed_data_clean.get('assets', [])
        selected_bids = parsed_data_clean.get('bids', [])
        print(f"selected bids: {selected_bids}")

        data_after_event = self.rand_event(sorted_bids, demand, event, parsed_data_clean["marketUnits"], market_price, min(prices), selected_assets, selected_bids)
        
        data = data_before_event | data_after_event

        
        socketio.emit('round_over', data, namespace='/game', to=room)
  

        game_room.set_all_players_bid_status(False)
        game_room.increment_round()

    def rand_event(self, sorted_bids, demand, event, marketUnits, market_price_old, min_price, selected_assets, selected_bids):
        #THIS IS WHERE THE EVENT HAPPENS
        if event == "none":
            event_name = "None"
            # data =  {
            #     "graphDataAfterEvent": None,
            #     "playerProfitsAfterEvent": None,
            #     "playerGainsAfterEvent": None,
            # } 
            print("No extra Events")
            # return data
        
        elif event == "high_dem":
            event_name = "Higher Demand"
            try:
                demand = random.randint(demand, int(min(demand+marketUnits*1/3, marketUnits*9/10)))
            except:
                demand = marketUnits

        elif event == "low_dem":
            event_name = "Lower Demand"
            try:
                demand = random.randint(int(max(demand-marketUnits*1/3, marketUnits*1/10)), demand)
            except:
                demand = 0

        elif event == "high_bidder_remove":
            event_name = "Remove Highest Cleared Bidder"
            for bid in sorted_bids:
                if bid['price'] == market_price_old:
                    bid['price'] = 0
                    bid['quantity'] = 0
                    break

        elif event == "low_bidder_remove":
            event_name = "Remove Lowest Cleared Bidder"
            # remove the quantity of the minimum price
            for bid in sorted_bids:
                if bid['price'] == min_price:
                    bid['price'] = 0
                    bid['quantity'] = 0
                    break

        elif event == "tax_coal&nat_gas":
            event_name = "Tax on Coal and Natural Gas"
            coal_natGas = ["Coal", "Natural Gas (Open Cycle)", "Coal-to-Liquid",
                       "Natural Gas (Combined Cycle)","Shale Oil Power Generation"]
            for bid in sorted_bids:
                if bid["asset"] in coal_natGas:
                    bid["generation"] = bid["generation"]+20 # add $20 tax

        elif event == "remove_renewable":
            event_name = "Remove Renewable Generators"
            renewables = [
                "Wind (onshore)", "Wind (Offshore)", "Solar Photovoltaic", "Concentrated Solar Power",
                "Large-Scale Hydropower", "Geothermal", "Biomass (Wood)", "Biomass (Agricultural Waste)",
                "Biogas (Landfills)", "Tidal Power", "Wave Power", "Concentrated Solar Thermal", "Algae Biofuel",
                "Organic Photovoltaic", "Microgrids (Renewable)", "Ocean Thermal Energy Conversion"
            ]
            for bid in sorted_bids:
                if bid["asset"] in renewables:
                    bid['price'] = 0
                    bid['quantity'] = 0

        elif event == "remove_by_asset_name":
            event_name = "Removed Some Bidders by Asset Name"
            for bid in sorted_bids:
                if bid["asset"] in selected_assets:
                    bid['price'] = 0
                    bid['quantity'] = 0

        elif event == "remove_by_bid_price":
            event_name = "Removed Some Bidders by Bid Price"
            for bid in sorted_bids:
                if bid["price"] in selected_bids:
                    selected_bids.remove(bid["price"])
                    bid['price'] = 0
                    bid['quantity'] = 0

        else:
            print("Event Not Recognized")
        

        prices = []
        quantities = []
        for bid in sorted_bids:
            prices.append(bid["price"])
            quantities.append(bid["quantity"])

        c = prices #prices
        u = quantities #quantities of each good
        b_eq = [demand, 0]

        #l = [0]*len(c)
        A_eq = [[1]*len(c), [0]*len(c)]
        bounds = []
        for upper_bound in u:
            bounds.append((0, upper_bound))

        #define the quantities cleared and market price  USING MAGIC
        if sum(u) >= demand:
            res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
            print(f"The marginal returned from LinProg: {res.eqlin['marginals']}")
            print(f"The vector x returned from LinProg{res.x}\n\n")
            market_price = res.eqlin["marginals"][0]
            x = res.x
        else:
            market_price = max(c)
            x = u

        graphData = linprog_to_graph(sorted_bids, x, demand, market_price)
        # TODO REDEFINE so that the bids are taken out at the lowest level (directly from the stuff passed back from the front end) Then put back more print statments
        player_profits = []
        player_gains = []
        for index, bid in enumerate(sorted_bids):
            gain = (market_price - bid["generation"]) * x[index]
            bid["data"].add_to_profit((market_price - bid["generation"]) * x[index])
            player_gains.append({"player": bid["player"], "gain": gain})
            player_profits.append({"player": bid["player"], "id": bid["id"], "total": bid["data"].get_profit()})
        sorted_player_profits = sorted(player_profits, key=lambda x: x["total"], reverse=True)
        sorted_player_gains_after_event = sorted(player_gains, key=lambda x: x["gain"], reverse=True)

        data =  {
                    "event": {"event_name": event_name,"event_tag": event},
                    "graphDataAE": graphData,
                    "playerProfitsAE": sorted_player_profits,
                    "playerGainsAE": sorted_player_gains_after_event,
                } 
          
        return data 
    
    @socketio.on('change_phase', namespace='/game')
    def handle_change_phase(data):
        phase = data.get('phase')
        if phase is not None:
            print(f"[SERVER] Received change_phase to: {phase}")
            # Broadcast to all clients in the namespace
            emit('update_phase', {'phase': phase}, namespace='/game', broadcast=True)

socketio.on_namespace(LobbyNamespace('/lobby'))
socketio.on_namespace(GameNamespace('/game'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
