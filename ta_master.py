# Trading account logbook


# 0: packages
import pandas as pd
import numpy as np
import math
import pickle
import copy
import os


# 1: ShareValue object
class ShareValue:

    def __init__(self, value, fee, **kwargs):
        self.pur_pr = value + fee
        if 'date' in kwargs.keys():
            self.pur_date = kwargs['date']
        else:
            self.pur_date = pd.Timestamp('now')
        self.shr_val = value
        self.div_val = 0
        self.rel_val = np.nan

    def update_sv(self, **kwargs):
        new_sh = copy.deepcopy(self)
        if 'value' in kwargs.keys():
            new_sh.shr_val = kwargs['value']
        if 'new_dividend' in kwargs.keys():
            new_sh.div_val = new_sh.div_val + kwargs['new_dividend']
        if 'date' in kwargs.keys():
            d = (kwargs['date'] - new_sh.pur_date).days
        else:
            d = (pd.Timestamp('now') - new_sh.pur_date).days
        if d > 0:
            new_sh.rel_val = (math.log(
                (new_sh.shr_val + new_sh.div_val - s_fee) / new_sh.pur_pr)
                * 365.0 / float(d))
        return new_sh

    def value(self, **kwarg):
        if kwarg['mode'] == 'rel':
            return self.rel_val
        elif kwarg['mode'] == 'all':
            return '{:.4f} ({:.2f}, {:.2f})'.format(
                                self.rel_val, self.shr_val, self.div_val)
        elif kwarg['mode'] == 'shr':
            return self.shr_val
        elif kwarg['mode'] == 'eff':
            return (self.div_val + self.shr_val)
        elif kwarg['mode'] == 'div':
            return self.div_val


# 2: methods that modify the trading account dataframe
def account_activity(increment, **kwargs):
    '''Modify account balance.

    Arguments:
    increment -- value added to trading account (can be negative)

    Keyword arguments
    date -- specify date, default is current time
            (e.g.: date = pd.Timestamp(2017,1,1))
    comment -- type of modification, default is 'Deposit'/'Withdrawal'
               depending on whether the given increment is positive or negative

    Note:
    If no ta file found, a new one will be created with the given balance;
    the comment is 'Opening deposit' in this case.
    '''
    if 'date' in kwargs.keys():
        now = kwargs['date']
    else:
        now = pd.Timestamp('now')
    try:
        ta = ta_read()
    except FileNotFoundError:
        cols = ['Date', 'Acct Bal', 'Comment']
        d = {'Date': now, 'Acct Bal': increment, 'Comment': 'Opening deposit'}
        ta = pd.DataFrame(d, index=[0], columns=cols)
        ta_write(ta)
        print('No trading account log file found, created new one.')
    else:
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind-1], ignore_index=True)
        ta.loc[ind, 'Date'] = now
        ta.loc[ind, 'Acct Bal'] = ta.loc[ind, 'Acct Bal'] + increment
        if 'comment' in kwargs.keys():
            ta.loc[ind, 'Comment'] = kwargs['comment']
        else:
            if increment < 0:
                ta.loc[ind, 'Comment'] = 'Withdrawal'
            else:
                ta.loc[ind, 'Comment'] = 'Deposit'
        ta_write(ta)


def buy(name, value, fee, **kwargs):
    '''Buy shares of a company.

    Arguments:
    name -- name of shares bought (no action if name matches an active share)
    value -- value of shares bought (i.e. price excluding transaction fee)
    fee -- transaction fee

    Keyword arguments
    date -- specify date, default is current time
    '''
    if name in all_shares():
        print('Share name already exists. No changes made.')
    else:
        if 'date' in kwargs.keys():
            now = kwargs['date']
        else:
            now = pd.Timestamp('now')
        ta = ta_read()
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind-1], ignore_index=True)
        ta.loc[ind, 'Date'] = now
        ta.loc[ind, 'Comment'] = 'Buy ' + name
        ta.loc[ind, 'Acct Bal'] = ta.loc[ind, 'Acct Bal'] - value - fee
        cols = list(ta.columns) + [name]
        ta = ta.reindex(columns=cols)
        ta.loc[:, name] = zero_value
        ta.loc[ind, name] = ShareValue(value, fee, date=now)
        ta_write(ta)


