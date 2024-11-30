import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import matplotlib.pyplot as plt
import pandas_ta as pta  # Changement d'alias pour éviter les conflits

# Initialiser la connexion à MetaTrader 5
if not mt5.initialize():
    print("Échec de l'initialisation de MetaTrader5")
    mt5.shutdown()
    exit()

# Définir le symbole et les timeframes
symbol = 'BTCUSD'
timeframe_m1 = mt5.TIMEFRAME_M1

# Définir la période de backtest
timezone = pytz.timezone("Etc/UTC")
start_date = datetime(2024, 11, 16, tzinfo=timezone)
end_date = datetime(2024, 11, 30, tzinfo=timezone)

# Vérifier si le symbole est disponible
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(f"Le symbole {symbol} n'est pas trouvé, veuillez vérifier le nom.")
    mt5.shutdown()
    exit()

if not symbol_info.visible:
    print(f"Le symbole {symbol} n'est pas visible, nous essayons de le rendre visible.")
    if not mt5.symbol_select(symbol, True):
        print(f"Impossible de sélectionner le symbole {symbol}, arrêt du script.")
        mt5.shutdown()
        exit()

# Fonction pour récupérer les données historiques
def get_data(symbol, timeframe, start, end):
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None or len(rates) == 0:
        print(f"Échec de la récupération des données pour le timeframe {timeframe}")
        return None
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')
    data.set_index('time', inplace=True)
    return data

# Récupérer les données historiques
data_m1 = get_data(symbol, timeframe_m1, start_date, end_date)

if data_m1 is None:
    print("Échec de la récupération des données historiques, arrêt du script.")
    mt5.shutdown()
    exit()

