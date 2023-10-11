import config
import mysql.connector
from map import draw_map
from geopy import distance
from blackjack import blackjack_main
import random

MAX_RANGE = 75
# 1. Lataa lisäosat geopy sekä sql-connector-python
# valikon kautta View->Tool Windows->Python Packages
# 2. Aseta config.py-tiedostoon tietokannan käyttäjänimi(user) ja salasana(pwd)
# 3. Käytä tietokantana lp_copy_demogame.sql-tiedostoa, jonka nimi on demo_game
# 4. Projektiin kuuluu config.py, blackjack.py, map.py
yhteys = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    database='demo_game',
    user=config.user,
    password=config.pwd,
    autocommit=True
)


# asettaa pelaajan aloituspaikan tietokantaan sekä päivittää tiedot vierailtujen kenttien joukkoon
def start_new_game(connected_heliports, ICAO, MAX_RANGE, player='Pelaaja', iso_country='GB', gas=400):
    sql = "insert into game "
    sql += f" (location, screen_name, fly_range, country_code, gas_left, gas_consumed) "
    sql += f" VALUES('{ICAO}', '{player}', '{MAX_RANGE}', '{iso_country}', '{gas}', '{0}');"
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    g_id = kursori.lastrowid

    sql = f"insert into heliports_visited (game_id, location) "
    sql += f" values('{g_id}','{ICAO}')"
    kursori = yhteys.cursor()
    kursori.execute(sql)

    goals = get_goals()
    goal_list = []
    for goal in goals:
        for i in range(0, goal['probability'], 1):
            goal_list.append(goal['id'])

    # exclude starting airport
    goal_ports = connected_heliports[1:].copy()
    random.shuffle(goal_ports)

    for i, goal_id in enumerate(goal_list):
        sql = "INSERT INTO goal_ports (game, location, goal) VALUES (%s, %s, %s);"
        cursor = yhteys.cursor(dictionary=True)
        cursor.execute(sql, (g_id, goal_ports[i]['ident'], goal_id))

    return g_id

    return g_id


# hakee iso_country-koodilla valitun valtion helikopterikenttien tiedot tietokannasta
def get_info_of_heliports(iso='GB'):
    sql = (f'select ident, longitude_deg, latitude_deg, name from airport ')
    sql += (f' where iso_country = "{iso}" and airport.type = "heliport"')
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    heliports_info = kursori.fetchall()
    return heliports_info


#   palauttaa kenttien tiedot jotka ovat yhteyksissä max_range-etäisyyden mukaan
def get_connected_heliports(heliports_info):
    connected_heliports = []
    # lisää ensimmäisen kentän listaan, johon vertaillaan yhteyttä
    connected_heliports.append(heliports_info[0])
    for heliport in heliports_info:
        for heliport_to_compare in heliports_info:
            if heliport_to_compare != heliport:
                distance_between = float(distance.distance((heliport['longitude_deg'], heliport['latitude_deg']), (
                heliport_to_compare['longitude_deg'], heliport_to_compare['latitude_deg'])).__str__()[0:5])
                # suorita, jos jompikumpi on listassa ja etäisyys on alle sallitun, ohita, jos molemmat ovat listassa, suoritetaan jos kumpikaan ei ole listassa
                if distance_between < MAX_RANGE and not (
                        heliport_to_compare in connected_heliports and heliport in connected_heliports):
                    if heliport_to_compare in connected_heliports:
                        connected_heliports.append(heliport)
                    elif heliport in connected_heliports:
                        connected_heliports.append(heliport_to_compare)
    # print("Amount of connected heliports", len(connected_heliports))
    return connected_heliports


def get_player_coordinates(g_id):
    sql = f"select longitude_deg, latitude_deg from airport where ident in (select location from game where id = '{g_id}');"
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos


def get_heliport_coordinates(ICAO):
    sql = f"select longitude_deg, latitude_deg from airport where ident = '{ICAO}';"
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos, tulos


def heliports_visited(g_id):
    sql = "select location from heliports_visited "
    sql += f"where game_id = '{g_id}' "
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchall()
    return tulos


