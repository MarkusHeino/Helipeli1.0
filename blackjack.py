import random


# print(f'\033[7;31mThere are 12 airports in range: \033[0m hey')
def is_int(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


def get_hand_value(hand):
    ace_in_hand = False
    value = 0
    for card in hand:
        if card['value'] > 10:
            value += 10
        else:
            value += card['value']
        if card['value'] == 1:
            ace_in_hand = True

    if ace_in_hand:
        if value+10 <= 21:
            value += 10
    return value


def get_hand_line(hand):
    value = get_hand_value(hand)
    line = f"{'You have':10s}  {value:2d}"
    for card in hand:
        line += f" |{card['value']:2d} {card['suit'][0]}|"
    return line


def get_house_hand_line(hand):
    value = get_hand_value(hand)
    line = f"{'House has':10s}  {value:2d}"
    for card in hand:
        line += f" |{card['value']:2d} {card['suit'][0]}|"
    return line


def get_game_result(p_value, h_value):
    result = "NULL"
    if p_value > 21:
        result = "Lost"
    elif h_value > 21:
        result = "Won"
    elif p_value == h_value:
        result = "Draw"
    elif p_value > h_value:
        result = "Won"
    elif p_value < h_value:
        result = "Lost"
    return result


def get_win_line(result):
    line = ""
    if result == "Draw":
        line = "Its a draw!"
    elif result == "Won":
        line = "You win!"
    elif result == "Lost":
        line = "You lose!"
    return line


def get_house_line(deck, p_value):
    house_hand = []
    house_hand.append(deck.pop())
    house_hand.append(deck.pop())
    h_value = get_hand_value(house_hand)
    while h_value < p_value and h_value < 21:
        house_hand.append(deck.pop())
        h_value = get_hand_value(house_hand)
    line = get_house_hand_line(house_hand)
    return line


def ask_hit_or_stay():
    answer = ""
    while answer != 's' and answer != 'h':
        answer = input("Type 'h' to hit new card or 's' to stay: ")
    if answer == 's':
        return False
    else:
        return True


def blackjack_main():
    suits = {'Hearts': 1, 'Diamonds': 2, 'Clubs': 3, 'Spades': 4}
    deck = []
    for s, suit in enumerate(suits):
        for value in range(1, 14):
            deck.append({'suit': suit, 'value': value})

    random.shuffle(deck)

    player_hand = []
    player_hand.append(deck.pop())
    player_hand.append(deck.pop())
    p_value = get_hand_value(player_hand)
    line = get_hand_line(player_hand)

    house_hand = []
    house_hand.append(deck.pop())
    house_hand.append(deck.pop())
    h_value = get_hand_value(house_hand)
    line += f".     House hand: |{house_hand[0]['value']:2d} {house_hand[0]['suit'][0]}| |???|"
    print(line)

    hit_more = True

    while hit_more and p_value <= 21:
        if p_value != 21:
            hit_more = ask_hit_or_stay()
        else:
            hit_more = False
        if hit_more:
            player_hand.append(deck.pop())
            p_value = get_hand_value(player_hand)
            line = get_hand_line(player_hand)
            print(line)
        else:
            line = get_hand_line(player_hand)

    if p_value <= 21:
        while h_value < p_value and h_value < 21:
            house_hand.append(deck.pop())
            h_value = get_hand_value(house_hand)
    line2 = get_house_hand_line(house_hand)

    result = get_game_result(p_value, h_value)
    line3 = get_win_line(result)
    print("+------------------------------------------+")
    print(line)
    print(line2)
    print(line3)
    input("Press 'Enter' to continue")
    return result