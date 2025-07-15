import random
import string

assets = [
    ("Coal", 30, 2000),                         ("Natural Gas (Combined Cycle)", 95, 1000),
    ("Natural Gas (Open Cycle)", 100, 500),     ("Nuclear", 90, 600),
    ("Wind (onshore)", 2.5, 10),                ("Wind (Offshore)", 2.5, 10),
    ("Solar Photovoltaic", 2.5, 500),           ("Concentrated Solar Power", 2.5, 100),
    ("Large-Scale Hydropower", 15, 300),        ("Geothermal", 70, 70),
    ("Biomass (Wood)", 25, 70),                 ("Biomass (Agricultural Waste)", 45, 30),
    ("Biogas (Landfills)", 60, 10),             ("Tidal Power", 2.5, 3),
    ("Wave Power", 2.5, 4),                     ("Hydrogen Fuel Cells", 100, 3),
    ("Waste-to-Energy (Incineration)", 60, 10), ("Waste-to-Energy (Landfill Gas)", 50, 1),
    ("Hydrogen Gas Turbine", 150, 200),         ("Compressed Air Energy", 50, 10),
    ("Pumped Storage Hydroelectric", 20, 100),  ("Shale Oil Power Generation", 150, 10),
    ("Coal-to-Liquid", 35, 100),                ("Concentrated Solar Thermal", 2.5, 50),
    ("Organic Photovoltaic", 2.5, 1),           ("Microgrids (Renewable)", 10, 5),
    ("Small Modular Reactors", 0, 100),         ("Ocean Thermal Energy Conversion", 2.5, 20),
    ("Algae Biofuel", 80, 20),                  ("Magnetohydrodynamic", 10, 100) 
] 

market_cap = 9000
used_ids = set()

def generate_user_id(length=8):
    while True:
        user_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        if user_id not in used_ids:
            used_ids.add(user_id)
            return user_id
        
def get_random_rgba():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

class Bid:
    def __init__(self):
        self.asset = ""
        self.units = 0
        self.generation = 0
        self.price = 0
        self.quantity = 0
    
    def set_asset_data(self, asset, units, generation):
        self.asset = asset
        self.units = units
        self.generation = generation
    
    def set_price_quantity(self, price, quantity):
        self.price = price
        self.quantity = quantity
        
    def get_units(self):
        return self.units
    
    def get_quantity(self):
        return self.quantity
    
    def get_generation(self):
        return self.generation
    
    def get_json_bid(self):
        x = {
            "asset": self.asset, 
            "units": self.units,
            "generation": self.generation,
            "price": self.price,
            "quantity": self.quantity 
        }
        return x
    

class Data:
    def __init__(self, username, id, bid_size, profit):
        self.username = username 
        self.id = id
        self.bids = [Bid() for _ in range(bid_size)]
        self.profit = profit
        self.color =  get_random_rgba() # (0, 255, 0)
        self.hasBid = False

    def get_player_bids(self):
        return self.bids
    
    def get_player_single_bid(self):
        return self.bids[0] # There is only one bid right now but in the future might have multiple

    def has_player_bid(self):
        return self.hasBid

    def get_all_player_units(self):
        count = 0
        for b in self.bids:
            count += b.get_units()
        return count

    def set_bid_status(self, input):
        self.hasBid = input
    
    def add_to_profit(self, in_profit):
        self.profit += in_profit
    
    def get_profit(self):
        return self.profit
    
    def get_id(self):
        return self.id

    def get_json_data(self):
        bids = []
        for bid in self.get_player_bids():
            bids.append(bid.get_json_bid())

        x = { 
            "username": self.username, 
            "id": self.id,
            "bids": bids,
            "profit": self.profit,
            "color": self.color,
            "hasBid": self.hasBid 
            }
        return x

class Player:
    def __init__(self, username, sid=""):
        self.username = username
        self.sid = sid
    
    def get_player_name(self):
        return self.username

    def get_player_sid(self):
        return self.sid

    def set_player_sid(self, input_sid):
        self.sid = input_sid

    def get_json_player(self):
        x = {
            "username": self.username, 
            "sid": self.sid
        }

        return x

