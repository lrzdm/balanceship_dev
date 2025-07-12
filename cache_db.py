import os
import json
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, String, Text, Integer
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.orm import Session
import math

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cache_db")

# Base ORM
Base = declarative_base()

# Engine di DB
if os.environ.get("STREAMLIT_CLOUD") == "1":
    DATABASE_URL = os.environ.get("DATABASE_URL")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite:///data/financials_db.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

Session = scoped_session(sessionmaker(bind=engine))

# Modelli tabella
#class FinancialCache(Base):
#    __tablename__ = 'cache'
#    id = Column(Integer, primary_key=True)
#    symbol = Column(String, index=True)
#    year = Column(Integer, index=True)
#    data_json = Column(Text)

class FinancialCache(Base):
    __tablename__ = 'cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, index=True)
    year = Column(Integer, index=True)
    data_json = Column(String)  # o JSON se usi PostgreSQL con JSONB
    
class KPICache(Base):
    __tablename__ = 'kpi_cache'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    description = Column(String, index=True, nullable=True)
    year = Column(Integer, index=True)
    kpi_json = Column(Text)

def create_tables():
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    logger.info("✅ Tabelle create o già esistenti.")


#def convert_numpy(obj):
#    if isinstance(obj, dict):
#        return {k: convert_numpy(v) for k, v in obj.items()}
#    elif isinstance(obj, list):
#        return [convert_numpy(v) for v in obj]
#    elif isinstance(obj, (np.floating, float)):
#        if np.isnan(obj) or obj != obj:
#            return None
#        return float(obj)
#    elif isinstance(obj, (np.integer, int)):
#        return int(obj)
#    elif obj is None:
#        return None
#    else:
#        return obj

def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif obj is None:
        return None
    else:
        return obj

def save_to_db(symbol, years, data_list):
    session = Session()
    try:
        for i, year in enumerate(years):
            year_int = int(year)

            # Salta se il dato manca o è malformato
            if i >= len(data_list) or not isinstance(data_list[i], dict) or not data_list[i]:
                logger.debug(f"Salvataggio SKIPPED per {symbol} anno {year}: no data.")
                continue

            data_for_year = data_list[i]

            # Validazione dell'anno nei dati
            data_year = data_for_year.get("year")
            if data_year != year_int:
                logger.warning(f"❌ Mismatch anno nei dati per {symbol}: atteso {year_int}, trovato {data_year}. Salvataggio saltato.")
                continue

            # Conversione dati e serializzazione JSON
            data_for_year = convert_numpy(data_for_year)
            json_data = json.dumps(data_for_year, ensure_ascii=False, allow_nan=False)

            entry = session.query(FinancialCache).filter_by(symbol=symbol, year=year_int).first()
            if entry:
                if entry.data_json != json_data:
                    entry.data_json = json_data
                    logger.info(f"Aggiornato FinancialCache per {symbol} anno {year_int}")
                else:
                    logger.debug(f"Nessuna modifica per {symbol} anno {year_int}")
            else:
                entry = FinancialCache(symbol=symbol, year=year_int, data_json=json_data)
                session.add(entry)
                logger.info(f"Inserito FinancialCache per {symbol} anno {year_int}")

        session.commit()
    except Exception as e:
        logger.error(f"Errore salvataggio FinancialCache: {e}")
        session.rollback()
        raise
    finally:
        session.close()



def load_from_db(symbol, years):
    session = Session()
    try:
        query = session.query(FinancialCache).filter(
            FinancialCache.symbol == symbol,
            FinancialCache.year.in_([int(y) for y in years])
        )
        results = query.all()
        
        data_by_year = {}
        for row in results:
            try:
                if isinstance(row.data_json, dict):
                    parsed = row.data_json
                else:
                    parsed = json.loads(row.data_json)
                parsed['year'] = row.year
                data_by_year[row.year] = parsed
            except Exception as e:
                print(f"Errore nel parsing DB per {symbol} {row.year}: {e}")
                data_by_year[row.year] = None
        
        data = [data_by_year.get(int(year), None) for year in years]
        
        return data
    except Exception as e:
        print(f"Errore durante il caricamento da DB per {symbol}: {e}")
        return [None] * len(years)
    finally:
        session.close()

