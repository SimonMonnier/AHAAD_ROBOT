import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import pytz
import pandas_ta as pta  # Changement d'alias pour éviter les conflits
import time

# Initialiser la connexion à MetaTrader 5
if not mt5.initialize():
    print("Échec de l'initialisation de MetaTrader5")
    mt5.shutdown()
    exit()

# Paramètres
symbol = "BTCUSD"
timeframe = mt5.TIMEFRAME_M1
nb_candles = 1000  # Nombre de bougies à récupérer

# Variables pour les positions
current_position = None  # 'buy', 'sell' ou None
entry_price = 0.0

# Variables pour la gestion de la simulation
simulation_mode = False
simulated_trades = []
simulated_balance = 100  # Solde initial simulé
simulated_gains = 0  # Compteur de gains simulés
consecutive_losses = 0  # Compteur de pertes réelles consécutives

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

# Fonctions pour l'exécution des ordres
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
    if lot > 100:
        lot = 100
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
        "magic": 234000,
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

def close_order(current_price, spread):
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
        "magic": 234000,
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
        if profit > 0:
            print(f"Trade réel gagnant : Profit = {profit:.2f}")
            consecutive_losses = 0  # Réinitialiser les pertes consécutives
        else:
            print(f"Trade réel perdant : Perte = {abs(profit):.2f}")
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
        # Calcul de l'Ichimoku avec append=True via l'accesseur DataFrame
        data.ta.ichimoku(append=True)
        data = data.dropna()
        # Debug : Vérifier les colonnes après l'ajout d'Ichimoku
        #print("Colonnes après l'ajout d'Ichimoku :", data.columns)

        # Renommer les colonnes Ichimoku pour correspondre aux noms attendus
        ichimoku_columns = {
            'ISA_9': 'ICHIMOKU_Senkou_A',
            'ISB_26': 'ICHIMOKU_Senkou_B',
            'ITS_9': 'ICHIMOKU_Tenkan',
            'IKS_26': 'ICHIMOKU_Kijun',
            'ICS_26': 'ICHIMOKU_Chikou'
        }
        data = data.rename(columns=ichimoku_columns)  # Éviter inplace=True

        # Debug : Vérifier les colonnes après renommage
        #print("Colonnes après renommage Ichimoku :", data.columns)

        # Vérifier si les colonnes Ichimoku ont été ajoutées
        required_columns = ['ICHIMOKU_Senkou_A', 'ICHIMOKU_Senkou_B', 'ICHIMOKU_Tenkan', 'ICHIMOKU_Kijun', 'ICHIMOKU_Chikou']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            print(f"Erreur : Les colonnes Ichimoku manquent : {missing_columns}")
            raise KeyError(f"Les colonnes Ichimoku manquent : {missing_columns}")

        # Définir le seuil de consolidation
        data.loc[:, 'ATR_Mean'] = data['ATR14'].rolling(window=100).mean()  # Utiliser .loc
        data.loc[:, 'Consolidation'] = np.where(data['ATR14'] < (data['ATR_Mean'] * 0.01618033), 1, 0)  # Utiliser .loc

        # Déterminer l'état du marché avec des conditions de confirmation, incluant le Chikou Span
        conditions = [
            (data['EMA20'] > data['EMA50']) & 
            (data['Consolidation'] == 0) & 
            (data['RSI14'] > 40) & 
            (data['close'] > data['ICHIMOKU_Senkou_A']) &
            #(data['close'] > data['ICHIMOKU_Senkou_B']) &
            (data['ICHIMOKU_Chikou'] > data['close']),  # Filtre Chikou Span pour buy

            (data['EMA20'] < data['EMA50']) & 
            (data['Consolidation'] == 0) & 
            (data['RSI14'] < 60) & 
            #(data['close'] < data['ICHIMOKU_Senkou_A']) &
            (data['close'] < data['ICHIMOKU_Senkou_B']) &
            (data['ICHIMOKU_Chikou'] < data['close']),  # Filtre Chikou Span pour sell

            (data['Consolidation'] == 1)
        ]
        choices = ['Tendance Haussière', 'Tendance Baissière', 'Consolidation']
        data['Market State'] = np.select(conditions, choices, default='Indéterminé')

        # Compter les bougies consécutives dans la tendance
        data['Trend_Consecutive'] = data['Market State'].ne(data['Market State'].shift()).cumsum()
        data['Trend_Consecutive'] = data.groupby('Trend_Consecutive').cumcount() + 1

        return data

    def decide_action(self, data, min_consecutive=14):
        global consecutive_losses, simulation_mode, simulated_gains
        # Utiliser uniquement les données disponibles jusqu'à l'instant présent
        current_state = data['Market State'].iloc[-1]
        current_consecutive = data['Trend_Consecutive'].iloc[-1]
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
    simulated_profit = 0.0
    entry_price_sim = 0.0
    exit_price_sim = 0.0

    if action == 'buy':
        entry_price_sim = current_price + spread
        exit_price_sim = next_close - spread
        simulated_profit = (exit_price_sim - entry_price_sim) * 0.01  # Taille de position fixe
    elif action == 'sell':
        entry_price_sim = current_price - spread
        exit_price_sim = next_close + spread
        simulated_profit = (entry_price_sim - exit_price_sim) * 0.01
    elif action == 'close':
        # Simuler la clôture sans profit ou selon la position actuelle
        simulated_profit = 0.0
        # Pour simplifier, on ne gère pas le profit ici
    else:
        return  # 'hold' ne nécessite aucune action

    simulated_balance += simulated_profit
    trade = {
        'entry_time': datetime.datetime.now(),
        'exit_time': datetime.datetime.now(),
        'position': action,
        'entry_price': entry_price_sim,
        'exit_price': exit_price_sim,
        'profit': simulated_profit,
        'balance': simulated_balance
    }
    simulated_trades.append(trade)

    if simulated_profit > 0:
        simulated_gains += 1
        print(f"Trade simulé gagnant {simulated_gains}/2 : {trade}")
        if simulated_gains >= 2:
            simulation_mode = False  # Sortir du mode simulation après 2 gains
            simulated_gains = 0  # Réinitialiser le compteur de gains simulés
            consecutive_losses = 0  # Réinitialiser les pertes réelles
            print("2 gains simulés atteints. Retour en mode réel.")
    else:
        simulated_gains = 0  # Réinitialiser le compteur si un trade simulé est perdant
        print(f"Trade simulé perdant : {trade}")
        # Continuer en mode simulation jusqu'à atteindre 2 gains simulés

