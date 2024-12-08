import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# ---------------------------------------
# Initialisation de MetaTrader 5
# ---------------------------------------
if not mt5.initialize():
    print("Échec de l'initialisation de MetaTrader5")
    mt5.shutdown()
    exit()

symbol = 'BTCUSD'

# Vérifier si le symbole est disponible
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(f"Le symbole {symbol} n'est pas trouvé, veuillez vérifier le nom.")
    mt5.shutdown()
    exit()

if not symbol_info.visible:
    print(f"Le symbole {symbol} n'est pas visible, tentative pour le rendre visible.")
    if not mt5.symbol_select(symbol, True):
        print(f"Impossible de sélectionner le symbole {symbol}, arrêt du script.")
        mt5.shutdown()
        exit()

# Définir la période de backtest
timezone = pytz.timezone("Etc/UTC")
start_date = datetime(2024, 1, 1, tzinfo=timezone)
end_date = datetime(2024, 12, 8, tzinfo=timezone)

# ---------------------------------------
# Fonctions pour récupérer les données M1
# ---------------------------------------
def get_m1_data(symbol, start, end):
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) == 0:
        print("Échec de la récupération des données M1.")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def build_volume_dataframe(data_m1):
    """
    Calcule Buyer_Volume et Seller_Volume à partir d'une heuristique basée sur la forme de la bougie.
    """
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
                # Bougie haussière
                buyer_factor = (body_ratio + close_pos) / 2
                buyer_vol = tv * buyer_factor
                seller_vol = tv - buyer_vol
            elif c < o:
                # Bougie baissière
                seller_factor = (body_ratio + (1 - close_pos)) / 2
                seller_vol = tv * seller_factor
                buyer_vol = tv - seller_vol
            else:
                # Neutre
                buyer_vol = tv * 0.5
                seller_vol = tv * 0.5

        data_m1.at[data_m1.index[i], 'Buyer_Volume'] = buyer_vol
        data_m1.at[data_m1.index[i], 'Seller_Volume'] = seller_vol

    return data_m1

def decide_action(data, min_ratio_change=1.618033):
    if len(data) < 2:
        return 'hold'

    last_buyer = data['Buyer_Volume'].iloc[-1]
    last_seller = data['Seller_Volume'].iloc[-1]
    prev_buyer = data['Buyer_Volume'].iloc[-2]
    prev_seller = data['Seller_Volume'].iloc[-2]

    prev_buyer3 = data['Buyer_Volume'].iloc[-3]
    prev_seller3 = data['Seller_Volume'].iloc[-3]

    if prev_seller == 0:
        prev_seller = 1.618033e-9
    if last_seller == 0:
        last_seller = 1.618033e-9

    prev_ratio = prev_buyer / prev_seller
    last_ratio = last_buyer / last_seller

    prev_ratio3 = prev_buyer3 / prev_seller3
    last_ratio3 = prev_buyer / prev_seller

    if last_ratio > prev_ratio * min_ratio_change and last_ratio3 > prev_ratio3 * min_ratio_change:
        return 'buy'
    if last_ratio * min_ratio_change < prev_ratio and last_ratio3 * min_ratio_change < prev_ratio3:
        return 'sell'
    return 'hold'


class AdvancedBacktest:
    def __init__(self, data_m1, symbol, initial_balance=100, stop_balance=500):
        self.data_m1 = data_m1
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.stop_balance = stop_balance
        self.position = None
        self.entry_price = 0.0
        self.entry_time = None
        self.position_size = 0.01
        self.trades = []
        self.equity_curve = []

        # Métriques
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
        self.highest_balance = initial_balance

    def update_position_size(self):
        symbol_info = mt5.symbol_info(self.symbol)
        self.position_size = float("{:.2f}".format(self.balance * 0.0001))
        if symbol_info is not None:
            if self.position_size > symbol_info.volume_max:
                self.position_size = symbol_info.volume_max

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
            'final_balance': self.balance
        }
        return metrics

    def print_metrics(self, time):
        metrics = self.get_metrics()
        print(f"=== Métriques après clôture de la position à {time} ===")
        print(f"Total des trades : {metrics['total_trades']}")
        print(f"Trades gagnants : {metrics['win_trades']}")
        print(f"Trades perdants : {metrics['loss_trades']}")
        print(f"Gain total : {metrics['total_gain']:.2f}")
        print(f"Perte totale : {metrics['total_loss']:.2f}")
        print(f"Profit net : {metrics['net_profit']:.2f}")
        print(f"Max de gains consécutifs : {metrics['max_consecutive_wins']}")
        print(f"Max de pertes consécutives : {metrics['max_consecutive_losses']}")
        print(f"Max Drawdown : {self.max_drawdown * 100:.2f}%")
        print(f"Solde actuel : {self.balance:.2f}\n")

    def close_position(self, price, time):
        if self.position is None:
            return
        if self.position == 'buy':
            profit = (price - self.entry_price) * self.position_size
        else:
            profit = (self.entry_price - price) * self.position_size

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

        self.trades.append({
            'entry_time': self.entry_time,
            'exit_time': time,
            'position': self.position,
            'entry_price': self.entry_price,
            'exit_price': price,
            'profit': profit,
            'balance': self.balance
        })

        # Afficher les métriques après clôture
        self.print_metrics(time)

        self.position = None
        self.entry_price = 0.0
        self.entry_time = None

    def open_position(self, direction, price, time):
        self.position = direction
        self.entry_price = price
        self.entry_time = time
        self.update_position_size()

    def run(self):
        for i in range(len(self.data_m1)):
            current_time = self.data_m1.index[i]
            current_price = self.data_m1['close'].iloc[i]

            action = decide_action(self.data_m1.iloc[:i+3])

            if action == 'buy':
                if self.position == 'sell':
                    self.close_position(current_price, current_time)
                if self.position != 'buy':
                    self.open_position('buy', current_price, current_time)

            elif action == 'sell':
                if self.position == 'buy':
                    self.close_position(current_price, current_time)
                if self.position != 'sell':
                    self.open_position('sell', current_price, current_time)

            # Calcul de l'équité
            if self.position is not None:
                if self.position == 'buy':
                    floating_pnl = (current_price - self.entry_price) * self.position_size
                else:
                    floating_pnl = (self.entry_price - current_price) * self.position_size
            else:
                floating_pnl = 0.0
            equity = self.balance + floating_pnl
            self.equity_curve.append({'time': current_time, 'equity': equity})

            if equity <= self.stop_balance:
                print("Stop loss global atteint, arrêt du backtest.")
                if self.position is not None:
                    self.close_position(current_price, current_time)
                break

        # Clôturer toute position restante à la fin du backtest
        if self.position is not None:
            self.close_position(self.data_m1['close'].iloc[-1], self.data_m1.index[-1])

def main():
    data_m1 = get_m1_data(symbol, start_date, end_date)
    if data_m1 is None:
        mt5.shutdown()
        return

    # Calcul du Buyer_Volume et Seller_Volume à partir de l'heuristique
    data_m1 = build_volume_dataframe(data_m1)

    # Lancement du backtest
    bt = AdvancedBacktest(data_m1=data_m1, symbol=symbol, initial_balance=100, stop_balance=75)
    bt.run()

    # Obtenir les métriques finales
    metrics = bt.get_metrics()

    # Affichage des résultats finaux
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
    trades_df = pd.DataFrame(bt.trades)
    print("\n=== Historique des trades ===")
    print(trades_df)

    mt5.shutdown()
    print("Backtest terminé.")


if __name__ == "__main__":
    main()
