Voici une version mise à jour de votre README incluant les informations sur la taille des lots :

---

# AHAAD ROBOT BTCUSD M1 MT5
<img src="BTCUSD.ico" alt="BTCUSD" width="618" height="618" />

## Introduction

Ce projet est un script Python permettant de récupérer des données de marché via MetaTrader 5, de calculer des indicateurs techniques, puis de prendre des décisions de trading (ou de simuler celles-ci) en fonction d'une stratégie basée sur Ichimoku, RSI, EMA et ATR. Il est important de noter que ce script nécessite une installation préalable de MetaTrader 5 sur votre machine, ainsi qu'un compte chez un broker compatible MetaTrader 5.

**Note :** Ce code est fourni à titre d'exemple éducatif. Le trading comporte des risques financiers importants. Utilisez ce script à vos propres risques, en mode simulation ou avec une extrême prudence pour du trading réel.

## Prérequis

- **Miniconda** (ou Anaconda)
- **Python 3.x**
- **MetaTrader 5 installé** sur votre machine
- **Un compte broker MetaTrader 5**
- Les dépendances Python listées ci-dessous

## Installation de Miniconda

1. Rendez-vous sur le site officiel de Miniconda :  
   [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html)

2. Téléchargez l'installateur correspondant à votre système d'exploitation (Windows, macOS ou Linux).

3. Installez Miniconda en suivant les instructions de l'installateur. Sur Windows, assurez-vous de cocher l'option pour ajouter conda à votre PATH, si cela vous est proposé.

## Création d'un environnement conda

Il est recommandé de créer un environnement virtuel dédié à ce projet afin d'éviter les conflits de dépendances avec d'autres projets.

1. Ouvrez un terminal ou une invite de commandes.
2. Créez un nouvel environnement, par exemple nommé `trading_env` :

   ```bash
   conda create --name trading_env python=3.9
   ```
   
   Ici, nous choisissons Python 3.9, mais vous pouvez opter pour une autre version compatible.

3. Activez l'environnement :

   ```bash
   conda activate trading_env
   ```

   Sur Windows, si l'activation ne fonctionne pas, essayez :
   
   ```bash
   source activate trading_env
   ```
   
   (Notamment sous Git Bash ou WSL).

## Installation des dépendances requises

Avant d'installer les dépendances, assurez-vous d'être dans le répertoire du projet (là où se trouve votre fichier `code.py` ou similaire).

Voici les dépendances Python nécessaires :

- `MetaTrader5`
- `pandas`
- `numpy`
- `matplotlib`
- `pytz`
- `pandas_ta`

Pour les installer :

```bash
pip install -r requirements.txt
```

## Installation de MetaTrader 5

1. Téléchargez MetaTrader 5 depuis le site officiel du broker avec lequel vous souhaitez travailler, ou via le site officiel de MetaQuotes :
   [https://www.metatrader5.com/](https://www.metatrader5.com/)

2. Installez MetaTrader 5 sur votre machine.

3. Ouvrez MetaTrader 5, connectez-vous à votre compte broker.

**Note :** Le script Python utilise la bibliothèque `MetaTrader5` pour communiquer avec le terminal MetaTrader 5 installé sur votre machine. Cette bibliothèque ne suffit pas à elle seule, il faut bien avoir le terminal MetaTrader 5 installé et configuré.

## Configuration du graphique dans MetaTrader 5

- Assurez-vous d’avoir au minimum **150 000 périodes (bougies)** chargées sur le graphique du symbole que vous tradez (par exemple BTCUSD en M1). Sans ce minimum de données, le robot peut générer des erreurs en raison d’un manque d’historique.  
- Plus vous avez de données, plus vous pourrez effectuer des tests sur une longue période (en réel ou en backtesting).

## Utilisation du programme de Trading en Temps Réel

1. Assurez-vous que votre terminal MetaTrader 5 est lancé et connecté à votre compte broker.
2. Dans votre terminal ou invite de commandes, activez l'environnement conda si ce n'est pas déjà fait :

   ```bash
   conda activate trading_env
   ```

3. Exécutez le script Python (par exemple) :

   ```bash
   python AHAAD_BTCUSD_M1.py
   ```

![AHAAD](ahaad.png)

Le script va se lancer, établir une connexion avec MetaTrader 5, récupérer les données, calculer les indicateurs, et exécuter les actions en fonction de la stratégie (en mode réel ou simulation selon les conditions du code).

### Gestion de la Taille de Lot (Exemple de Progressivité)

- La taille de lot commence à **0.01** pour un solde d’environ **100 €**.
- Le lot est progressif : par exemple, à **1000 €**, la taille de lot est de **0.1**, à **2500 €**, le lot est de **0.25**, etc.

Cette approche permet de planifier une croissance exponentielle des gains, tout en limitant le risque au fur et à mesure que le capital augmente.

## Backtesting sur Données Historiques

Vous pouvez lancer des backtests à l'aide du script dédié, par exemple :

```bash
python backtesting_BTCUSD.py
```

Dans ce script, vous pouvez ajuster la plage de dates utilisée pour les tests. Par exemple :

```python
start_date = datetime(2024, 12, 4, tzinfo=timezone)
end_date = datetime(2024, 12, 6, tzinfo=timezone)
```

Modifiez ces dates selon vos besoins. Notez que pour réaliser des backtests fiables sur une période plus ou moins longue, vous devrez disposer d’un historique de données suffisamment important dans MetaTrader 5. Plus l’historique est long, plus vos backtests seront représentatifs.

Assurez-vous que votre graphique dans MetaTrader 5 a suffisamment de données disponibles avant d’effectuer un backtest. Sans un historique assez fourni, le backtest pourra être tronqué ou impossible sur certaines plages de dates.

## Remarques supplémentaires

- Assurez-vous que le trading algo est autorisé (cliquez sur le bouton Play/Stop dans la barre d'outils de MetaTrader 5).
- Assurez-vous que le symbole (ici "BTCUSD") est bien disponible dans votre MetaTrader 5.
- Le script utilise un mode de simulation après un certain nombre de trades perdants consécutifs. Vous pouvez étudier et modifier la logique si nécessaire.
- Le script est configuré pour fonctionner sur des bougies M1 (1 minute) et récupérer un grand nombre de bougies. Avec un minimum de 150 000 bougies affichées dans le graphique de Metatrader 5, vous vous assurez que l’historique est suffisant pour les calculs, que ce soit en temps réel ou en backtesting.
- Le code affiche des informations dans la console ; pensez à les consulter pour toute information ou erreur.
- Il est recommandé de tester d’abord en mode simulation ou avec un compte de démonstration avant d’utiliser le script sur un compte réel.

## Support & Contributions

Ce projet est fourni "en l’état" sans garantie.  
Veuillez noter que l’assistance en direct n’est pas garantie.

### MR
```
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
⠀⠀⢹⣿⣷⡀⠀⠀⢰⣶⣿⣿⣿⣷⣶⣶⣾⣿⣿⠿⠛⠁⠀⠀⠀⣸⣿⡿⠀⠀
⠀⠀⠀⠹⣿⣷⣄⠀⠀⠀⠀⠀⣿⡇⠀⢸⣿⡇⠀⠀⠀⠀⠀⢀⣾⣿⠟⠁⠀⠀
⠀⠀⠀⠀⠘⢻⣿⣷⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣾⣿⡿⠋⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⠛⢿⣿⣷⣶⣤⣤⣤⣤⣤⣤⣴⣾⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⠻⠿⠿⠿⠿⠟⠛⠉⠁
```