def main():
    global current_position, entry_price, simulation_mode, simulated_balance, simulated_gains, consecutive_losses
    try:
        account_info = mt5.account_info()
        if account_info is None:
            print("Échec de la récupération des informations du compte")
            return

        print("Informations du compte :", account_info)

        # Afficher le solde initial du compte
        balance = get_account_balance()
        if balance is not None:
            print(f"Solde initial du compte : {balance}")

        # Initialiser la dernière barre traitée
        last_bar_time = None

        while True:
            # Récupérer les dernières bougies fermées (exclure la bougie en formation)
            data_m1 = get_data(timeframe, nb_candles)
            if data_m1 is None or data_m1.empty:
                print("Pas de données disponibles, réessai dans 10 secondes.")
                time.sleep(10)
                continue

            # Sélectionner la dernière bougie fermée
            latest_closed_bar = data_m1.iloc[-2]  # Bougie fermée
            latest_closed_time = latest_closed_bar.name

            # Vérifier si cette bougie a déjà été traitée
            if last_bar_time != latest_closed_time:
                print(f"Nouvelle bougie détectée à {latest_closed_time}")
                last_bar_time = latest_closed_time

                # Calculer les indicateurs et décider de l'action
                try:
                    data_with_indicators = ichimoku_strategy.calculate_indicators(data_m1)
                    action = ichimoku_strategy.decide_action(data_with_indicators, min_consecutive=14)
                except KeyError as e:
                    print(f"Erreur lors du calcul des indicateurs : {e}")
                    action = 'hold'

                print(f"Action décidée : {action}")

                # Exécuter l'action
                if simulation_mode:
                    if action in ['buy', 'sell', 'close']:
                        # Simuler le trade
                        next_close = data_m1.iloc[-1]['close']  # Le prix de clôture suivant
                        spread = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid) / 2  # Approximation du spread
                        execute_simulated_trade(action, latest_closed_bar['close'], spread, next_close)
                else:
                    if action == 'buy':
                        if current_position != 'sell':
                            close_order(current_price, spread)
                        if current_position != 'buy':
                            open_order('buy')
                    elif action == 'sell':
                        if current_position != 'buy':
                            close_order(current_price, spread)
                        if current_position != 'sell':
                            open_order('sell')
                    elif action == 'close':
                        if current_position is not None:
                            # Clôturer la position avec le dernier prix de clôture
                            current_price = latest_closed_bar['close']
                            spread = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid) / 2  # Approximation du spread
                            close_order(current_price, spread)
                    # 'hold' ne nécessite aucune action

            else:
                # Aucune nouvelle bougie, attendre avant de vérifier à nouveau
                time.sleep(1)  # Attendre 1 seconde avant de vérifier à nouveau

    except KeyboardInterrupt:
        print("Script interrompu par l'utilisateur")
    finally:
        # Clôturer les positions ouvertes
        if current_position is not None:
            # Clôturer la position avec le dernier prix de clôture disponible
            data_m1 = get_data(timeframe, 1)
            if data_m1 is not None and not data_m1.empty:
                latest_closed_bar = data_m1.iloc[-1]
                current_price = latest_closed_bar['close']
                spread = (mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid) / 2  # Approximation du spread
                close_order(current_price, spread)
        mt5.shutdown()
        print("Connexion à MetaTrader5 fermée.")
        # Afficher les trades simulés
        if simulated_trades:
            print("\n=== Historique des trades simulés ===")
            for trade in simulated_trades:
                print(trade)

if __name__ == "__main__":
    main()
