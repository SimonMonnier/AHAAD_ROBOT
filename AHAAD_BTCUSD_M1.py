import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import pytz
import pandas_ta as pta  # Changement d'alias pour éviter les conflits
import time
import os

# ASCII Art d'un robot trader Bitcoin

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
... # Make with love by Mister Robot # ...⠀
"""

print(ascii_art)
time.sleep(2)

def clear_console():
    # Efface la console en fonction du système d'exploitation
    os.system('cls' if os.name == 'nt' else 'clear')

# Initialiser la connexion à MetaTrader 5
if not mt5.initialize():
    print("Échec de l'initialisation de MetaTrader5")
    mt5.shutdown()
    exit()

# Paramètres
symbol = "BTCUSD"
timeframe = mt5.TIMEFRAME_M1
nb_candles = 100000  # Nombre de bougies à récupérer

# Variables pour les positions réelles
current_position = None  # 'buy', 'sell' ou None
entry_price = 0.0

# Variables pour la gestion de la simulation
simulation_mode = False
simulated_trades = []
simulated_balance = 100  # Solde initial simulé
simulated_gains = 0  # Compteur de gains simulés
consecutive_losses = 0  # Compteur de pertes réelles consécutives

# Variables pour la gestion des positions simulées
simulated_current_position = None  # 'buy', 'sell' ou None
simulated_entry_price = 0.0

# Variables supplémentaires pour la gestion des trades simulés
latest_close_price = 0.0
spread = 0.0
simulated_entry_time = None

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
    # Convertir en DataFrame pandas
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')
    data.set_index('time', inplace=True)
    return data

def check_existing_position():
    global current_position, entry_price
    positions = mt5.positions_get(symbol=symbol)
    if positions and len(positions) > 0:
        pos = positions[0]  # Supposant une seule position
        if pos.type == mt5.POSITION_TYPE_BUY:
            current_position = 'buy'
            entry_price = pos.price_open
            print(f"Position réelle BUY détectée ouverte à {entry_price}")
        elif pos.type == mt5.POSITION_TYPE_SELL:
            current_position = 'sell'
            entry_price = pos.price_open
            print(f"Position réelle SELL détectée ouverte à {entry_price}")
        else:
            print("Type de position réel inconnu détecté.")
            current_position = None
            entry_price = 0.0
    else:
        print("Aucune position réelle ouverte détectée.")
        current_position = None
        entry_price = 0.0

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
    # Calculer la taille du lot en fonction du solde
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
        "magic": 3,
        "comment": f"Python script open {order_type}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    # Envoyer la requête
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Échec de l'envoi de l'ordre {order_type}, retcode =", result.retcode)
    else:
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
    pos = positions[0]  # Supposant une seule position
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
        "magic": 3,
        "comment": f"Python script close {current_position}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Échec de la clôture de la position {current_position}, retcode =", result.retcode)
    else:
        print(f"Position {current_position} clôturée au prix {price}")
        # Calculer le profit réel
        if current_position == 'buy':
            profit = (price - entry_price) * 0.01  # Taille de position fixe (0.01)
        elif current_position == 'sell':
            profit = (entry_price - price) * 0.01
        else:
            profit = 0.0
        clear_console()
        print(ascii_art)

        if profit > 0:
            print(f"Trade réel gagnant")
            consecutive_losses = 0  # Réinitialiser les pertes consécutives
        else:
            print(f"Trade réel perdant")
            consecutive_losses += 1
            # Vérifier si 3 pertes consécutives sont atteintes pour activer le mode simulation
            if consecutive_losses >= 3:
                simulation_mode = True
                simulated_gains = 0  # Réinitialiser le compteur de gains simulés
                print("3 pertes consécutives atteintes. Passage en mode simulation.")
        # Réinitialiser la position
        current_position = None
        entry_price = 0.0

class IchimokuStrategy:
    def __init__(self):
        pass

    def calculate_indicators(self, data):
        data = data.copy(deep=True)  # Assurer une copie profonde
        data = data.dropna()
        # Calcul des EMA
        data['EMA20'] = data['close'].ewm(span=20, adjust=False).mean()
        data['EMA50'] = data['close'].ewm(span=50, adjust=False).mean()
        data = data.dropna()
        # Calcul de l'ATR14
        data['TR'] = np.maximum(
            (data['high'] - data['low']),
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        data = data.dropna()
        data['ATR14'] = data['TR'].rolling(window=14).mean()
        data = data.dropna()
        # Calcul du RSI
        data['RSI14'] = pta.rsi(data['close'], length=14)
        data = data.dropna()
        # Calcul de l'Ichimoku
        data.ta.ichimoku(append=True)
        data = data.dropna()

        ichimoku_columns = {
            'ISA_9': 'ICHIMOKU_Senkou_A',
            'ISB_26': 'ICHIMOKU_Senkou_B',
            'ITS_9': 'ICHIMOKU_Tenkan',
            'IKS_26': 'ICHIMOKU_Kijun',
            'ICS_26': 'ICHIMOKU_Chikou'
        }
        data = data.rename(columns=ichimoku_columns)

        required_columns = ['ICHIMOKU_Senkou_A', 'ICHIMOKU_Senkou_B', 'ICHIMOKU_Tenkan', 'ICHIMOKU_Kijun', 'ICHIMOKU_Chikou']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            print(f"Erreur : Les colonnes Ichimoku manquent : {missing_columns}")
            raise KeyError(f"Les colonnes Ichimoku manquent : {missing_columns}")

        data.loc[:, 'ATR_Mean'] = data['ATR14'].rolling(window=100).mean()
        adx = pta.adx(data['high'], data['low'], data['close'], length=14)
        data = pd.concat([data, adx], axis=1)
        data.loc[:, 'Consolidation'] = np.where((data['ATR14'] < (data['ATR_Mean'] * 0.618033)) & (data['ADX_14'] < 20), 1, 0)

        data = data.dropna()
        conditions = [
            (data['EMA20'] > data['EMA50']) &
            (data['Consolidation'] == 0) &
            (data['RSI14'] > 40) &
            (data['close'] > data['ICHIMOKU_Senkou_A']) &
            (data['ICHIMOKU_Chikou'] > data['close']),

            (data['EMA20'] < data['EMA50']) &
            (data['Consolidation'] == 0) &
            (data['RSI14'] < 60) &
            (data['close'] < data['ICHIMOKU_Senkou_B']) &
            (data['ICHIMOKU_Chikou'] < data['close']),

            (data['Consolidation'] == 1)
        ]
        choices = ['Tendance Haussière', 'Tendance Baissière', 'Consolidation']
        data['Market State'] = np.select(conditions, choices, default='Indéterminé')

        data['Trend_Consecutive'] = data['Market State'].ne(data['Market State'].shift()).cumsum()
        data['Trend_Consecutive'] = data.groupby('Trend_Consecutive').cumcount() + 1

        return data

    def decide_action(self, data, min_consecutive=7):
        global consecutive_losses, simulation_mode, simulated_gains
        current_state = data['Market State'].iloc[-1]
        current_consecutive = data['Trend_Consecutive'].iloc[-1]
        clear_console()
        print(ascii_art)

        print(f"État du marché : {current_state}, Consécutif : {current_consecutive}")
        if current_state == 'Tendance Haussière' and current_consecutive >= min_consecutive:
            return 'buy'
        elif current_state == 'Tendance Baissière' and current_consecutive >= min_consecutive:
            return 'sell'
        elif current_state == 'Consolidation':
            return 'close'
        else:
            return 'hold'

# Instancier la stratégie Ichimoku
ichimoku_strategy = IchimokuStrategy()

def execute_simulated_trade(action, current_price, spread, next_close):
    global simulation_mode, simulated_balance, simulated_gains, simulated_trades
    global simulated_current_position, simulated_entry_price, consecutive_losses

    if action == 'buy':
        if simulated_current_position is None:
            simulated_entry_price = current_price + spread
            simulated_current_position = 'buy'
            print(f"Position simulée BUY ouverte à {simulated_entry_price}")
        elif simulated_current_position == 'sell':
            print("Clôture de la position simulée SELL avant d'ouvrir une position simulée BUY")
            if close_simulated_position(current_price, spread):
                simulated_entry_price = current_price + spread
                simulated_current_position = 'buy'
                print(f"Position simulée BUY ouverte à {simulated_entry_price}")
    elif action == 'sell':
        if simulated_current_position is None:
            simulated_entry_price = current_price - spread
            simulated_current_position = 'sell'
            print(f"Position simulée SELL ouverte à {simulated_entry_price}")
        elif simulated_current_position == 'buy':
            print("Clôture de la position simulée BUY avant d'ouvrir une position simulée SELL")
            if close_simulated_position(current_price, spread):
                simulated_entry_price = current_price - spread
                simulated_current_position = 'sell'
                print(f"Position simulée SELL ouverte à {simulated_entry_price}")
    elif action == 'close':
        close_simulated_position(current_price, spread)
    else:
        return

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
            print(f"Trade simulé gagnant {simulated_gains}/2 : {trade}")
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
    global simulated_current_position, simulated_entry_price
    global latest_close_price, spread, simulated_entry_time

    account_info = mt5.account_info()
    if account_info is None:
        print("Échec de la récupération des informations du compte")
        return

    print("Informations du compte :", account_info)

    balance = get_account_balance()
    if balance is not None:
        print(f"Solde initial du compte : {balance}")

    check_existing_position()

    last_bar_time = None

    try:
        while True:
            # Détection de la nouvelle bougie via get_last_closed_bar
            bar = get_last_closed_bar()
            if bar is not None:
                bar_time = datetime.datetime.utcfromtimestamp(bar['time']).replace(tzinfo=pytz.utc)
                if bar_time != last_bar_time:
                    # Nouvelle bougie détectée
                    print(f"Nouvelle bougie détectée à {bar_time}")
                    last_bar_time = bar_time

                    # Récupérer les données complètes maintenant que la nouvelle bougie est apparue
                    data_m1 = get_data(timeframe, nb_candles)
                    if data_m1 is None or data_m1.empty:
                        print("Pas de données disponibles, réessai plus tard.")
                    else:
                        # Récupération du spread et du prix de clôture de la dernière bougie fermée
                        latest_closed_bar = data_m1.iloc[-2]
                        latest_close_price = latest_closed_bar['close']
                        tick = mt5.symbol_info_tick(symbol)
                        if tick is not None:
                            spread = (tick.ask - tick.bid) / 2
                        else:
                            spread = 0.0

                        try:
                            data_with_indicators = ichimoku_strategy.calculate_indicators(data_m1)
                            action = ichimoku_strategy.decide_action(data_with_indicators, min_consecutive=7)
                        except KeyError as e:
                            print(f"Erreur lors du calcul des indicateurs : {e}")
                            action = 'hold'

                        print(f"Action décidée : {action}")
                        if simulation_mode:
                            if action in ['buy', 'sell']:
                                simulated_entry_time = bar_time
                                execute_simulated_trade(action, latest_closed_bar['close'], spread, latest_close_price)
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
                            # 'hold' ne nécessite aucune action

            # Polling fréquent (0.1 seconde)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Script interrompu par l'utilisateur")
    finally:
        if current_position is not None:
            data_m1 = get_data(timeframe, 1)
            if data_m1 is not None and not data_m1.empty:
                latest_closed_bar = data_m1.iloc[-1]
                current_price = latest_closed_bar['close']
                if mt5.symbol_info_tick(symbol) is not None:
                    spread = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid) / 2
                else:
                    spread = 0.0
                close_order()
        mt5.shutdown()
        print("Connexion à MetaTrader5 fermée.")
        if simulated_trades:
            print("\n=== Historique des trades simulés ===")
            for trade in simulated_trades:
                print(trade)

if __name__ == "__main__":
    main()