class Room:
    def __init__(self, admin_username):
        self.admin = Player(admin_username)
        self.players = []  # List of Player objects
        self.playersData = []  # List of Data objects
        self.game = {"started": False, "currentRound": 1}

    def add_player(self, username, sid=""):
        self.players.append(Player(username, sid))

    def add_data(self, name, bid_size, profit):
        self.playersData.append(Data(name, generate_user_id(), bid_size, profit))

    def get_room_status(self):
        return self.game["started"]
    
    def get_admin(self):
        return self.admin.get_player_name()

    def get_admin_sid(self):
        return self.admin.get_player_sid()

    def set_room_status(self, input_game_status):
        self.game["started"] = input_game_status

    def remove_player(self, name):
        for player in self.players:
            if player.username == name:
                self.players.remove(player)
                break

    def create_players_data(self):
        for d in self.players:
            self.add_data(d.get_player_name(), 1, 0)

        asset_indexes = list(range(len(assets)))
        for data in self.playersData:
            for b in data.get_player_bids():
                # Reset the asset index list if it's empty
                if not asset_indexes:
                    asset_indexes = list(range(len(assets)))
                
                rand_asset = random.choice(asset_indexes)
                asset_indexes.remove(rand_asset)
                
                b.set_asset_data(
                    assets[rand_asset][0], 
                    random.randint(400, 800), 
                    assets[rand_asset][1]
                )

    def get_sid_from_players(self, input_username):
        p = self.admin
        if input_username != self.admin.get_player_name():
            p = self.get_player(input_username)
        return p.get_player_sid()

    def set_sid_from_players(self, input_username, input_sid):
        p = self.admin
        if input_username != self.admin.get_player_name():
            p = self.get_player(input_username)
        p.set_player_sid(input_sid)

    def get_player_data(self, input_username):
        p = self.get_data(input_username)
        return p.get_json_data()

    def get_player_data_object(self, input_username):
        p = self.get_data(input_username)
        return p
    
    def get_player_bid_status(self, input_username):
        d = self.get_data(input_username)
        return d.has_player_bid()

    def has_all_players_bid(self):
        for d in self.playersData:
            if(not d.has_player_bid()):
                return False
        return True
    
    def set_all_players_bid_status(self, input_status):
        for p in self.playersData:
            p.set_bid_status(input_status)

    def get_total_bid_units(self):
        count = 0
        for d in self.playersData:
            for b in d.get_player_bids():
                count += b.get_quantity()
        return count 

    def get_current_round(self):
        return self.game["currentRound"]

    def increment_round(self):
        self.game["currentRound"] = self.game["currentRound"]+1

    def get_json_all_bids(self):
        all_bids = []
        for p_data in self.playersData:
            for bid in p_data.get_player_bids():
                in_json = bid.get_json_bid()
                in_json["data"] = p_data
                in_json["player"] = p_data.username
                in_json["id"] = p_data.get_id()
                in_json["color"] = p_data.color
                all_bids.append(in_json)
        return all_bids
    
    def get_json_room(self):
        x = {
            "admin": self.admin.get_json_player(),
            "players": [p.get_json_player() for p in self.players], #(call get_json_player on each element of the array),
            "playersData": [d.get_json_data() for d in self.playersData], #(call get_json_data on each element of the array),
            "game": self.game
            }
        return x

    def get_player(self, input_username):
        return next((obj for obj in self.players if obj.username == input_username), None)
    
    def get_data(self, input_username):
        return next((obj for obj in self.playersData if obj.username == input_username), None)

class RoomManager:
    def __init__(self):
        self.rooms = {} # dictionary of Room classes

    def create_room(self, admin_username):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if code not in self.rooms: 
                self.rooms[code] = Room(admin_username)
                return code

    def delete_room(self, input_room_code):
        del self.rooms[input_room_code]
        
    def get_room(self, input_room_code):
        return self.rooms.get(input_room_code)
    
    def get_rooms(self):
        return self.rooms

    def get_game_status(self, input_room_code):
        return (self.rooms[input_room_code]).get_room_status()

    def set_game_status(self, input_room_code, input_game_status):
        return (self.rooms[input_room_code]).set_room_status(input_game_status)
    
    def get_username_from_players_room(self, input_room_code):
        return self.rooms[input_room_code].players

    def get_sid_from_players_room(self, input_username, input_room_code):#QUESTION wouldnt this also need the room code?
        return self.rooms[input_room_code].get_sid_from_players(input_username)

    def set_sid_from_players_room(self, input_room_code, input_username, input_sid):#QUESTION doenst this need room code too?
        self.rooms[input_room_code].set_sid_from_players(input_username, input_sid)

    def get_player_stats(self, input_room_code, input_username):#QUESTION room code here too?
        return self.rooms[input_room_code].get_player_data(input_username)

    def get_players_room_bid_status(self, input_room_code, input_username):
        return self.rooms[input_room_code].get_player_bid_status(input_username)

    def get_rooms_total_bid_units(self, input_room_code):
        return self.rooms[input_room_code].get_total_units()

    def get_room_current_round(self, input_room_code):
        return self.rooms[input_room_code].get_current_round()

    def increment_room_round(self, input_room_code):
        return self.rooms[input_room_code].increment_round()

    def set_all_players_in_room_bid_status(self, input_room_code, input_status):
        return self.rooms[input_room_code].set_all_players_bid_status(input_status)