# palauttaa pelaajaa lähimmät kentät listana, lisää heliports_info:on etäisyyden pelaajasta
# 'distance_from_player'-muuttujan sisälle sekä järjestää ne lähimmästä kauimpaan
# sekä
def get_heliports_in_range(map_info, g_id):
    player_coordinate = get_player_coordinates(g_id)
    heliports_in_range = []
    for info in map_info:
        if player_coordinate != (info['longitude_deg'], info['latitude_deg']):
            distance_between = float(
                distance.distance((info['longitude_deg'], info['latitude_deg']), player_coordinate).__str__()[0:5])
            info['distance_from_player'] = distance_between
            if distance_between <= get_max_range(g_id):  # and distance_between !=0:
                heliports_in_range.append(info)
    heliports_in_range = sort_heliports_by_distance(heliports_in_range)
    # heliports_in_range = get_map_info(heliports_in_range)
    return heliports_in_range


# palauttaa kentät järjestettynä lähimmästä kauimpaan pelaajasta nähden.
# Lisää järjestysluvun('range_index') palautettavaan listaan,joka näytetään kartalla, jotta pelaaja
# voi valita mihin liikkuu
def sort_heliports_by_distance(heliports_info):
    sorted_heliports_info = heliports_info
    for h in range(len(sorted_heliports_info)):
        min_idx = h
        for p in range(h + 1, len(heliports_info)):
            if sorted_heliports_info[p]['distance_from_player'] < sorted_heliports_info[min_idx][
                'distance_from_player']:
                min_idx = p
        sorted_heliports_info[h], sorted_heliports_info[min_idx] = sorted_heliports_info[min_idx], \
        sorted_heliports_info[h]
    map_index = 0
    for info in sorted_heliports_info:
        map_index += 1
        info['range_index'] = str(map_index)
    return sorted_heliports_info


# näyttää kentän nimen ja etäisyyden pelaajasta nähden rivitettynä
def show_heliports_with_distance(heliports):
    line = ""
    for c in range(3):
        line += f"{'':8.8s} {'Heliport name':25.25s} {'distance in km':9.9s} "
    print(line)
    line = ""
    counter = 1
    for h in range(0, len(heliports)):
        if counter < 4:
            line += (f" | {h + 1:2d}.{heliports[h]['name']:25.25s} | {heliports[h]['distance_from_player']:5.1f} km | ")
            counter += 1
            if counter == 4 or (h + 1) == len(heliports):
                print(line)
                line = ""
                counter = 1


# näyttää pelkästään kentät ilman etäisyyttä, voidaan käyttää esim näyttämään connected_heliports tai
# disconnected_heliports
def show_heliports(heliports):
    line = ""
    for c in range(3):
        line += f"{'':8.8s} {'Heliport name':25.25s}"
    print(line)
    line = ""
    counter = 1
    for h in range(0, len(heliports)):
        if counter < 5:  # ((h + 1) % 4) != 0:
            line += (f" | {h + 1:2d}.{heliports[h]['name']:25.25s} | ")
            counter += 1
            if counter == 5 or (h + 1) == len(heliports):
                print(line)
                line = ""
                counter = 1


def get_gas_left(g_id):
    sql = f"select gas_left from game where id = '{g_id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos[0]


def get_max_range(g_id):
    sql = f"select fly_range from game where id = '{g_id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)
    tulos = kursori.fetchone()
    return tulos[0]


def update_max_range(g_id):
    gas_left = get_gas_left(g_id)
    current_max_range = get_max_range(g_id)
    if gas_left < current_max_range:
        sql = "update game "
        sql += f"set fly_range = gas_left "
        sql += f"where id = '{g_id}' "
        kursori = yhteys.cursor()
        kursori.execute(sql)

    elif gas_left > MAX_RANGE and current_max_range < MAX_RANGE:
        sql = "update game "
        sql += f"set fly_range = '{MAX_RANGE}' "
        sql += f"where id = '{g_id}' "
        kursori = yhteys.cursor()
        kursori.execute(sql)


# päivittää tietokantaan pelaajan sijainnin sekä muut tarvittavat arvot
def update_player_move(distance_moved, g_id, ICAO):
    sql = "update game "
    sql += f"set gas_consumed = (gas_consumed)+'{distance_moved}' "
    sql += f",gas_left = gas_left-'{distance_moved}' "
    sql += f", location = '{ICAO}' "
    sql += f", turns = (turns) + '{1}' "
    sql += f" where id = '{g_id}' ;"
    kursori = yhteys.cursor()
    kursori.execute(sql)

    update_max_range(g_id)

    sql = "select game_id, location from heliports_visited"
    kursori.execute(sql)
    tulos = kursori.fetchall()
    # tarkastaa ettei jo vierailtua kenttää lisätä listaan toiseen kertaan
    if (g_id, ICAO) not in tulos:
        sql = f"insert into heliports_visited(game_id, location) "
        sql += f" values('{g_id}','{ICAO}')"
        kursori.execute(sql)


