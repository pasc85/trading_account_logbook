import urllib.request
from bs4 import BeautifulSoup
import sys

# read in list of stocks to check and
# the corresponding threshold prices
stocks = {}
try:
    wl_file = open('watchlist.txt', 'r')
    for line in wl_file:
        if line.strip():
            temp = line.strip().split(' ')
            stocks[temp[0]] = float(temp[1])
    wl_file.close()
except FileNotFoundError:
    print('File <watchlist.txt> not present.')
    print('No action taken.')
    raise
except IndexError:
    print('Watchlist not in the correct format;'
          + ' should be: "<handle> <value>".')
    print('No action taken.')
    raise

# initialisation
alert = False
best_ratio = 100.00
best_name = 'Empty_watchlist.'
best_curr = 1.0
best_comp = 1.0
output = ''

# scrape stock prices and set output to alert message
# if some of them are below the given prices
for s in stocks.keys():
    source = "https://finance.yahoo.com/quote/" + s
    filehandle = urllib.request.urlopen(source)
    soup = BeautifulSoup(filehandle.read(), "html.parser")
    priceSpan = soup.findAll("span", {"class": "Fz(36px)"})
    for elt in priceSpan:
        curr = float(elt.getText())
        comp = stocks[s]
        if curr <= comp:
            alert = True
            output += '\nALERT!!!\n'
            output += '%s is currently %.3f < %.3f.\n' % (s, curr, comp)
        else:
            if curr/comp < best_ratio:
                best_name = s
                best_ratio = curr/comp
                best_curr = curr
                best_comp = comp

# if nothing to alert to, set output to be message with the next best stock
if not alert:
    output += 'Nothing to alert to.\n'
    if best_name == 'Empty watchlist.':
        output += best_name
    else:
        output += ('(%s is closest with current price %.3f > %.3f.)'
                   % (best_name, best_curr, best_comp))

# now, either send email with output message or print to console
if len(sys.argv) > 1 and sys.argv[1] == '-email':
    # email only if there is something to alert to
    if alert:
        try:
            config_file = open('email_config.txt', 'r')
            config = eval(config_file.read())
            config_file.close()
        except FileNotFoundError:
            print('No config file present;'
                  + ' should be called <email_config.txt>.')
            print('Email not sent.')
            raise
        except SyntaxError:
            print('Invalid syntax in the config file.')
            print('Email not sent.')
            raise
        if len(config) == 5:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            try:
                s = smtplib.SMTP(host=config['host'], port=config['port'])
                s.starttls()
                s.login(config['sender'], config['password'])
                msg = MIMEMultipart()
                msg['From'] = config['sender']
                msg['To'] = config['recipient']
                msg['Subject'] = 'Stock price alert'
                msg.attach(MIMEText(output, 'plain'))
                s.send_message(msg)
                s.quit()
            except Exception:
                print('Problem with sending the email.'
                      + ' Check config file, etc.')
                print('Email not sent. Here is the output message:')
                print(output)
        else:
            print('The config dictionary does not contain the correct'
                  + ' number of entries.')
            print('Email not sent. Here is the output message:')
            print(output)
else:
    print(output)