def update(**values):
    '''Update given shares values and all relative values.

    Keyword arguments:
    <share_name> -- specify shares value of active shares to be updated
                        (keep previous value if not specified)
    date -- specify date, default is current time
            (e.g.: date = pd.Timestamp(2017,1,1))

    Note:
    Running this method without any arguments leaves the share values
        invariant and updates the time-dependent relative values only.
    '''
    if 'date' in values.keys():
        now = values['date']
    else:
        now = pd.Timestamp('now')
    shares = active_shares()
    ta = ta_read()
    ind = ta.index[-1] + 1
    ta = ta.append(ta.loc[ind - 1], ignore_index=True)
    ta.loc[ind, 'Date'] = now
    ta.loc[ind, 'Comment'] = 'Update'
    for s in shares:
        if (now-ta.loc[ind, s].pur_date).days > 0:
            if s in values.keys():
                curr_val = values[s]
            else:
                curr_val = ta.loc[ind, s].shr_val
            ta.loc[ind, s] = ta.loc[ind, s].update_sv(value=curr_val, date=now)
    ta_write(ta)


def auto_update():
    '''Scrape the value of the portfolio and update.'''
    ud = get_update_dict()
    update(**ud)


def dividend(name, amount, **kwargs):
    '''Log a dividend that was paid.

    Arguments:
    name -- name of shares for which a dividend was paid
                    (no action if it is not an active share)
    amount -- total amount of dividend paid

    Keyword arguments
    date -- specify date, default is current time
            (e.g.: date = pd.Timestamp(2017,1,1))
    '''
    if name not in active_shares():
        print('Given share name is not an active share, no action taken.')
    else:
        if 'date' in kwargs.keys():
            now = kwargs['date']
        else:
            now = pd.Timestamp('now')
        ta = ta_read()
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind - 1], ignore_index=True)
        ta.loc[ind, 'Date'] = now
        ta.loc[ind, 'Comment'] = 'Dividend ' + name
        ta.loc[ind, 'Acct Bal'] = ta.loc[ind, 'Acct Bal'] + amount
        ta.loc[ind, name] = ta.loc[ind, name].update_sv(
                                    new_dividend=amount, date=now)
        ta_write(ta)


def sell(name, amount, **kwargs):
    '''Sell a share.

    Arguments:
    name -- name of shares which was sold
                    (no action if it is not an active share)
    amount -- amount credited to the account after the sale

    Keyword arguments:
    date -- specify date, default is current time
            (e.g.: date = pd.Timestamp(2017,1,1))

    Note:
    A message will state the overall return of this investment, taking into
    account the purchase price, fees, dividends paid, time for which it was
    held, and the amount credited to the account after the sale.
    '''
    if name not in active_shares():
        print('Given share name is not an active share, no action taken.')
    else:
        if 'date' in kwargs.keys():
            now = kwargs['date']
        else:
            now = pd.Timestamp('now')
        ta = ta_read()
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind - 1], ignore_index=True)
        ta.loc[ind, 'Date'] = now
        ta.loc[ind, 'Comment'] = 'Sell ' + name
        ta.loc[ind, 'Acct Bal'] = ta.loc[ind, 'Acct Bal'] + amount
        s = ta.loc[ind, name]
        pp = s.pur_pr
        d = now - s.pur_date
        ev = amount + s.div_val
        r = math.log(ev/pp)*365/(d.days)*100
        ta.loc[ind, name] = zero_value
        ta_write(ta)
        print(name + ' was sold with an overall return of {:.1f}%.'.format(r))


# 3: methods that return a displayable dataframe
def rel_values(**kwargs):
    '''Return dataframe with relative values as floats.

    Keyword arguments:
    all_shares -- display all shares instead of
                                    active ones only (default False)
    comments -- display comments (default False)
    acct_bal -- display account balance (default False)
    date_as_string -- write dates as strings (default False)
    date_as_index -- set dates as index (default True)
    mode -- default is 'rel', set to 'eff' or 'div' to
                                    display effective values or dividends

    Note:
    Relative values take into account the purchase price, fees, dividends, the
    time for which the investment has been held, and the current share price.
    Interpretation: If the share was sold now, what interest rate (continuously
    compounded) would have led to the same profit/loss.
    '''
    display_args = {'all_shares': False,
                    'comments': False,
                    'acct_bal': False,
                    'date_as_string': False,
                    'mode': 'rel'}
    for k in kwargs.keys():
        if k in display_args.keys():
            display_args[k] = kwargs[k]
    if 'date_as_index' in kwargs.keys() and not kwargs['date_as_index']:
        temp = convert_df(display_args)
    else:
        temp = convert_df(display_args).set_index('Date')
    return temp