# käytetään arvon tarkistamaan että pelaaja antaa käyttökelpoisen syötteen, kesken
def ask_location_num(number_of_heliports):
    chosen_heliport_num = -1
    while chosen_heliport_num > len(number_of_heliports) or chosen_heliport_num <= 0:
        chosen_heliport_num = (input("Give heliport number you want to travel to: "))
        if not is_int(chosen_heliport_num):
            print("Given choice is not valid!")
            chosen_heliport_num = -1
        else:
            chosen_heliport_num = int(chosen_heliport_num)
            if chosen_heliport_num > len(number_of_heliports) or chosen_heliport_num <= 0:
                print("Given number is not valid!")
    return chosen_heliport_num - 1


def get_disconnected_heliports(connected_heliports):
    # connected_heliports = get_connected_heliports(heliports_info)
    disconnected_heliports = []
    for heliport in heliports_info:
        if (heliport not in connected_heliports):
            disconnected_heliports.append(heliport)
    return disconnected_heliports


# palauttaa kenttien kauimmat kulmapisteet/koordinaatit,
# käytetään skaalaamaan karttaa. Siis alin vasen, alin oikea, ylin vasen ja ylin oikea koordinaatti
# Tekee muutakin mutta tiedoille ei ole ainakaan vielä käyttöä
def get_corner_lon_lat(connected_heliports):
    corner_heliports = {}
    min_lon_index = 0
    for h in range(1, len(connected_heliports)):
        if connected_heliports[min_lon_index]['longitude_deg'] > connected_heliports[h]['longitude_deg']:
            min_lon_index = h
    max_lon_index = 0

    for h in range(1, len(connected_heliports)):
        if connected_heliports[max_lon_index]['longitude_deg'] < connected_heliports[h]['longitude_deg']:
            max_lon_index = h

    min_lat_index = 0
    for h in range(1, len(connected_heliports)):
        if connected_heliports[min_lat_index]['latitude_deg'] > connected_heliports[h]['latitude_deg']:
            min_lat_index = h
    max_lat_index = 0
    for h in range(1, len(connected_heliports)):
        if connected_heliports[max_lat_index]['latitude_deg'] < connected_heliports[h]['latitude_deg']:
            max_lat_index = h

    corner_lon_lat = {'min_lon': connected_heliports[min_lon_index]['longitude_deg'], \
                      'max_lon': connected_heliports[max_lon_index]['longitude_deg'], \
                      'min_lat': connected_heliports[min_lat_index]['latitude_deg'], \
                      'max_lat': connected_heliports[max_lat_index]['latitude_deg']}

    # hakee pisteiden välisen pituuden ja korkeuden, tarkastaa mikä on pisin etäisyys pisteiden välillä
    left_height = get_distance(connected_heliports, min_lon_index, min_lat_index, min_lon_index, max_lat_index)
    upper_width = get_distance(connected_heliports, min_lon_index, max_lat_index, max_lon_index, max_lat_index)
    right_height = get_distance(connected_heliports, max_lon_index, max_lat_index, max_lon_index, min_lat_index)
    lower_width = get_distance(connected_heliports, min_lon_index, min_lat_index, max_lon_index, min_lat_index)
    if (lower_width < upper_width):
        height = upper_width
    else:
        height = lower_width
    if right_height < left_height:
        width = left_height
    else:
        width = right_height

    # print("low left coordinates:", corner_lon_lat['min_lon'], corner_lon_lat['min_lat'])
    # print("low right coordinates:", corner_lon_lat['max_lon'], corner_lon_lat['min_lat'])
    # print("top right coordinates:", corner_lon_lat['max_lon'], corner_lon_lat['max_lat'])
    # print("top left coordinates: ", "lon", corner_lon_lat['min_lon'], ", lat", corner_lon_lat['max_lat'])
    # print("height",height, "width", width)

    return corner_lon_lat


# käytetään ylempään funktioon
def get_distance(connected_maps, lon_index, lat_index, lon2_index, lat2_index):
    distance_between = distance.distance( \
        (connected_heliports[lon_index]['longitude_deg'], connected_heliports[lat_index]['latitude_deg']), \
        (connected_heliports[lon2_index]['longitude_deg'], connected_heliports[lat2_index]['latitude_deg']))
    return distance_between


