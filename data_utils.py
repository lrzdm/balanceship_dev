import os
from flask import Flask, render_template, request, jsonify
import yfinance as yf
import csv
import pickle
import pandas as pd
import time
import atexit
import datetime
from cache_db import load_from_db
from cache_db import save_to_db
import random


def read_exchanges(filename):
    exchanges = {}
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 2:
                exchanges[row[0].strip()] = row[1].strip()
    return exchanges

def read_companies(filename):
    companies = []
    with open(filename, 'r', encoding='utf-8', errors='replace') as file:
        reader = csv.DictReader(file)
        for row in reader:
            companies.append(row)
    return companies
    
##def format_to_billions(value):
##    try:
##        value_in_billions = value / 1_000_000_000
##        return f"{value_in_billions:,.3f}"
##    except Exception:
##        return "N/A"
    
def get_financial_data_from_source(symbol, years, description=None, stock_exchange=None):
    #Scarica i dati finanziari da Yahoo Finance per ogni anno richiesto

    def format_to_billions(x):
        try:
            return float(x) / 1e9
        except:
            return 0

    results = []

    try:
        stock = yf.Ticker(symbol)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        info = stock.info

        if financials.empty and balance_sheet.empty and cashflow.empty:
            print(f"No financial data found for symbol: {symbol}")
            return []

        # Ottieni anni disponibili nei dati
        #columns_years = [col.year for col in financials.columns if isinstance(col, pd.Timestamp)]
        columns_years = []
        for col in financials.columns:
            try:
                parsed = pd.to_datetime(col)
                columns_years.append(parsed.year)
            except:
                continue
        print(f"[{symbol}] Anni trovati in financials: {columns_years}")



        for year in years:
            sleep_time = random.uniform(4, 8)
            time.sleep(sleep_time)
            if year not in columns_years:
                print(f"Year {year} not found for symbol {symbol}")
                continue

            year_index = columns_years.index(year)
            year_column = financials.columns[year_index]

            # Funzioni di utilità per prendere i dati in modo sicuro
            def f(idx): return financials.loc[idx, year_column] if idx in financials.index else 0
            def fb(idx): return balance_sheet.loc[idx, year_column] if idx in balance_sheet.index else 0
            def fc(idx): return cashflow.loc[idx, year_column] if idx in cashflow.index else 0

            data = {
                'symbol': symbol,
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'description': description,
                'stock_exchange': stock_exchange,
                'year': year,
                'total_revenue': format_to_billions(f('Total Revenue')),
                'operating_revenue': format_to_billions(f('Operating Revenue')),
                'cost_of_revenue': format_to_billions(f('Cost Of Revenue')),
                'gross_profit': format_to_billions(f('Gross Profit')),
                'operating_expense': format_to_billions(f('Operating Expense')),
                'sg_and_a': format_to_billions(f('Selling General And Administration')),
                'r_and_d': format_to_billions(f('Research And Development')),
                'operating_income': format_to_billions(f('Operating Income')),
                'net_non_operating_interest_income_expense': format_to_billions(f('Net Non Operating Interest Income Expense')),
                'interest_expense_non_operating': format_to_billions(f('Interest Expense Non Operating')),
                'pretax_income': format_to_billions(f('Pretax Income')),
                'tax_provision': format_to_billions(f('Tax Provision')),
                'net_income_common_stockholders': format_to_billions(f('Net Income Common Stockholders')),
                'net_income': format_to_billions(f('Net Income')),
                'net_income_continuous_operations': format_to_billions(f('Net Income Continuous Operations')),
                'basic_eps': f('Basic EPS'),
                'diluted_eps': f('Diluted EPS'),
                'basic_average_shares': format_to_billions(f('Basic Average Shares')),
                'diluted_average_shares': format_to_billions(f('Diluted Average Shares')),
                'total_expenses': format_to_billions(f('Total Expenses')),
                'normalized_income': format_to_billions(f('Normalized Income')),
                'interest_expense': format_to_billions(f('Interest Expense')),
                'net_interest_income': format_to_billions(f('Net Interest Income')),
                'ebit': format_to_billions(f('EBIT')),
                'ebitda': format_to_billions(f('EBITDA')),
                'reconciled_depreciation': format_to_billions(f('Reconciled Depreciation')),
                'normalized_ebitda': format_to_billions(f('Normalized EBITDA')),
                'total_assets': format_to_billions(fb('Total Assets')),
                'stockholders_equity': format_to_billions(fb("Stockholders Equity")),
                'free_cash_flow': format_to_billions(fc("Free Cash Flow")),
                'changes_in_cash': format_to_billions(fc('Changes In Cash')),
                'working_capital': format_to_billions(fb("Working Capital")),
                'invested_capital': format_to_billions(fb("Invested Capital")),
                'total_debt': format_to_billions(fb("Total Debt")),
            }

            results.append(data)
            time.sleep(random.uniform(4, 8))
        return results

    except Exception as e:
        print(f"Error retrieving financial data for {symbol}: {e}")
        return []