def load_many_from_db(symbols, years):
    session = Session()
    try:
        query = session.query(FinancialCache).filter(
            FinancialCache.symbol.in_(symbols),
            FinancialCache.year.in_([int(y) for y in years])
        )
        results = query.all()

        data_by_symbol_year = {}
        for row in results:
            try:
                parsed = json.loads(row.data_json) if isinstance(row.data_json, str) else row.data_json
                parsed['year'] = row.year
                data_by_symbol_year[(row.symbol, row.year)] = parsed
            except Exception as e:
                print(f"Errore parsing {row.symbol}-{row.year}: {e}")
                data_by_symbol_year[(row.symbol, row.year)] = None

        return data_by_symbol_year

    except Exception as e:
        print(f"Errore batch load: {e}")
        return {}
    finally:
        session.close()

#-------------------------------------------------------------

def save_kpis_to_db(kpi_df):
    session = Session()
    try:
        for _, row in kpi_df.iterrows():
            symbol = row['symbol']
            year = int(row['year'])

            # Controlla solo su symbol + year, IGNORA description per decidere se esiste
            exists = session.query(KPICache).filter_by(symbol=symbol, year=year).first()
            if exists:
                # La combinazione esiste già, NON FARE NULLA
                logger.info(f"Record già esistente per {symbol} anno {year}, salto inserimento")
                continue

            # Se non esiste, inserisci nuova riga (con description anche se è NULL)
            desc = row.get('description', None)

            data = row.drop(['symbol','year','description'], errors='ignore').to_dict()
            data = convert_numpy(data)
            json_data = json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True)

            entry = KPICache(symbol=symbol, year=year, description=desc, kpi_json=json_data)
            session.add(entry)
            logger.info(f"Inserito KPICache per {symbol} anno {year}")

        session.commit()
    except Exception as e:
        logger.error(f"Errore salvataggio KPICache: {e}")
        session.rollback()
        raise
    finally:
        session.close()



def load_kpis_for_symbol_year(symbol, year, description=None):
    session = Session()
    try:
        query = session.query(KPICache).filter_by(symbol=symbol, year=year)
        if description is not None:
            query = query.filter_by(description=description)
        entry = query.first()
        if entry:
            if isinstance(entry.kpi_json, str):
                data = json.loads(entry.kpi_json)
            elif isinstance(entry.kpi_json, dict):
                data = entry.kpi_json
            else:
                raise ValueError(f"Formato inatteso in kpi_json: {type(entry.kpi_json)}")
            data.update({'symbol': entry.symbol, 'year': entry.year, 'description': entry.description})
            return pd.DataFrame([data])
        else:
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Errore caricamento KPICache per {symbol} {year}: {e}")
        return pd.DataFrame()
    finally:
        session.close()

def load_all_kpis():
    session = Session()
    try:
        entries = session.query(KPICache).all()
        if not entries:
            return pd.DataFrame()
        rows = []
        for entry in entries:
            try:
                if isinstance(entry.kpi_json, str):
                    data = json.loads(entry.kpi_json)
                elif isinstance(entry.kpi_json, dict):
                    data = entry.kpi_json
                else:
                    # Prova a convertire a stringa prima di json.loads
                    try:
                        json_str = str(entry.kpi_json)
                        data = json.loads(json_str)
                    except Exception:
                        raise ValueError(f"Formato inatteso in kpi_json: {type(entry.kpi_json)}")

            except Exception as e:
                logger.error(f"Errore parsing JSON per {entry.symbol} {entry.year}: {e}")
                continue
            data.update({'symbol': entry.symbol, 'year': entry.year, 'description': entry.description})
            rows.append(data)
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Errore caricamento tutti i KPI: {e}")
        return pd.DataFrame()
    finally:
        session.close()

