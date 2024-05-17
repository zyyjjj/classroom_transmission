import numpy as np
import pandas as pd
import datetime
from datetime import date

def process_class_schedule_data(semester):

    if semester == "fa21":
        read_path = 'G:/Data_Peter/classroom_transmission/data/data_fa21/class_schedule_fa21.xlsx'
        write_path = 'G:/Data_Peter/classroom_transmission/data/data_fa21/class_schedule_fa21.csv'
    elif semester == "sp22":
        read_path = 'G:/Data_Peter/classroom_transmission/data/data_sp22/class_schedule_sp22.xlsx'
        write_path = 'G:/Data_Peter/classroom_transmission/data/data_sp22/class_schedule_sp22.csv'

    courses = pd.read_excel(read_path)

    schedule_data = courses[['Session','Subject','Catalog','Section','Class Start Date','Class End Date','Mtg Start Date','Mtg End Date','Mtg Start Time','Mtg End Time','Meeting Days','Facil ID']]
    schedule_data = schedule_data[~(schedule_data['Facil ID'].isna())&~(schedule_data['Facil ID'] == 'ONLINE')&~(schedule_data['Subject'] == 'PE')]

    # Handle TBA and 25L classes
    idx = 0
    for i in schedule_data.index:
        if schedule_data.loc[i, 'Facil ID'] == 'TBA' or schedule_data.loc[i, 'Facil ID'] == '25L':
            schedule_data.loc[i, 'Facil ID'] = 'Room' + str(idx)
            idx += 1

    schedule_csv = schedule_data.reset_index(drop = True)

    schedule_csv["daily_class_hours"] = 0
    schedule_csv["1"] = 0 # Monday
    schedule_csv["2"] = 0 # Tuesday
    schedule_csv["3"] = 0 # Wednesday
    schedule_csv["4"] = 0 # Thursday
    schedule_csv["5"] = 0 # Friday
    schedule_csv["6"] = 0 # Saturday
    schedule_csv["7"] = 0 # Sunday

    for i in range(len(schedule_csv)):
        meet_day = schedule_csv.loc[i, 'Meeting Days']
        start = schedule_csv.loc[i, 'Mtg Start Time']
        end = schedule_csv.loc[i, 'Mtg End Time']
        if pd.isna(meet_day):
            meet_day = 'MTWRF'
            schedule_csv.loc[i, 'Meeting Days'] = 'MTWRF'
            schedule_csv.loc[i, 'daily_class_hours'] = 0.5
        if 'M' in meet_day:
            schedule_csv.loc[i, '1'] = 1
        if 'T' in meet_day:
            schedule_csv.loc[i, '2'] = 1
        if 'W' in meet_day:
            schedule_csv.loc[i, '3'] = 1
        if 'R' in meet_day:
            schedule_csv.loc[i, '4'] = 1
        if 'F' in meet_day:
            schedule_csv.loc[i, '5'] = 1
        if 'S' in meet_day:
            schedule_csv.loc[i, '6'] = 1
        if 'U' in meet_day:
            schedule_csv.loc[i, '7'] = 1
        if pd.isna(start) and pd.isna(end):
            schedule_csv.loc[i, 'Mtg Start Time'] = datetime.time(0, 0)
            schedule_csv.loc[i, 'Mtg End Time'] = datetime.time(0, 0)
        else:
            delta = datetime.datetime.combine(date.today(), end) - datetime.datetime.combine(date.today(), start)
            schedule_csv.loc[i, 'daily_class_hours'] = delta / datetime.timedelta(hours=1)
        
        # If daily class hours is still 0, impute to 0.5
        if schedule_csv.loc[i, 'daily_class_hours'] == 0:
            schedule_csv.loc[i, 'daily_class_hours'] = 0.5

    schedule_csv.to_csv(write_path)