def get_map_info(connected_heliports):
    # Haetaan reunapisteet
    lon_lat = get_corner_lon_lat(connected_heliports)
    map_info = []
    # näillä jaetaan kartta ruudukkoon, joka on 58 ruutua leveä ja 18 ruutua korkea
    map_width = 58
    map_height = 18
    # Asetetaan kartan reunapisteet, muutetaan koordinaatit floatista int-muotoon.
    # Lisätään marginaalit reunoille ja skaalataan hieman, muuten luku on epätarkka
    min_lon = int((lon_lat['min_lon'] - 0.8) * 1000)
    max_lon = int((lon_lat['max_lon'] + 0.8) * 1000)
    min_lat = int((lon_lat['min_lat'] - 0.6) * 500)
    max_lat = int((lon_lat['max_lat'] + 0.6) * 500)
    # Yksi askel vastaa yhtä ruudukkoa koordinaatistossa, eli ruudun korkeus on stepY, leveys stepX
    # Lasketaan reunapisteiden etäisyys toisistaan, ja jaetaan se tasaisesti jokaiselle ruudulle
    stepY = int((min_lat - max_lat) / map_height)
    stepX = int((max_lon - min_lon) / map_width)
    # käydään läpi kaikki yhteyksissä olevat kentät ja lisätään niihin tieto sen koordinaateista kartalla
    for connected_heliport in connected_heliports:
        row_num = 0
        # Käydään läpi jokainen ruudukko koordinaatistossa, ja jos kentän koordinaatit
        # ovat ruudukon sisällä, niin asetetaan koordinaatit talteen kentän tietoihin,
        # jotta osataan map.py:ssä laittaa oikealle paikalle merkki
        for y in range(max_lat, min_lat, stepY):  # (5450, 5050, -50)
            column_num = 0
            for x in range(min_lon, max_lon, stepX):  # (-4000, -600, 68 )
                if connected_heliport['longitude_deg'] > (float(x) / 1000) and connected_heliport[
                    'longitude_deg'] < (float(x + stepX) / 1000) and connected_heliport['latitude_deg'] < (
                        float(y) / 500) and connected_heliport['latitude_deg'] > (float(y + stepY) / 500):
                    connected_heliport['x'] = column_num
                    connected_heliport['y'] = row_num
                    map_info.append(connected_heliport)
                column_num += 1
            row_num += 1
    return map_info


def get_game_ids(iso_country='GB'):
    sql = f"select id, screen_name from game where country_code = '{iso_country}';"
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchall()
    return tulos


def get_game_id(connected_heliports, iso_country='GB'):
    selection = 0
    while selection != 'c' and selection != 'n' or selection == 0:
        selection = input("Type 'n' start new game or 'c' to continue game: ")
        if selection == 'c':
            ids = get_game_ids(iso_country)
            if len(ids) == 0:
                screen_name = input("No games found! Starting new game, give player name: ")
                g_id = start_new_game(connected_heliports, connected_heliports[0]['ident'], MAX_RANGE, screen_name)
            else:
                slot = 0
                while 0 >= slot or slot > len(ids):  ## or type(slot) != int:
                    for id in ids:
                        print(f"Slot {id['id']} | Name: {id['screen_name']} ")
                    slot = (input("Type slot number to select"))
                    if not is_int(slot):
                        print("Given slot doesnt exist!")
                        slot = 0
                    else:
                        slot = int(slot)
                        if 0 >= slot or slot > len(ids):
                            print("Given slot doesnt exist!")
                        else:
                            g_id = slot
        elif selection == 'n':
            screen_name = input("Starting new game, give player name: ")
            g_id = start_new_game(connected_heliports, connected_heliports[0]['ident'], MAX_RANGE, screen_name)
        else:
            print("Not valid choice!")
    return g_id


# get all goals
def get_goals():
    sql = "SELECT * FROM goal;"
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    result = kursori.fetchall()
    return result


def update_player_gas(g_id, gas_gained):
    sql = "update game "
    sql += f" set gas_left = gas_left+'{gas_gained}' "
    sql += f" where id = '{g_id}'"
    kursori = yhteys.cursor()
    kursori.execute(sql)
    update_max_range(g_id)


def check_goal(g_id, cur_airport):
    sql = f'''SELECT goal_ports.id, goal, goal.id as goal_id, name, target_value, opened 
    FROM goal_ports 
    JOIN goal ON goal.id = goal_ports.goal 
    WHERE game = %s 
    AND location = %s'''
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql, (g_id, cur_airport))
    result = kursori.fetchone()
    if result is None:
        return False
    elif result['opened'] == 1:
        return False
    else:
        result['opened'] == 1
        set_goal_opened(result['id'])
        update_player_gas(g_id, result['target_value'])
    return result