def get_financial_data(symbol, years, force_refresh=False, description=None, stock_exchange=None):
    if not isinstance(years, (list, tuple)):
        years = [years]
    # Carica dati cached (None se non disponibili)
    cached_data = load_from_db(symbol, years)

    # Trova anni mancanti (dove cached_data[i] è None)
    missing_years = [year for i, year in enumerate(years) if cached_data[i] is None]

    # BLOCCO PER STREAMLIT CLOUD
    #if os.environ.get("STREAMLIT_CLOUD") == "1":
    #    return cached_data
    if missing_years or force_refresh:
        # Scarica dati mancanti
        new_data = get_financial_data_from_source(symbol, missing_years, description=description, stock_exchange=stock_exchange)
        if new_data:
            # Salva nuovi dati nel DB/cache
            save_to_db(symbol, missing_years, new_data)

            # Integra i dati scaricati nei dati cached
            for i, year in enumerate(years):
                if cached_data[i] is None and year in missing_years:
                    idx = missing_years.index(year)
                    #cached_data[i] = new_data[idx]
                    if idx < len(new_data):
                        cached_data[i] = new_data[idx]
                    else:
                        cached_data[i] = None                 
 
    return cached_data



def remove_duplicates(data):
    seen = set()
    unique_data = []
    for item in data:
        if not isinstance(item, dict):  # Salta None o altri tipi non validi
            continue
        item_tuple = tuple(item.items())
        if item_tuple not in seen:
            seen.add(item_tuple)
            unique_data.append(item)
    return unique_data



def get_all_financial_data(force_refresh=True):
    exchanges = read_exchanges('exchanges.txt')
    financial_data = []

    for exchange in exchanges.values():
        companies = read_companies(exchange)
        for company in companies:
            symbol = company['ticker']
            description = company['description']
            stock_exchange = exchange

            data_list = get_financial_data(
                symbol, ['2021', '2022', '2023', '2024'],
                force_refresh=force_refresh,
                description=description,
                stock_exchange=stock_exchange
            )
            #print(f"Fetched {len(data_list)} records for {symbol}")

            for data in data_list:
                if data is not None and isinstance(data, dict):
                    data['description'] = description
                    data['stock_exchange'] = stock_exchange
                    financial_data.append(data)
                #save_to_db(symbol, selected_years, data_list)
            time.sleep(random.uniform(5, 9))

    financial_data = remove_duplicates(financial_data)
    financial_data = [x for x in financial_data if 'symbol' in x and 'year' in x]

    # Ordina se la lista è rimasta valida
    if financial_data:
        financial_data.sort(key=lambda x: (x['symbol'], x['year']))

    #financial_data.sort(key=lambda x: (x['symbol'], x['year']))
    return financial_data




