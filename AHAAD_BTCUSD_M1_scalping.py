import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import datetime
import pytz
import time
import os
import pandas_ta as pta

# Configuration
symbol = "BTCUSD"
timeframe = mt5.TIMEFRAME_M1
nb_candles = 100
min_ratio_change = 1.618033

current_position = None
entry_price = 0.0
simulation_mode = False
simulated_trades = []
simulated_balance = 100
simulated_gains = 0
consecutive_losses = 0
simulated_current_position = None
simulated_entry_price = 0.0
simulated_entry_time = None

ascii_art = """
... # 1.618 AHAAD #...
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣴⣶⣶⣶⣶⣦⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣀⣤⣾⣿⡿⠿⠛⠛⠛⠛⠛⠛⠻⢿⣿⣿⣦⣄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢠⣼⣿⡿⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠿⣿⣷⣄⠀⠀⠀⠀
⠀⠀⠀⣰⣿⡿⠋⠀⠀⠀⠀⠀⣿⡇⠀⢸⣿⡇⠀⠀⠀⠀⠀⠈⢿⣿⣦⡀⠀⠀
⠀⠀⣸⣿⡿⠀⠀⠀⠸⠿⣿⣿⣿⡿⠿⠿⣿⣿⣿⣶⣄⠀⠀⠀⠀⢹⣿⣷⠀⠀
⠀⢠⣿⡿⠁⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠀⠈⣿⣿⣿⠀⠀⠀⠀⠀⢹⣿⣧⠀
⠀⣾⣿⡇⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⢀⣠⣿⣿⠟⠀⠀⠀⠀⠀⠈⣿⣿⠀
⠀⣿⣿⡇⠀⠀⠀⠀⠀⠀⢸⣿⣿⡿⠿⠿⠿⣿⣿⣥⣄⠀⠀⠀⠀⠀⠀⣿⣿⠀
⠀⢿⣿⡇⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠀⠀⢻⣿⣿⣧⠀⠀⠀⠀⢀⣿⣿⠀
⠀⠘⣿⣷⡀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠀⠀⣼⣿⣿⡿⠀⠀⠀⠀⣸⣿⡟⠀
⠀⠀⢹⣿⣷⡀⠀⠀⢰⣶⣿⣿⣿⣷⣶⣶⣶⣾⣿⣿⠿⠛⠁⠀⠀⠀⣸⣿⡿⠀⠀
⠀⠀⠀⠹⣿⣷⣄⠀⠀⠀⠀⠀⣿⡇⠀⢸⣿⡇⠀⠀⠀⠀⠀⢀⣾⣿⠟⠁⠀⠀
⠀⠀⠀⠀⠘⢻⣿⣷⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣾⣿⡿⠋⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⠛⢿⣿⣷⣶⣤⣤⣤⣤⣤⣤⣴⣾⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⠻⠿⠿⠿⠿⠟⠛⠉⠁
... # BTCUSD #...
... # Make with love by Mister Robot # ...
"""

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(ascii_art)

def get_account_balance():
    account_info = mt5.account_info()
    if account_info is not None:
        return account_info.balance
    else:
        print("Échec de la récupération des informations du compte")
        return None

def get_data(timeframe, n=1000):
    utc_now = datetime.datetime.now(pytz.utc)
    utc_from = utc_now - datetime.timedelta(minutes=n)
    rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_now)
    if rates is None or len(rates) < 100:
        print(f"Pas assez de données récupérées pour le timeframe {timeframe}")
        return None
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s', utc=True)
    data.set_index('time', inplace=True)
    return data

def open_order(order_type):
    global current_position, entry_price, consecutive_losses, simulation_mode
    if simulation_mode:
        print("En mode simulation, aucun ordre réel n'est envoyé.")
        return
    balance = get_account_balance()
    if balance is None:
        print("Impossible de récupérer le solde du compte")
        return
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "introuvable")
        return
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print("Échec de la sélection de", symbol)
            return
    lot = float("{:.2f}".format(balance * 0.0001))
    if lot > symbol_info.volume_max:
        lot = symbol_info.volume_max
    if lot < 0.01:
        lot = 0.01
    if order_type == 'buy':
        price = mt5.symbol_info_tick(symbol).ask
        order_type_mt5 = mt5.ORDER_TYPE_BUY
    elif order_type == 'sell':
        price = mt5.symbol_info_tick(symbol).bid
        order_type_mt5 = mt5.ORDER_TYPE_SELL
    else:
        print("Type d'ordre non valide")
        return
    deviation = 20
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type_mt5,
        "price": price,
        "deviation": deviation,
        "magic": 1618,
        "comment": f"Python script open {order_type}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Échec de l'envoi de l'ordre {order_type}, retcode =", result.retcode)
    else:
        clear_console()
        print(f"Ordre {order_type} ouvert au prix {price}")
        current_position = order_type
        entry_price = price