def set_goal_opened(id):
    sql = "update goal_ports "
    sql += "set opened = '1' "
    sql += f"where id = '{id}' "
    kursori = yhteys.cursor()
    kursori.execute(sql)


def is_int(x):
    try:
        int(x)
        return True
    except:
        return False


def ask_bet(g_id):
    bet = 0
    while bet > get_gas_left(g_id) or bet <= 0:
        bet = input("How much you want to bet for: ")
        if is_int(bet):
            bet = int(bet)
        else:
            bet = 0
    return bet


def play_game(g_id, goal):
    answer = 'NULL'
    print(f"\33[0;34m Shady squirrel challenges you to play {goal['name']}!\33[0m")
    while answer != 'y' and answer != 'n':
        answer = input(f"Type 'y' to play {goal['name']}, 'n' to continue game: ")
    if answer == 'y':
        return True
    elif answer == 'y':
        return False


def dice_game():
    dice1 = random.randint(1, 6)

    dice2 = random.randint(1, 6)

    print(f"You got {dice1} and {dice2}")

    if dice1 == dice2:
        print(f"Dices match! Congrats, you won!")
        result = 'Won'

    else:
        print("You lost! Unlucky!")
        result = 'Lost'

    input("Press 'Enter' to continue")
    return result


def coinflip():
    guess = input("Guess the outcome (Heads or Tails): ").capitalize()

    while guess not in ["H", "T"]:
        print("Incorrect input! Try gain")
        guess = input("Guess the outcome (Type 'H' for Heads or 'T' for Tails): ").capitalize()

    result = random.choice(["H", "T"])
    if result == 'H':
        print(f"The coin landed on Heads.")
    elif result == "T":
        print("The coin landed on Tails.")

    if guess == result:
        print(f"Congrats, you guessed right! You won!")
        result = "Won"
    else:
        print("You guessed wrong, you lost! Unlucky!")
        result = "Lost"
    input("Press 'Enter to continue")

    return result


def run_minigame(g_id, bet, goal):
    result = 0
    winnings = 0
    if goal['name'] == "Coinflip":
        result = coinflip()
        if result == 'Won':
            winnings = bet
    elif goal['name'] == "Dicegame":
        result = dice_game()
        if result == 'Won':
            winnings = bet * 3
    elif goal['name'] == "Blackjack":
        result = blackjack_main()
        if result == 'Won':
            winnings = bet
    if result == 'Lost':
        winnings = -bet
    update_player_gas(g_id, winnings)
    return winnings


def get_player_score(g_id):
    sql = f"SELECT gas_left, gas_consumed, turns FROM game where id = '{g_id}' "
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchall()[0]
    score = int(tulos['gas_left'] - tulos['gas_consumed'])

    return score


def get_high_scores():
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute("SELECT * FROM high_score ORDER BY score DESC")
    tulos = kursori.fetchall()
    return tulos


# kerätään pelaajan pisteet tulostaulukkoon
def update_highscore(g_id, list_id):
    kursori = yhteys.cursor()
    kursori.execute(
        f"update high_score set screen_name = (select screen_name from game where id= '{g_id}'),  score = (select (gas_left-gas_consumed) from game where id = '{g_id}') where list_id = '{list_id}';")


# näytetään tulostaulu
def display_highscore():
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute("SELECT * FROM high_score ORDER BY score DESC")
    tulos = kursori.fetchall()
    line = " /"
    print(f"{'':8s} HIGH SCORES")
    for _ in range(25):
        line += "="
    line += "\ "
    print(line)
    line = " |"
    for _ in range(25):
        line += "-"
    line += "|"
    for i, high_score in enumerate(tulos):

        print(f" | {i + 1:2d}. {high_score['screen_name']:10s} |  {high_score['score']:5d} |")
        if i < len(tulos) - 1:
            print(line)
    line = " \\"
    for _ in range(25):
        line += "="
    line += "/"
    print(line)


def is_bigger_than_high_scores(g_id):
    high_scores = get_high_scores()
    for high_score in high_scores:
        if high_score['score'] < get_player_score(g_id):
            update_highscore(game_id, high_score['list_id'])
            break


def get_gas_consumed(g_id):
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(f"SELECT gas_consumed FROM game where '{g_id}' ")
    tulos = kursori.fetchall()
    return tulos[0]


