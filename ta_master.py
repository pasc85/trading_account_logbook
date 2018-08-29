### Trading account logbook

# (methods that are not intended to be called by user do not have docstrings)



### 0: packages
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import pickle
import copy



### 1: shares_value object
class shares_value:
    # fixed parameters
    pur_pr = float(0)
    pur_date = pd.Timestamp('now')
    # variable parameters
    shr_val = float(0)
    div_val = float(0)
    rel_val = float(0)

    def __init__(self,value,fee,**kwargs):
        self.pur_pr = value + fee
        if 'date' in kwargs.keys(): self.pur_date = kwargs['date']
        else: self.pur_date = pd.Timestamp('now')
        self.shr_val = value
        self.div_val = 0
        self.rel_val = np.nan

    def update_sv(self,**kwargs):
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
            new_sh.rel_val =( math.log(
                ( new_sh.shr_val+new_sh.div_val-s_fee ) / new_sh.pur_pr )
                * 365.0 / float(d) )
        return new_sh

    def value(self,**kwarg):
        if kwarg['mode']=='rel': return self.rel_val
        elif kwarg['mode']=='all':
            return '{:.4f} ({:.2f},{:.2f})'.format(
                                self.rel_val,self.shr_val,self.div_val)
        elif kwarg['mode']=='shr': return self.shr_val
        elif kwarg['mode']=='eff': return (self.div_val + self.shr_val)
        elif kwarg['mode']=='div': return self.div_val



### 2: methods that modify the trading account dataframe
def account_activity(increment,**kwargs):
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
    if 'date' in kwargs.keys(): now = kwargs['date']
    else: now = pd.Timestamp('now')
    try:
        ta = pickle.load(open(ta_fname,'rb'))
    except FileNotFoundError:
        cols = ['Date','Acct Bal','Comment']
        ta = pd.DataFrame({'Date' : now,
                       'Acct Bal' : increment,
                        'Comment' : 'Opening deposit'}, index=[0],columns=cols)
        pickle.dump(ta, open( ta_fname, 'wb' ) )
        print('No trading account log file found, created new one.')
    else:
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind-1], ignore_index=True)
        ta.loc[ind,'Date'] = now
        ta.loc[ind,'Acct Bal'] = ta.loc[ind,'Acct Bal'] + increment
        if 'comment' in kwargs.keys():
            ta.loc[ind,'Comment'] = kwargs['comment']
        else:
            if increment < 0: ta.loc[ind,'Comment'] = 'Withdrawal'
            else: ta.loc[ind,'Comment'] = 'Deposit'
        pickle.dump(ta, open( ta_fname, 'wb' ) )