def close_order():
    global current_position, entry_price, consecutive_losses, simulation_mode, simulated_gains
    if simulation_mode:
        print("En mode simulation, aucune position réelle n'est clôturée.")
        return
    if current_position is None:
        print("Aucune position ouverte à clôturer")
        return
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        print("Aucune position trouvée pour le symbole", symbol)
        current_position = None
        entry_price = 0.0
        return
    pos = positions[0]
    lot = pos.volume
    if pos.type == mt5.POSITION_TYPE_BUY:
        order_type_mt5 = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
    elif pos.type == mt5.POSITION_TYPE_SELL:
        order_type_mt5 = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
    else:
        print("Type de position inconnu")
        return
    deviation = 20
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type_mt5,
        "position": pos.ticket,
        "price": price,
        "deviation": deviation,
        "magic": 1618,
        "comment": f"Python script close {current_position}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Échec de la clôture de la position {current_position}, retcode =", result.retcode)
    else:
        print(f"Position {current_position} clôturée au prix {price}")
        if current_position == 'buy':
            profit = (price - entry_price) * 0.01
        elif current_position == 'sell':
            profit = (entry_price - price) * 0.01
        else:
            profit = 0.0
        clear_console()
        print(ascii_art)

        if profit > 0:
            print("Trade réel gagnant")
            consecutive_losses = 0
        else:
            print("Trade réel perdant")
            consecutive_losses += 1
            if consecutive_losses >= 3:
                simulation_mode = True
                simulated_gains = 0
                print("3 pertes consécutives atteintes. Passage en mode simulation.")
        current_position = None
        entry_price = 0.0

def build_volume_dataframe(data_m1):
    data_m1['Buyer_Volume'] = 0.0
    data_m1['Seller_Volume'] = 0.0
    for i in range(len(data_m1)):
        o = data_m1['open'].iloc[i]
        h = data_m1['high'].iloc[i]
        l = data_m1['low'].iloc[i]
        c = data_m1['close'].iloc[i]
        tv = data_m1['tick_volume'].iloc[i]

        if tv == 0:
            buyer_vol = 0.0
            seller_vol = 0.0
        else:
            rng = h - l if (h - l) != 0 else 1e-9
            body = abs(c - o)
            body_ratio = body / rng
            close_pos = (c - l) / rng

            if c > o:
                buyer_factor = (body_ratio + close_pos) / 2
                buyer_vol = tv * buyer_factor
                seller_vol = tv - buyer_vol
            elif c < o:
                seller_factor = (body_ratio + (1 - close_pos)) / 2
                seller_vol = tv * seller_factor
                buyer_vol = tv - seller_vol
            else:
                buyer_vol = tv * 0.5
                seller_vol = tv * 0.5

        data_m1.at[data_m1.index[i], 'Buyer_Volume'] = buyer_vol
        data_m1.at[data_m1.index[i], 'Seller_Volume'] = seller_vol
    return data_m1

def decide_action(data, min_ratio_change=1.618033):
    if len(data) < 4:
        return 'hold'
    last_buyer = data['Buyer_Volume'].iloc[-2]
    last_seller = data['Seller_Volume'].iloc[-2]
    prev_buyer = data['Buyer_Volume'].iloc[-3]
    prev_seller = data['Seller_Volume'].iloc[-3]
    prev_buyer3 = data['Buyer_Volume'].iloc[-4]
    prev_seller3 = data['Seller_Volume'].iloc[-4]

    if prev_seller == 0:
        prev_seller = 1.618033e-9
    if last_seller == 0:
        last_seller = 1.618033e-9

    prev_ratio = prev_buyer / prev_seller
    last_ratio = last_buyer / last_seller
    prev_ratio3 = prev_buyer3 / (prev_seller3 if prev_seller3 != 0 else 1.618033e-9)
    last_ratio3 = prev_buyer / (prev_seller if prev_seller != 0 else 1.618033e-9)

    if last_ratio > prev_ratio * min_ratio_change and last_ratio3 > prev_ratio3 * min_ratio_change:
        return 'buy'
    if last_ratio * min_ratio_change < prev_ratio and last_ratio3 * min_ratio_change < prev_ratio3:
        return 'sell'
    return 'hold'

def execute_simulated_trade(action, current_price, spread, next_close):
    global simulation_mode, simulated_balance, simulated_gains, simulated_trades
    global simulated_current_position, simulated_entry_price, consecutive_losses, simulated_entry_time

    if action == 'buy':
        if simulated_current_position is None:
            simulated_entry_price = current_price + spread
            simulated_current_position = 'buy'
            simulated_entry_time = datetime.datetime.now()
            print(f"Position simulée BUY ouverte à {simulated_entry_price}")
        elif simulated_current_position == 'sell':
            print("Clôture de la position simulée SELL avant d'ouvrir une position simulée BUY")
            if close_simulated_position(current_price, spread):
                simulated_entry_price = current_price + spread
                simulated_current_position = 'buy'
                simulated_entry_time = datetime.datetime.now()
                print(f"Position simulée BUY ouverte à {simulated_entry_price}")
    elif action == 'sell':
        if simulated_current_position is None:
            simulated_entry_price = current_price - spread
            simulated_current_position = 'sell'
            simulated_entry_time = datetime.datetime.now()
            print(f"Position simulée SELL ouverte à {simulated_entry_price}")
        elif simulated_current_position == 'buy':
            print("Clôture de la position simulée BUY avant d'ouvrir une position simulée SELL")
            if close_simulated_position(current_price, spread):
                simulated_entry_price = current_price - spread
                simulated_current_position = 'sell'
                simulated_entry_time = datetime.datetime.now()
                print(f"Position simulée SELL ouverte à {simulated_entry_price}")
    elif action == 'close':
        close_simulated_position(current_price, spread)

