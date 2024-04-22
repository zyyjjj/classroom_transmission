import datetime as dt


# utility functions to map between actual date and regression time index

def date_to_reg_time_fa21(date, start_date = dt.date(2021, 8, 26)):
    return (date - start_date).days

def date_to_reg_time_sp22(date, start_date = dt.date(2022, 2, 7)):
    return (date - start_date).days

def string_to_date(date_str):
    if date_str is not None:
        return dt.datetime.strptime(date_str[:10], '%Y-%m-%d').date()