def all_values(**kwargs):
    '''Return dataframe with all types of value displayed as a string.

    Keyword arguments:
    all_shares -- display all shares instead of
                                    active ones only (default False)
    comments -- display comments (default True)
    acct_bal -- display account balance (default True)
    date_as_string -- write dates as strings (default False)
    date_as_index -- set dates as index (default False)

    Note:
    The output string is of the form 'relative value (share value, dividends)'.
    '''
    display_args = {'all_shares': False,
                    'comments': True,
                    'acct_bal': True,
                    'date_as_string': False,
                    'mode': 'all'}
    for k in kwargs.keys():
        if k in display_args.keys():
            display_args[k] = kwargs[k]
    if 'date_as_index' in kwargs.keys() and kwargs['date_as_index']:
        temp = convert_df(display_args).set_index('Date')
    else:
        temp = convert_df(display_args)
    return temp


def shr_values(**kwargs):
    '''Return dataframe with shares values as floats.

    Keyword arguments:
    all_shares -- display all shares instead of
                                    active ones only (default False)
    comments -- display comments (default False)
    acct_bal -- display account balance (default True)
    date_as_string -- write dates as strings (default False)
    date_as_index -- set dates as index (default True)
    '''
    display_args = {'all_shares': False,
                    'comments': False,
                    'acct_bal': True,
                    'date_as_string': False,
                    'mode': 'shr'}
    for k in kwargs.keys():
        if k in display_args.keys():
            display_args[k] = kwargs[k]
    if 'date_as_index' in kwargs.keys() and not kwargs['date_as_index']:
        temp = convert_df(display_args)
    else:
        temp = convert_df(display_args).set_index('Date')
    return temp


def convert_df(display_args):
    if display_args['all_shares']:
        shares = all_shares()
    else:
        shares = active_shares()
    cols = shares
    if display_args['comments']:
        cols = ['Comment'] + cols
    if display_args['acct_bal']:
            cols = ['Acct Bal'] + cols
    cols = ['Date'] + cols
    ta = ta_read()
    for s in shares:
        for j in range(ta.shape[0]):
            ta.loc[j, s] = ta.loc[j, s].value(mode=display_args['mode'])
    if display_args['date_as_string']:
        for j in range(ta.shape[0]):
            ta.loc[j, 'Date'] = ta.loc[j, 'Date'].strftime("%y-%m-%d")
    return ta.reindex(columns=cols)


# 4: other methods on the data frame
def all_shares():
    '''Return list of all shares.'''
    return list_shares(mode='all')


def active_shares():
    '''Return list of active shares.'''
    return list_shares()


def list_shares(**kwarg):
    ta = ta_read()
    shares = list(ta.columns)
    shares.remove('Date')
    shares.remove('Acct Bal')
    shares.remove('Comment')
    ind = ta.index[-1]
    if not ('mode', 'all') in kwarg.items():
        to_remove = []
        for s in shares:
            if ta.loc[ind, s].shr_val == 0:
                to_remove.append(s)
        for s in to_remove:
                shares.remove(s)
    return shares


def delete_last_row():
    '''Back up trading account dataframe and then delete the last row.

    Note:
    Other changes have to be done manually.
    '''
    backup()
    ta = ta_read()
    ta = ta.drop(ta.index[-1])
    ta_write(ta)
    print('Backed up trading account and deleted last row.')


def total_value():
    '''Return time series of total value of the trading account.'''
    t = shr_values(all_shares=True, date_as_index=False)
    shares = all_shares()
    tvs = []
    for i in t.index:
        share_count = 0
        sum = t.loc[i, 'Acct Bal']
        for s in shares:
            temp = t.loc[i, s]
            if temp > 0:
                sum = sum + temp
                share_count = share_count + 1
        tvs.append(sum - share_count * s_fee)
    t = t.reindex(columns=['Date', 'Total Value']).set_index('Date')
    t.loc[:, 'Total Value'] = tvs
    return t