def close_simulated_position(current_price, spread):
    global simulation_mode, simulated_balance, simulated_gains, simulated_trades
    global simulated_current_position, simulated_entry_price, consecutive_losses, simulated_entry_time

    if simulated_current_position is not None:
        if simulated_current_position == 'buy':
            exit_price = current_price - spread
            profit = (exit_price - simulated_entry_price) * 0.01
        elif simulated_current_position == 'sell':
            exit_price = current_price + spread
            profit = (simulated_entry_price - exit_price) * 0.01

        simulated_balance += profit
        trade = {
            'entry_time': simulated_entry_time,
            'exit_time': datetime.datetime.now(),
            'position': simulated_current_position,
            'entry_price': simulated_entry_price,
            'exit_price': exit_price,
            'profit': profit,
            'balance': simulated_balance
        }
        simulated_trades.append(trade)

        clear_console()
        print(ascii_art)

        if profit > 0:
            simulated_gains += 1
            print(f"Trade simulé gagnant : {trade}")
            if simulated_gains >= 1:
                simulation_mode = False
                simulated_gains = 0
                consecutive_losses = 0
                print("1 gain simulé atteint. Retour en mode réel.")
        else:
            simulated_gains = 0
            print(f"Trade simulé perdant : {trade}")

        simulated_current_position = None
        simulated_entry_price = 0.0
        return True
    else:
        print("Aucune position simulée ouverte à clôturer.")
        return False

def get_last_closed_bar():
    # Récupère la dernière bougie clôturée (position 1)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, 1)
    if rates is not None and len(rates) > 0:
        return rates[0]
    return None

def main():
    global current_position, entry_price, simulation_mode, simulated_balance, simulated_gains, consecutive_losses
    global simulated_current_position, simulated_entry_price, simulated_entry_time

    if not mt5.initialize():
        print("Échec de l'initialisation de MetaTrader5")
        mt5.shutdown()
        return

    account_info = mt5.account_info()
    if account_info is None:
        print("Échec de la récupération des informations du compte")
        return

    print("Informations du compte :", account_info)
    balance = get_account_balance()
    if balance is not None:
        print(f"Solde initial du compte : {balance}")

    last_bar_time = None

    try:
        clear_console()
        print("Démarrage du script...")

        while True:
            bar = get_last_closed_bar()
            if bar is not None:
                bar_time = datetime.datetime.utcfromtimestamp(bar['time']).replace(tzinfo=pytz.utc)
                if bar_time != last_bar_time:
                    # Nouvelle bougie détectée
                    clear_console()
                    print(f"Nouvelle bougie détectée à {bar_time}, close={bar['close']}")
                    last_bar_time = bar_time

                    # Récupérer toutes les données maintenant
                    data_m1 = get_data(timeframe, nb_candles)
                    if data_m1 is None or data_m1.empty:
                        print("Pas de données disponibles, réessai plus tard.")
                    else:
                        data_m1 = build_volume_dataframe(data_m1)
                        if len(data_m1) >= 4:
                            action = decide_action(data_m1, min_ratio_change=min_ratio_change)
                            print(f"Action décidée : {action}")

                            # Récupération du spread actuel
                            tick = mt5.symbol_info_tick(symbol)
                            if tick is not None:
                                spread = (tick.ask - tick.bid) / 2
                            else:
                                spread = 0.0

                            # Logique d'exécution en fonction du mode
                            latest_closed_bar = data_m1.iloc[-2]
                            current_price = latest_closed_bar['close']

                            if simulation_mode:
                                if action in ['buy', 'sell']:
                                    simulated_entry_time = bar_time
                                    execute_simulated_trade(action, current_price, spread, current_price)
                            else:
                                if action == 'buy':
                                    if current_position == 'sell':
                                        close_order()
                                    if current_position != 'buy':
                                        open_order('buy')
                                elif action == 'sell':
                                    if current_position == 'buy':
                                        close_order()
                                    if current_position != 'sell':
                                        open_order('sell')
                                elif action == 'close':
                                    if current_position is not None:
                                        close_order()

            # Polling fréquent
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Script interrompu par l'utilisateur")
    finally:
        if current_position is not None:
            data_m1 = get_data(timeframe, 1)
            if data_m1 is not None and not data_m1.empty:
                latest_closed_bar = data_m1.iloc[-1]
                current_price = latest_closed_bar['close']
                spread = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid)/2 if mt5.symbol_info_tick(symbol) else 0.0
                close_order()
        mt5.shutdown()
        print("Connexion à MetaTrader5 fermée.")
        if simulated_trades:
            print("\n=== Historique des trades simulés ===")
            for trade in simulated_trades:
                print(trade)

if __name__ == "__main__":
    main()