class Backtest:
    def __init__(self, data_m1, initial_balance=100, stop_balance=50):
        self.data_m1 = data_m1
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.stop_balance = stop_balance
        self.position = None  # 'buy', 'sell' ou None
        self.entry_price = 0.0
        self.entry_time = None
        self.position_size = 0.01  # Taille de position initiale
        self.trades = []
        self.actions = []  # Nouvelle liste pour enregistrer les actions
        self.max_drawdown = 0.0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.total_gain = 0.0
        self.total_loss = 0.0
        self.win_trades = 0
        self.loss_trades = 0
        self.total_trades = 0
        self.equity_curve = []
        self.highest_balance = initial_balance

    def calculate_indicators(self, data):
        data = data.copy()

        # Calcul des EMA
        data['EMA20'] = data['close'].ewm(span=20, adjust=False).mean()
        data['EMA50'] = data['close'].ewm(span=50, adjust=False).mean()

        # Calcul de l'ATR14
        data['TR'] = np.maximum(
            (data['high'] - data['low']),
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        data['ATR14'] = data['TR'].rolling(window=14).mean()

        # Calcul du RSI
        data['RSI14'] = pta.rsi(data['close'], length=14)

        # Calcul de l'Ichimoku avec append=True via l'accesseur DataFrame
        data.ta.ichimoku(append=True)

        # Debug : Vérifier les colonnes après l'ajout d'Ichimoku
        print("Colonnes après l'ajout d'Ichimoku :", data.columns)

        # Renommer les colonnes Ichimoku pour correspondre aux noms attendus
        ichimoku_columns = {
            'ISA_9': 'ICHIMOKU_Senkou_A',
            'ISB_26': 'ICHIMOKU_Senkou_B',
            'ITS_9': 'ICHIMOKU_Tenkan',
            'IKS_26': 'ICHIMOKU_Kijun',
            'ICS_26': 'ICHIMOKU_Chikou'
        }
        data.rename(columns=ichimoku_columns, inplace=True)

        # Debug : Vérifier les colonnes après renommage
        print("Colonnes après renommage Ichimoku :", data.columns)

        # Vérifier si les colonnes Ichimoku ont été ajoutées
        required_columns = ['ICHIMOKU_Senkou_A', 'ICHIMOKU_Senkou_B', 'ICHIMOKU_Tenkan', 'ICHIMOKU_Kijun', 'ICHIMOKU_Chikou']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            print(f"Erreur : Les colonnes Ichimoku manquent : {missing_columns}")
            raise KeyError(f"Les colonnes Ichimoku manquent : {missing_columns}")

        # Définir le seuil de consolidation
        data['ATR_Mean'] = data['ATR14'].rolling(window=100).mean()
        data['Consolidation'] = np.where(data['ATR14'] < (data['ATR_Mean'] * 0.01618033), 1, 0)

        # Déterminer l'état du marché avec des conditions de confirmation, incluant le Chikou Span
        conditions = [
            (data['EMA20'] > data['EMA50']) & 
            (data['Consolidation'] == 0) & 
            (data['RSI14'] > 50) & 
            (data['close'] > data['ICHIMOKU_Senkou_A']) &
            (data['ICHIMOKU_Chikou'] > data['close']),  # Filtre Chikou Span pour buy

            (data['EMA20'] < data['EMA50']) & 
            (data['Consolidation'] == 0) & 
            (data['RSI14'] < 50) & 
            (data['close'] < data['ICHIMOKU_Senkou_A']) &
            (data['ICHIMOKU_Chikou'] < data['close']),  # Filtre Chikou Span pour sell

            (data['Consolidation'] == 1)
        ]
        choices = ['Tendance Haussière', 'Tendance Baissière', 'Consolidation']
        data['Market State'] = np.select(conditions, choices, default='Indéterminé')

        # Compter les bougies consécutives dans la tendance
        data['Trend_Consecutive'] = data['Market State'].ne(data['Market State'].shift()).cumsum()
        data['Trend_Consecutive'] = data.groupby('Trend_Consecutive').cumcount() + 1

        return data

    def decide_action(self, data, min_consecutive=3):
        # Utiliser uniquement les données disponibles jusqu'à l'instant présent
        current_state = data['Market State'].iloc[-1]
        current_consecutive = data['Trend_Consecutive'].iloc[-1]

        if current_state == 'Tendance Haussière' and current_consecutive >= min_consecutive:
            return 'buy'
        elif current_state == 'Tendance Baissière' and current_consecutive >= min_consecutive:
            return 'sell'
        elif current_state == 'Consolidation':
            return 'close'
        else:
            return 'hold'

    def execute_action(self, action, current_price, current_time):
        if action == 'buy':
            if self.position == 'sell':
                self.close_position(current_price, current_time)
            self.update_position_size()
            if self.position != 'buy':
                self.open_position('buy', current_price, current_time)
        elif action == 'sell':
            if self.position == 'buy':
                self.close_position(current_price, current_time)
            self.update_position_size()
            if self.position != 'sell':
                self.open_position('sell', current_price, current_time)
        elif action == 'hold':
            self.close_position(current_price, current_time)
        elif action == 'close':
            self.close_position(current_price, current_time)

    def open_position(self, position_type, price, time):
        self.position = position_type
        self.entry_price = price
        self.entry_time = time
        self.update_position_size()
        print(f"Ouverture d'une position {position_type} à {price} au {time}")

    def close_position(self, price, time):
        if self.position is not None:
            profit = 0.0
            price_difference = price - self.entry_price
            if self.position == 'buy':
                profit = price_difference * self.position_size
            elif self.position == 'sell':
                profit = -price_difference * self.position_size
            self.balance += profit
            self.total_trades += 1
            if profit > 0:
                self.total_gain += profit
                self.win_trades += 1
                self.consecutive_wins += 1
                self.consecutive_losses = 0
                if self.consecutive_wins > self.max_consecutive_wins:
                    self.max_consecutive_wins = self.consecutive_wins
            else:
                self.total_loss += abs(profit)
                self.loss_trades += 1
                self.consecutive_losses += 1
                self.consecutive_wins = 0
                if self.consecutive_losses > self.max_consecutive_losses:
                    self.max_consecutive_losses = self.consecutive_losses
            # Mise à jour du drawdown
            if self.balance > self.highest_balance:
                self.highest_balance = self.balance
            drawdown = (self.highest_balance - self.balance) / self.highest_balance
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            # Enregistrer le trade
            trade = {
                'entry_time': self.entry_time,
                'exit_time': time,
                'position': self.position,
                'entry_price': self.entry_price,
                'exit_price': price,
                'profit': profit,
                'balance': self.balance
            }
            self.trades.append(trade)
            # Afficher les métriques après chaque clôture
            metrics = self.get_metrics()
            print(f"=== Métriques après clôture de la position à {time} ===")
            print(f"Type de position fermée : {self.position}")
            print(f"Profit du trade : {profit:.2f}")
            print(f"Solde actuel : {self.balance:.2f}")
            print(f"Total des trades : {metrics['total_trades']}")
            print(f"Trades gagnants : {metrics['win_trades']}")
            print(f"Trades perdants : {metrics['loss_trades']}")
            print(f"Gain total : {metrics['total_gain']:.2f}")
            print(f"Perte totale : {metrics['total_loss']:.2f}")
            print(f"Profit net : {metrics['net_profit']:.2f}")
            print(f"Max de gains consécutifs : {metrics['max_consecutive_wins']}")
            print(f"Max de pertes consécutives : {metrics['max_consecutive_losses']}")
            print(f"Max Drawdown : {self.max_drawdown * 100:.2f}%\n")
            # Réinitialiser la position
            self.position = None
            self.entry_price = 0.0
            self.entry_time = None

    def update_position_size(self):
        balance = self.balance
        self.position_size = float("{:.2f}".format(balance * 0.0001))  # 0,1% du solde

    def run_backtest(self):
        data = self.calculate_indicators(self.data_m1.copy())
        data = data.dropna()

        for i in range(len(data)):
            current_time = data.index[i]
            current_price = data['close'].iloc[i]
            current_data = data.iloc[:i+1]

            action = self.decide_action(current_data, min_consecutive=3)
            self.actions.append({'time': current_time, 'action': action})  # Enregistrer l'action

            self.execute_action(action, current_price, current_time)
            self.equity_curve.append({'time': current_time, 'balance': self.balance})

            # Calculer le P&L flottant de la position ouverte
            if self.position is not None:
                price_difference = current_price - self.entry_price
                if self.position == 'buy':
                    floating_pnl = price_difference * self.position_size
                elif self.position == 'sell':
                    floating_pnl = -price_difference * self.position_size
            else:
                floating_pnl = 0.0

            # Calculer l'équité en incluant le P&L flottant
            equity = self.balance + floating_pnl

            # Vérifier si l'équité a atteint le stop_balance
            if equity <= self.stop_balance:
                print(f"L'équité a atteint le niveau d'arrêt de {self.stop_balance} en raison d'une position ouverte. Arrêt du backtest.")
                if self.position is not None:
                    self.close_position(current_price, current_time)
                break

            # Vérifier si le solde a atteint le stop_balance après clôture de position
            if self.balance <= self.stop_balance:
                print(f"Le solde a atteint le niveau d'arrêt de {self.stop_balance}. Arrêt du backtest.")
                if self.position is not None:
                    self.close_position(current_price, current_time)
                break

        # Clôturer toute position restante à la fin du backtest
        if self.position is not None:
            self.close_position(current_price, current_time)

    def get_metrics(self):
        metrics = {
            'total_gain': self.total_gain,
            'total_loss': self.total_loss,
            'net_profit': self.total_gain - self.total_loss,
            'win_trades': self.win_trades,
            'loss_trades': self.loss_trades,
            'total_trades': self.total_trades,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'max_drawdown': self.max_drawdown,
            'final_balance': self.balance,
        }
        return metrics

def plot_backtest(data, trades, equity_curve, actions, symbol):
    plt.figure(figsize=(14, 7))

    # Tracer les prix de clôture
    plt.plot(data.index, data['close'], label='Prix de Clôture', color='black')

    # Tracer les EMA
    plt.plot(data.index, data['EMA20'], label='EMA20', color='blue')
    plt.plot(data.index, data['EMA50'], label='EMA50', color='red')

    # Tracer l'Ichimoku
    plt.plot(data.index, data['ICHIMOKU_Senkou_A'], label='Ichimoku Senkou A', color='green', linestyle='--')
    plt.plot(data.index, data['ICHIMOKU_Senkou_B'], label='Ichimoku Senkou B', color='brown', linestyle='--')

    # Tracer le RSI
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    ax2.plot(data.index, data['RSI14'], label='RSI14', color='purple', alpha=0.3)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.3)
    ax2.axhline(30, color='green', linestyle='--', alpha=0.3)
    ax2.set_ylabel('RSI')

    # Colorier le fond en fonction des actions
    for action in actions:
        action_time = action['time']
        action_type = action['action']
        if action_type == 'buy':
            color = 'lightgreen'
        elif action_type == 'sell':
            color = 'lightcoral'
        elif action_type == 'hold':
            color = 'khaki'
        elif action_type == 'close':
            color = 'lightblue'
        else:
            continue  # Ignorer les actions indéterminées

        # Tracer un rectangle sur toute la hauteur du graphique pour la bougie actuelle
        # Ajuster le padding temporel selon le timeframe
        ax1.axvspan(action_time - pd.Timedelta(minutes=0.5), action_time + pd.Timedelta(minutes=0.5), color=color, alpha=0.3)

    # Tracer les signaux d'achat et de vente
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        buy_signals = trades_df[trades_df['position'] == 'buy']
        sell_signals = trades_df[trades_df['position'] == 'sell']
        close_signals = trades_df[trades_df['position'] == 'close']

        plt.scatter(buy_signals['entry_time'], buy_signals['entry_price'], marker='^', color='g', label='Buy Signal', alpha=1)
        plt.scatter(sell_signals['entry_time'], sell_signals['entry_price'], marker='v', color='r', label='Sell Signal', alpha=1)
        plt.scatter(close_signals['exit_time'], close_signals['exit_price'], marker='o', color='b', label='Close Signal', alpha=1)

    plt.title(f"Analyse du marché {symbol} sur le laps de temps M1")
    plt.xlabel("Temps")
    plt.ylabel("Prix")
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.show()

    # Tracer l'équité
    equity_df = pd.DataFrame(equity_curve)
    plt.figure(figsize=(14, 5))
    plt.plot(equity_df['time'], equity_df['balance'], label='Équité', color='blue')
    plt.title("Équité de la stratégie")
    plt.xlabel("Temps")
    plt.ylabel("Balance")
    plt.legend()
    plt.show()