def backup():
    '''Save timestamped dataframe as well as a spreadsheet with the full
    record of trading account activities in a separate folder.
    '''
    ta = ta_read()
    d = pd.Timestamp('now').strftime("%y-%m-%d")
    if not os.path.isdir('./backups'):
        os.mkdir('./backups')
        print('Created folder for backups.')
    name = './backups/' + ta_fname.split('_')[0] + '_' + d
    backup_file = open(name + '.p', 'wb')
    pickle.dump(ta, backup_file)
    backup_file.close()
    writer = pd.ExcelWriter(name + '.xlsx', engine='xlsxwriter')
    ta = shr_values(all_shares=True, comments=True, date_as_string=True)
    ta.to_excel(writer, sheet_name='Trading Account ' + d)
    writer.save()


def account_name(*acct_name):
    '''Display current account name, switch to others, or create new one.

    Optional arguments:
    acct_name -- name of account (string) to switch to (if name exists)
                                    or to create (if name does not exit)

    Note:
    Return list of existing accounts with active/current
                                    one in the first position.
    '''
    try:
        names_file = open('account_names.p', 'rb')
        names = pickle.load(names_file)
        names_file.close()
    except FileNotFoundError:
        print('No file with account names found. Created new one.')
        if acct_name:
            names = [acct_name[0]]
            print('with given account name, '+names[0]+'.')
        else:
            names = ['ta']
            print('with default account name, ta.')
        names_file = open('account_names.p', 'wb')
        pickle.dump(names, names_file)
        names_file.close()
    else:
        if acct_name:
            name = acct_name[0]
            if name in names:
                names.remove(name)
                names.insert(0, name)
                print('Switched to existing account, '+names[0]+'.')
            else:
                names.insert(0, name)
                print('Switched to new account, '+names[0]+'.')
            names_file = open('account_names.p', 'wb')
            pickle.dump(names, names_file)
            names_file.close()
    global ta_fname
    ta_fname = names[0]+'_save.p'
    if not os.path.isfile(ta_fname):
        print('Warning: The account with the above name has not been')
        print('initiated yet. Initiate using the method account_activity,')
        print('passing the opening deposit amount as an argument. Calling')
        print('any other methods before doing that will cause errors.')
    return names


def ta_write(ta):
    ta_file = open(ta_fname, 'wb')
    pickle.dump(ta, ta_file)
    ta_file.close()


def ta_read():
    ta_file = open(ta_fname, 'rb')
    ta = pickle.load(ta_file)
    ta_file.close()
    return ta


# 5: other tools
def bond_evaluation(coupon, years_to_maturity):
    '''Return table linking overall return rates to bond prices.

    Arguments:
    coupon -- annual yield of the bond in percent
    years_to_maturity -- number of years to maturity
    '''
    y = coupon*0.01
    m = years_to_maturity
    drs = list(k*0.1 for k in range(-10, 100, 5))
    be = pd.DataFrame({'Return (%)': drs, 'Price': 1})
    be = be.set_index('Return (%)')
    for i in be.index:
        d = i*0.01
        if i == 0:
            be.loc[i, 'Price'] = 100 + m * 100 * y
        else:
            be.loc[i, 'Price'] = 100.0/d * (y + (1/(1+d))**m * (d-y))
    return be