def compute_kpis(financial_data):
    import pandas as pd
    import numpy as np

    # Mappa colonne dataset -> nomi usati nei KPI
    col_map = {
        'Gross Profit': 'gross_profit',
        'Total Revenue': 'total_revenue',
        'Operating Income': 'operating_income',
        'Net Income': 'net_income',
        'EBITDA': 'ebitda',
        'EBIT': 'ebit',
        'Total Assets': 'total_assets',
        'Stockholders Equity': 'stockholders_equity',
        'Invested Capital': 'invested_capital',
        'Total Debt': 'total_debt',
        'Interest Expense': 'interest_expense',
        'Tax Provision': 'tax_provision',
        'Pretax Income': 'pretax_income',
        'SG&A': 'sg_and_a',
        'R&D': 'r_and_d',
        'Free Cash Flow': 'free_cash_flow',
        'Change in Cash': 'changes_in_cash',
        'Working Capital': 'working_capital',
        'Current Assets': 'current_assets',
        'Current Liabilities': 'current_liabilities',
        'inventories': 'inventories',
        'cost_of_revenue': 'cost_of_revenue',
        'receivables': 'receivables',
    }

    # Invertiamo il dizionario per rinominare da dataset a nomi KPI
    reverse_map = {v: k for k, v in col_map.items()}

    try:
        def to_float(val):
            if pd.isna(val):
                return np.nan
            if isinstance(val, str):
                # pulizia stringhe numeriche con virgole, parentesi ecc.
                val = val.replace(",", "").replace("(", "-").replace(")", "")
            try:
                return float(val)
            except:
                return np.nan

        # Se è un dizionario singolo, lo trasformiamo in lista per DataFrame
        if isinstance(financial_data, dict):
            financial_data = [financial_data]

        df = pd.DataFrame(financial_data)

        # Rinominare le colonne del dataset con i nomi KPI (se presenti)
        df.rename(columns=reverse_map, inplace=True)

        # Assicuriamoci che tutte le colonne necessarie esistano, altrimenti creiamole con NaN
        for col in col_map.keys():
            if col not in df.columns:
                df[col] = np.nan

        # Conversione numerica su tutte le colonne KPI
        for col in col_map.keys():
            df[col] = df[col].apply(to_float)

        # Colonne "base" che devono sempre esserci
        if 'symbol' not in df.columns:
            df['symbol'] = 'N/A'
        if 'year' not in df.columns:
            df['year'] = 'N/A'

        # Calcolo KPI
        df['Gross Margin'] = df['Gross Profit'] / df['Total Revenue']
        df['Operating Margin'] = df['Operating Income'] / df['Total Revenue']
        df['Net Margin'] = df['Net Income'] / df['Total Revenue']
        df['EBITDA Margin'] = df['EBITDA'] / df['Total Revenue']
        df['ROA'] = df['Net Income'] / df['Total Assets']
        df['ROE'] = df['Net Income'] / df['Stockholders Equity']
        df['ROIC'] = df['EBIT'] / df['Invested Capital']
        df['Debt/Equity'] = df['Total Debt'] / df['Stockholders Equity']
        #df['Interest Coverage'] = df['EBIT'] / df['Interest Expense']
        df['Tax Rate'] = df['Tax Provision'] / df['Pretax Income']
        df['SG&A/Revenue'] = df['SG&A'] / df['Total Revenue']
        df['R&D/Revenue'] = df['R&D'] / df['Total Revenue']
        df['FCF Margin'] = df['Free Cash Flow'] / df['Total Revenue']
        df['Working Capital/Revenue'] = df['Working Capital'] / df['Total Revenue']
        #df['Current Ratio'] = df['Current Assets'] / df['Current Liabilities']
        #df['Quick Ratio'] = (df['Current Assets'] - df['inventories']) / df['Current Liabilities']
        df['Asset Turnover'] = df['Total Revenue'] / df['Total Assets']
        #df['Inventory Turnover'] = df['cost_of_revenue'] / df['inventories']
        #df['Receivables Turnover'] = df['Total Revenue'] / df['receivables']
        df['Equity Ratio'] = df['Stockholders Equity'] / df['Total Assets']

        df = df.drop_duplicates(subset=['symbol', 'year'])


        # Restituisco solo le colonne richieste, se esistono
        kpi_cols = ['symbol', 'year', 'description', 'Gross Margin', 'Operating Margin', 'Net Margin', 'EBITDA Margin',
                    'ROA', 'ROE', 'ROIC', 'Debt/Equity', 'Tax Rate',
                    'SG&A/Revenue', 'R&D/Revenue', 'FCF Margin', 'Working Capital/Revenue', 'Asset Turnover', 'Equity Ratio']

        # Per sicurezza, filtriamo solo colonne esistenti
        kpi_cols_present = [col for col in kpi_cols if col in df.columns]

        return df[kpi_cols_present]

    except Exception as e:
        print(f"Errore nel calcolo dei KPI: {e}")
        return pd.DataFrame()


def get_or_fetch_data(symbol, years, description, stock_exchange):
    print(f"get_or_fetch_data chiamata per {symbol} anni {years}", flush=True)
    db_data = load_from_db(symbol, years)

    final_data = []
    years_to_fetch = []

    for i, year in enumerate(years):
        record = db_data[i]
        if isinstance(record, dict) and record:
            print(f"Dati da DB per {symbol} anno {year} trovati.", flush=True)
            record['description'] = description
            record['stock_exchange'] = stock_exchange
            final_data.append(record)
        else:
            print(f"Dati da DB per {symbol} anno {year} MANCANTI, da scaricare.", flush=True)
            years_to_fetch.append(year)

    if years_to_fetch:
        print(f"Scarico dati per {symbol} anni: {years_to_fetch}", flush=True)
        fetched_data = get_financial_data(symbol, years_to_fetch, description=description, stock_exchange=stock_exchange)

        valid_data = []

        for i, data in enumerate(fetched_data):
            if isinstance(data, dict) and data:
                data_year = data.get("year")
                expected_year = years_to_fetch[i]

                if data_year == expected_year:
                    print(f"Dati scaricati validi per {symbol} anno {expected_year}", flush=True)
                    data['description'] = description
                    data['stock_exchange'] = stock_exchange
                    final_data.append(data)
                    valid_data.append(data)
                else:
                    print(f"⚠️ ATTENZIONE: Anno nei dati = {data_year}, ma ci si aspettava {expected_year}. Dato SCARTATO.", flush=True)
            else:
                print(f"Dati scaricati NON validi per {symbol} anno {years_to_fetch[i]}", flush=True)

        if valid_data:
            print(f"Salvo dati nuovi nel DB per {symbol} anni {[d['year'] for d in valid_data]}", flush=True)
            save_to_db(symbol, [d['year'] for d in valid_data], valid_data)
        else:
            print(f"Nessun dato valido da salvare per {symbol}", flush=True)

    return final_data






if __name__ == '__main__':
    main()