def get_stats(g_id):
    sql = f"SELECT screen_name, gas_left, gas_consumed, turns, location, fly_range FROM game where id = '{g_id}' "
    kursori = yhteys.cursor(dictionary=True)
    kursori.execute(sql)
    tulos = kursori.fetchall()

    return tulos[0]


# heliports_info = get_info_of_heliports()
# connected_heliports = get_connected_heliports(heliports_info)
# disconnected_heliports = get_disconnected_heliports(connected_heliports)
# show_heliports(heliports_info)
# show_heliports(disconnected_hgeliports)
# show_heliports(connected_heliports)
# print(f" {'Amount of connected heliports':32.32s}:", len(connected_heliports))
# print(f" {'Amount of disconnected heliports':32.32s}:", len(disconnected_heliports))
# print(f" {'Amount of all heliports':32.32s}:", len(heliports_info))
heliports_info = get_info_of_heliports()
connected_heliports = get_connected_heliports(heliports_info)
map_info = get_map_info(connected_heliports)
# print(map_info)
# get_corner_lon_lat(connected_heliports)


print('''
    The Squirrel Nation has revered the Great Pine Tree for many generations. 
    Every few years the Great Pine Tree produces a single Mega Cone that is 
    treasured and revered in an almost religious manner. If something were 
    to happen to this most sacred cone, all of \33[4msquirrelkind\33[0m 
    would descend into turmoil... 

    Now the unspeakable has happened: The Mega Cone has disappeared!     

    The Cone Copter Guard are the devout guardians of the Great Pine Tree and the Squirrel 
    Nation. Take your place among the daring pilots and spare no cone to fulfill your duty! 
    Your task as the pilot of the Cone Helicopter Guard is to find it and in so doing pass 
    the game. Try to also collect as many regular cones as possible along the way. They 
    serve as fuel for your chopper and give you points. 
    
    Be careful, because if you run out 
    of cones, it's game over. Extra cones will be used to plant trees for the good 
    of all \33[4msquirrelkind!\33[0m One for all and all for the cones!
    ''')

game_id = get_game_id(connected_heliports)
GameOver = False
# get_heliports_in_range(connected_heliports)
gameStart = True

goal = False

actionline = ["", "", ""]
while not GameOver:
    heliports_in_range = get_heliports_in_range(map_info, game_id)
    print(f" {'Heliports near player':32.32s}:", len(heliports_in_range))
    draw_map(map_info, heliports_in_range, get_player_coordinates(game_id), heliports_visited(game_id), goal,
             actionline, get_stats(game_id))

    if len(heliports_in_range) != 0:
        chosen_heliport_num = ask_location_num(heliports_in_range)
        update_player_move((heliports_in_range[chosen_heliport_num]['distance_from_player']), game_id,
                           heliports_in_range[chosen_heliport_num]['ident'])
        goal = check_goal(game_id, heliports_in_range[chosen_heliport_num]['ident'])
        heliports_in_range = get_heliports_in_range(map_info, game_id)
        draw_map(map_info, heliports_in_range, get_player_coordinates(game_id),
                 heliports_visited(game_id), goal, actionline, get_stats(game_id))

    # draw_map(map_info, heliports_in_range, get_player_coordinates(game_id), MAX_RANGE, heliports_visited(game_id), goal)
    if goal != False:
        game_on = False
        if goal['name'] == "Great":
            print("\33[0;36m \33[7m You found THE MEGA CONE! You win! \33[0m")
            GameOver = True
        elif goal['name'] == "Coinflip" or goal['name'] == "Dicegame" or goal['name'] == "Blackjack":
            game_on = play_game(game_id, goal)
            if game_on:
                bet = ask_bet(game_id)
                winnings = run_minigame(game_id, bet, goal)
                if winnings > 0:
                    actionline[0] = f" | You won {winnings} from {goal['name']}!  "
                elif winnings < 0:
                    actionline[0] = f" | You lost {winnings} in {goal['name']}!  "
    heliports_in_range = get_heliports_in_range(map_info, game_id)
    if len(heliports_in_range) == 0:
        GameOver = True
        print("\33[0;31m You run out of pine cones! Game over!\33[0m")

        # print(heliports_in_range[chosen_heliport_num]['name'])
print("Your score ", get_player_score(game_id))  # , get_gas_left(game_id), get_gas_consumed(game_id) )
is_bigger_than_high_scores(game_id)
display_highscore()