def simulate_p(mu, sigma, begweek=12, endweek=52, **kwargs):
    '''Simulate the evolution of shares with a given growth specified by a mean
    and standard deviation. Produces a table that indicates how likely it is
    that certain p values will achieved within a specified period. The week in
    which each p value was achieved is indicated in the second row.

    Arguments:
    mu -- mean weekly growth rate, can be found from historical data using the
                                method find_mu_sigma
    sigma -- standard deviation of weekly growth rates, can be found from
                                historical data using the method find_mu_sigma

    Optional arguments:
    begweek -- first week of period in which share may be sold
    endweek -- last week of period in which share may be sold

    Keyword arguments:
    name -- name of the share for which the analysis is carried out

    Note:
    If share name was given and if a file 'p_table.xlsx' is present in the
    working directory, a row with the obtained p values will be added to it.
    Also note that neither dividends nor order fees are taken into account.
    '''
    N = 10000
    n = endweek
    b = begweek-1
    maxima = np.zeros((2, N))
    for k in range(N):
        if sigma == 0:
            sigma = 0.00000001
        ls = sigma*np.random.randn(n) + mu
        lv = list(np.cumsum(ls))
        lv.insert(0, 0)
        v = list(map(lambda t: math.exp(t), lv))
        v.pop(0)
        p = np.zeros(n-b)
        for i in range(b, n):
            p[i-b] = math.log(v[i])*52/float(i)
        maxima[0, k] = np.max(p)
        maxima[1, k] = np.argmax(p)+b+1
    ordered = np.sort(maxima[0, :])
    cols = ['Date', 'Sharename', 'p_max', 'p_90', 'p_80', 'p_70', 'p_60',
            'p_50', 'p_40', 'p_30', 'p_20', 'p_10', 'p_min']
    data = ['' for i in range(13)]
    df = pd.DataFrame([data, data], columns=cols, index=[0, 1])
    df = df.fillna('')
    val = ordered[N-1]
    idx = np.where(maxima[0, :] == val)
    df.iloc[0, 2] = '{:.4f}'.format(val)
    df.iloc[1, 2] = '{:d}'.format(int(maxima[1, idx]))
    val = ordered[0]
    idx = np.where(maxima[0, :] == val)
    df.iloc[0, 12] = '{:.4f}'.format(val)
    df.iloc[1, 12] = '{:d}'.format(int(maxima[1, idx]))
    for k in range(9):
        val = ordered[int(((9-k)*N)/10)]
        idx = np.where(maxima[0, :] == val)
        df.iloc[0, k+3] = '{:.4f}'.format(val)
        df.iloc[1, k+3] = '{:d}'.format(int(maxima[1, idx]))
    df.iloc[0, 0] = pd.Timestamp('now').strftime("%y-%m-%d")
    if 'name' in kwargs.keys():
        df.iloc[0, 1] = kwargs['name']
        if os.path.isfile('p_table.xlsx'):
            old_p = pd.read_excel('p_table.xlsx')
            new_p = old_p.append(df.iloc[0], ignore_index=True)
            writer = pd.ExcelWriter('p_table.xlsx', engine='xlsxwriter')
            new_p.to_excel(writer, sheet_name='Significance of p-values')
            writer.save()
        else:
            writer = pd.ExcelWriter('p_table.xlsx', engine='xlsxwriter')
            new_p = df.reindex(index=[df.index[0]])
            new_p.to_excel(writer, sheet_name='Significance of p-values')
            writer.save()
    return df


def find_mu_sigma(data=[]):
    '''Find mean logreturn and its standard deviation from a data column of
    weekly share prices. This data can be passed as an argument or must be
    saved in a file called 'data.csv' in the working directory (downloaded
    from Yahoo Finance).

    Optional arguments:
    data -- list of weekly stock prices
    '''
    if data:
        v = data
    else:
        try:
            d = pd.read_csv('data.csv')
        except FileNotFoundError:
            print('File data.csv not found, return NaN.')
            return [np.nan, np.nan]
        else:
            d = d.dropna(how='any')
            d = d.reset_index()
            v = d.Close
    log_returns = []
    for k in range(1, len(v)):
        log_returns.append(math.log(float(v[k])/float(v[k-1])))
    log_returns = np.asarray(log_returns)
    mu = log_returns.mean()
    sigma = log_returns.std()
    return [mu, sigma]


def check_watchlist():
    '''Check whether stocks in watchlist are below given values.'''
    cwl = open('./cwl.py')
    exec(cwl.read())
    cwl.close()


def get_update_dict():
    '''Get a dictionary of current values in the portfolio.'''
    import urllib.request
    from bs4 import BeautifulSoup
    dict_file_name = account_name()[0] + '_dict.txt'
    update_dict = {}
    if os.path.isfile(dict_file_name):
        stock_dict_file = open(dict_file_name, 'r')
        for line in stock_dict_file:
            if line.strip():
                temp_list = line.strip().split(' ')
                TA_name = temp_list[0]
                YF_name = temp_list[1]
                n_stock = int(temp_list[2])
                source = "https://finance.yahoo.com/quote/"+YF_name
                filehandle = urllib.request.urlopen(source)
                soup = BeautifulSoup(filehandle.read(), "html.parser")
                priceSpan = soup.findAll("span", {"class": "Fz(36px)"})
                for elt in priceSpan:
                    curr_pr = float(elt.getText())
                update_dict[TA_name] = n_stock * curr_pr
        stock_dict_file.close()
    else:
        print('File containing dictionary of stocks in the portfolio')
        print('not found. Should be called <' + dict_file_name + '>.')
    return update_dict


# 6: constants
# trading fee (approximate value that will be used to compute the relative
# values -- exact fee will be implicitly logged when selling)
s_fee = 15
# zero_value to pad inactive shares or new ones
zero_value = ShareValue(0, 0)
# initialise (set name of trading account to be used)
account_name()
