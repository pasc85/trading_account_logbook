import urllib.request
from bs4 import BeautifulSoup
import os

if os.path.isfile('watchlist.txt'):

    # read in list of stocks to check and
    # the corresponding threshold prices
    stocks = {}
    wl_file = open('watchlist.txt', 'r')
    for line in wl_file:
        if line.strip():
            temp = line.strip().split(' ')
            stocks[temp[0]] = float(temp[1])
    wl_file.close()

    # scrape stock prices and print alert message
    # if some of them are below the given prices
    alert = False
    best_ratio = 100.00
    best_name = ''
    best_curr = 1.0
    best_comp = 1.0
    for s in stocks.keys():
        source = "https://finance.yahoo.com/quote/"+s
        filehandle = urllib.request.urlopen(source)
        soup = BeautifulSoup(filehandle.read(), "html.parser")
        priceSpan = soup.findAll("span", {"class": "Fz(36px)"})
        for elt in priceSpan:
            curr = float(elt.getText())
            comp = stocks[s]
            if curr <= comp:
                alert = True
                print('ALERT!!!')
                print('%s is currently %.3f < %.3f.' % (s, curr, comp))
            else:
                if curr/comp < best_ratio:
                    best_name = s
                    best_ratio = curr/comp
                    best_curr = curr
                    best_comp = comp

    if not alert:
        print('Nothing to alert to.')
        print('(%s is closest with current price %.3f > %.3f.)'
              % (best_name, best_curr, best_comp))

else:
    print('File <watchlist.txt> not present.')