def buy(name,value,fee,**kwargs):
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
        if 'date' in kwargs.keys(): now = kwargs['date']
        else: now = pd.Timestamp('now')
        ta = pickle.load(open(ta_fname,'rb'))
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind-1], ignore_index=True)
        ta.loc[ind,'Date'] = now
        ta.loc[ind,'Comment'] = 'Buy ' + name
        ta.loc[ind,'Acct Bal'] = ta.loc[ind,'Acct Bal'] - value - fee
        cols = list(ta.columns) + [name]
        ta = ta.reindex(columns=cols)
        ta.loc[:,name] = zero_value
        ta.loc[ind,name] = shares_value(value,fee,date=now)
        pickle.dump(ta, open( ta_fname, 'wb' ) )


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
    Best to always run update() before any of the other activites.
    '''
    if 'date' in values.keys(): now = values['date']
    else: now = pd.Timestamp('now')
    shares = active_shares()
    ta = pickle.load(open(ta_fname,'rb'))
    ind = ta.index[-1] + 1
    ta = ta.append(ta.loc[ind - 1], ignore_index=True)
    ta.loc[ind,'Date'] = now
    ta.loc[ind,'Comment'] = 'Update'
    for s in shares:
        if (now-ta.loc[ind,s].pur_date).days > 0:
            if s in values.keys():
                curr_val = values[s]
            else:
                curr_val = ta.loc[ind,s].shr_val
            ta.loc[ind,s] = ta.loc[ind,s].update_sv(value=curr_val,date=now)
    pickle.dump(ta, open( ta_fname, 'wb' ) )


def dividend(name,amount,**kwargs):
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
        if 'date' in kwargs.keys(): now = kwargs['date']
        else: now = pd.Timestamp('now')
        ta = pickle.load(open(ta_fname,'rb'))
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind - 1], ignore_index=True)
        ta.loc[ind,'Date'] = now
        ta.loc[ind,'Comment'] = 'Dividend ' + name
        ta.loc[ind,'Acct Bal'] = ta.loc[ind,'Acct Bal'] + amount
        ta.loc[ind,name] = ta.loc[ind,name].update_sv(
                                    new_dividend=amount,date=now)
        pickle.dump(ta, open( ta_fname, 'wb' ) )


def sell(name,amount,**kwargs):
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
        if 'date' in kwargs.keys(): now = kwargs['date']
        else: now = pd.Timestamp('now')
        ta = pickle.load(open(ta_fname,'rb'))
        ind = ta.index[-1] + 1
        ta = ta.append(ta.loc[ind - 1], ignore_index=True)
        ta.loc[ind,'Date'] = now
        ta.loc[ind,'Comment'] = 'Sell ' + name
        ta.loc[ind,'Acct Bal'] = ta.loc[ind,'Acct Bal'] + amount
        s = ta.loc[ind,name]
        pp = s.pur_pr
        d = now - s.pur_date
        ev = amount + s.div_val
        r = math.log(ev/pp)*365/(d.days)*100
        ta.loc[ind,name] = zero_value
        pickle.dump(ta, open( ta_fname, 'wb' ) )
        print(name + ' was sold with an overall return of {:.1f}%.'.format(r))



### 3: methods that return a displayable dataframe
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
    display_args = { 'all_shares' : False,
                       'comments' : False,
                       'acct_bal' : False,
                 'date_as_string' : False,
                           'mode' : 'rel'}
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
    display_args = { 'all_shares' : False,
                       'comments' : True,
                       'acct_bal' : True,
                 'date_as_string' : False,
                           'mode' : 'all'}
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
    display_args = { 'all_shares' : False,
                       'comments' : False,
                       'acct_bal' : True,
                 'date_as_string' : False,
                           'mode' : 'shr'}
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
    ta = pickle.load(open(ta_fname,'rb'))
    for s in shares:
        for j in range(ta.shape[0]):
            ta.loc[j,s] = ta.loc[j,s].value(mode=display_args['mode'])
    if display_args['date_as_string']:
        for j in range(ta.shape[0]):
            ta.loc[j,'Date'] = ta.loc[j,'Date'].strftime("%y-%m-%d")
    return ta.reindex(columns=cols)



### 4: other methods on the data frame
def all_shares():
    '''Return list of all shares.'''
    return list_shares(mode='all')


def active_shares():
    '''Return list of active shares.'''
    return list_shares()


def list_shares(**kwarg):
    ta = pickle.load(open(ta_fname,'rb'))
    shares = list(ta.columns)
    shares.remove('Date')
    shares.remove('Acct Bal')
    shares.remove('Comment')
    ind = ta.index[-1]
    if not ('mode','all') in kwarg.items():
        to_remove = []
        for s in shares:
            if ta.loc[ind,s].shr_val==0:
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
    ta = pickle.load(open(ta_fname,'rb'))
    ta = ta.drop(ta.index[-1])
    pickle.dump(ta, open( ta_fname, 'wb' ) )
    print('Backed up trading account and deleted last row.')


def total_value():
    '''Return time series of total value of the trading account.'''
    t = shr_values(all_shares=True, date_as_index=False)
    shares = all_shares()
    tvs = []
    for i in t.index:
        share_count = 0
        sum = t.loc[i,'Acct Bal']
        for s in shares:
            temp = t.loc[i,s]
            if temp>0:
                sum = sum + temp
                share_count = share_count + 1
        tvs.append( sum - share_count * s_fee )
    t = t.reindex(columns = ['Date','Total Value']).set_index('Date')
    t.loc[:,'Total Value'] = tvs
    return t


def backup():
    '''Save timestamped dataframe as well as a spreadsheet with the full
    record of trading account activities in a separate folder.
    '''
    ta = pickle.load(open(ta_fname,'rb'))
    d = pd.Timestamp('now').strftime("%y-%m-%d")
    name = './backups/ta_' + d
    pickle.dump(ta, open( name + '.p', 'wb' ) )
    writer = pd.ExcelWriter( name + '.xlsx', engine='xlsxwriter')
    ta = shr_values(all_shares=True, comments=True, date_as_string=True)
    ta.to_excel(writer, sheet_name='Trading Account ' + d)
    writer.save()



### 5: other tools
def bond_evaluation(coupon,years_to_maturity):
    '''Return table linking overall return rates to bond prices.

    Arguments:
    coupon -- annual yield of the bond in percent
    years_to_maturity -- number of years to maturity
    '''
    y = coupon*0.01
    m = years_to_maturity
    drs = list(k*0.1 for k in range(-10,100,5))
    be = pd.DataFrame({'Return (%)':drs, 'Price':1})
    be = be.set_index('Return (%)')
    for i in be.index:
        d = i*0.01
        if i==0:
            be.loc[i,'Price'] = 100 + m * 100 * y
        else:
            be.loc[i,'Price'] = 100.0/d * ( y + (1/(1+d))**m * (d-y) )
    return be



### 6: constants
# trading fee (approximate value that will be used to compute the relative
# values -- exact fee will be implicitly logged when selling)
s_fee = 10
# zero_value to pad inactive shares or new ones
zero_value = shares_value(0,0)
# name of the trading account
ta_fname = 'ta_save.p'