def main():
    # Initialiser le backtest
    backtest = Backtest(data_m1=data_m1, initial_balance=100, stop_balance=75)

    # Lancer le backtest avec gestion des erreurs
    try:
        backtest.run_backtest()
    except KeyError as e:
        print(f"Erreur lors du calcul des indicateurs : {e}")
        mt5.shutdown()
        exit()

    # Obtenir les métriques
    metrics = backtest.get_metrics()

    # Afficher les métriques finales
    print("=== Résultats finaux du backtest ===")
    print(f"Gain total : {metrics['total_gain']:.2f}")
    print(f"Perte totale : {metrics['total_loss']:.2f}")
    print(f"Profit net : {metrics['net_profit']:.2f}")
    print(f"Total des trades : {metrics['total_trades']}")
    print(f"Trades gagnants : {metrics['win_trades']}")
    print(f"Trades perdants : {metrics['loss_trades']}")
    print(f"Max de gains consécutifs : {metrics['max_consecutive_wins']}")
    print(f"Max de pertes consécutives : {metrics['max_consecutive_losses']}")
    print(f"Max Drawdown : {metrics['max_drawdown'] * 100:.2f}%")
    print(f"Solde final : {metrics['final_balance']:.2f}")

    # Afficher l'historique des trades
    trades_df = pd.DataFrame(backtest.trades)
    print("\n=== Historique des trades ===")
    print(trades_df)

    # Optionnel : Visualiser l'état du marché et les trades
    plot_results = True  # Mettre à True pour activer la visualisation
    if plot_results:
        try:
            data_with_indicators = backtest.calculate_indicators(backtest.data_m1.copy()).dropna()
            plot_backtest(data_with_indicators, trades_df, backtest.equity_curve, backtest.actions, symbol)
        except KeyError as e:
            print(f"Erreur lors du tracé des indicateurs : {e}")

    # Fermer la connexion à MetaTrader 5
    mt5.shutdown()
    print("Connexion à MetaTrader5 fermée.")

if __name__ == "__main__":
    main()
