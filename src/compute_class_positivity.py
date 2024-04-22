import numpy as np
import datetime as dt
import pandas as pd
from utils import date_to_reg_time_fa21, date_to_reg_time_sp22, string_to_date

"""
Use separate functions for each semester because the data have subtle differences.
"""

def compute_class_positivity_fa21(T_e=7, T_a=7):

    # load student features and class registration data
    all_students_classes = pd.read_csv('../data/data_fa21/class_registration_fa21.csv')
    all_students_classes.drop_duplicates(inplace = True)
    all_students_features = pd.read_csv('../data/data_fa21/study_population_finalized_fa21.csv', index_col = 0) 
    positive_students = all_students_features[all_students_features["infected_on_this_day"]==1].reset_index(drop=True)

    # load and process class schedule
    class_schedule = pd.read_csv('../data/data_fa21/class_schedule_fa21.csv', index_col = 0)
    enrollment = pd.read_csv('../data/data_fa21/class_registration_fa21.csv', index_col = 0)
    enrollment = enrollment.reset_index(drop = True)
    class_schedule_enrollment = enrollment[['subject', 'catalog_nbr', 'class_section', 'class_enroll_tot']].drop_duplicates()
    class_schedule['Section'] = class_schedule['Section'].astype('string')
    # strip leading zeros
    class_schedule['Section'] = class_schedule['Section'].str.lstrip("0")
    class_schedule_enrollment.rename(columns = {'subject':'Subject', 'catalog_nbr':'Catalog', 'class_section':'Section'}, inplace = True)

    # Create enrollment column
    class_schedule = class_schedule.merge(class_schedule_enrollment, how = 'left', on = ['Subject', 'Catalog', 'Section'])
    class_schedule['class_enroll_tot'] = class_schedule['class_enroll_tot'].fillna(0)
    class_schedule.rename(columns = {'Subject':'SUBJECT', 'Catalog':'CATALOG_NBR', 'Section':'CLASS_SECTION', 'Facil ID': 'room', 'Mtg Start Time': 'mtgstarttime', 'Mtg End Time': 'mtgendtime', 'Meeting Days': 'meetingdays'}, inplace = True)

    # Create a dataframe to store a history of positive hours per class
    reg_length = len(all_students_features['day_idx'].drop_duplicates())
    class_prevalence_columns = ['room', 'mtgstarttime', 'mtgendtime', 'meetingdays', 'daily_class_hours','enrollment']
    class_prevalence_columns.extend([str(t) for t in np.arange(reg_length+1)])
    class_positive_hours = pd.DataFrame(columns = class_prevalence_columns)

    # If a class section ever had a positive, create an array for it
    # if not, no need to keep an array for it
    for i in range(len(positive_students)):
        # Get emplid for positive student (lowercase, without '0x')
        emplid = positive_students['employee_id_hash'][i]
        
        # Get set of classes this student is registered for
        students_classes = all_students_classes.loc[all_students_classes['employee_id_hash']==emplid].reset_index(drop=True)
        
        # Obtain notification date of positive test (if null, then ignore)
        if positive_students.loc[i][['hd_notify_date']].isnull().any():
            break
        notify_date = dt.datetime.strptime(positive_students['hd_notify_date'][i][:10], '%Y-%m-%d').date()
        
        # Then, map the notify date to the regression time index and day of the week
        notify_reg_time = date_to_reg_time_fa21(notify_date)
        notify_day_of_week = notify_date.isoweekday()
        
        for j in range(len(students_classes)):
            # Fall 2021: 7W1 classes from Aug 26 - October 19; 7W2 classes from October 20 - Dec 7
            
            # Get room, meeting time, meeting schedule, and class enrollment for the class
            subject_, catalog_, section_, enrollment_ = students_classes.loc[j][
                ['subject', 'catalog_nbr', 'class_section', 'class_enroll_tot']]
            if students_classes.loc[j][['subject', 'catalog_nbr', 'class_section']].isnull().any():
                continue 
            
            # Locate the bucket for this class
            class_ = class_schedule.query(
                'SUBJECT == @subject_ & CATALOG_NBR == @catalog_ & CLASS_SECTION == @section_ ')
            # If mapped to multiple buckets, just get the first one (impossible)
            if len(class_)>1:
                class_ = class_.head(1)
            # If mapped to no buckets (online, PE, or 7W2 class), ignore
            if len(class_) == 0:
                continue
            class_.reset_index(inplace = True)

            # If daily class hours information exists, use it. Otherwise, impute as 0.5.
            if not class_['daily_class_hours'].empty:
                daily_class_hours_ = class_['daily_class_hours'].values[0]
            else:
                daily_class_hours_ = 0.5        

            session_ = class_.loc[0, 'Session']
            if (session_ == '7W1' and notify_reg_time >= date_to_reg_time_fa21(dt.date(2021, 10, 20))) or (session_ == '7W2' and notify_reg_time < date_to_reg_time_fa21(dt.date(2021, 10, 20))):
                continue
            
            # Get room, start, end, and meeting days for this bucket
            room_, mtgstarttime_, mtgendtime_, meetingdays_, enrollment_ = class_['room'].values[0], class_['mtgstarttime'].values[0], class_['mtgendtime'].values[0], class_['meetingdays'].values[0], class_['class_enroll_tot'].values[0]
            
            cph_query = class_positive_hours.query('room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')
            if cph_query.empty:
                # Calculate correct enrollment value of all classes that match the room, start, end, and meetingdays.
                # First, get list of other classes that share the same room and time (cross-listed)
                other_classes = class_schedule.query(
                    'room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')[
                ['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION', 'class_enroll_tot']]
                # Drop duplicate subject, catalog, and section combinations
                other_classes.drop_duplicates(subset = ['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION'], inplace = True)
                # Aggregate enrollment values of these classes
                enrollment_ = other_classes['class_enroll_tot'].sum()
                class_positive_hours = pd.concat([class_positive_hours, pd.DataFrame([[room_, mtgstarttime_, mtgendtime_, meetingdays_, daily_class_hours_, enrollment_]], 
                                    columns=['room', 'mtgstarttime', 'mtgendtime', 'meetingdays', 'daily_class_hours','enrollment'])])
                
            class_positive_hours.reset_index(drop=True, inplace = True)
            class_positive_hours.fillna(0, inplace = True)
            class_index = class_positive_hours.index[(class_positive_hours['room']==room_)
                                        & (class_positive_hours['mtgstarttime']==mtgstarttime_)
                                        & (class_positive_hours['mtgendtime'] == mtgendtime_)
                                        & (class_positive_hours['meetingdays'] == meetingdays_)] 
            weekly_meeting_times = class_[['1','2','3','4','5','6','7']].reset_index(drop=True)
            
            if class_.empty:    
                for day_idx in range(1,6):
                    weekly_meeting_times.loc[0, day_idx] = 1
                for day_idx in [6,7]:
                    weekly_meeting_times.loc[0, day_idx] = 0
            
            # distribute to previous T_a days, only to days on which the class meets
            # also log class enrollment
            for tau in range(min(T_a, notify_reg_time)):
                prev_reg_time = notify_reg_time - tau
                prev_day_of_week = (notify_day_of_week - tau) % 7
                if prev_day_of_week == 0:
                    prev_day_of_week = 7
                if weekly_meeting_times[str(prev_day_of_week)].values[0]==1:
                    class_positive_hours.at[class_index.values[0], str(prev_reg_time)] += 1

    # Compute classroom exposure per student per day
    student_ids = all_students_features[['employee_id_hash']].drop_duplicates().reset_index(drop=True)
    agg_daily_class_prevalence = pd.Series([])
    agg_daily_class_prevalence_dict = {}

    for i in range(len(student_ids)):
        is_positive = 0
        emplid = student_ids['employee_id_hash'][i]
        student_classes = all_students_classes.loc[all_students_classes['employee_id_hash']==emplid].reset_index(drop=True)
        student_history_length = len(all_students_features.query('employee_id_hash == @emplid'))
        agg_class_prevalence = pd.DataFrame(columns = [str(t) for t in np.arange(student_history_length)])

        # in Fall 2021, 0xDAFE5A62C2ED7146DC420A05834847CB has two hd_notify_dates, 9/1 and 12/1
        if str(emplid) in positive_students['employee_id_hash'].values:
            is_positive = 1
            hd_notify_date = min(positive_students[positive_students['employee_id_hash']==str(emplid)]['hd_notify_date'])
            hd_notify_reg_time = date_to_reg_time_fa21(string_to_date(hd_notify_date))

        for j in range(len(student_classes)):
            subject_, catalog_, section_ = student_classes.loc[j][
                ['subject', 'catalog_nbr', 'class_section']]
            if subject_ is None or catalog_ is None or section_ is None:
                continue
            class_ = class_schedule.query(
                'SUBJECT == @subject_ & CATALOG_NBR == @catalog_ & CLASS_SECTION == @section_ ')
            if len(class_) == 0:
                continue
            
            room_, mtgstarttime_, mtgendtime_, meetingdays_ = class_['room'].values[0], class_['mtgstarttime'].values[0], class_['mtgendtime'].values[0], class_['meetingdays'].values[0]
            class_positive_history = class_positive_hours.query('room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')
                        
            if not class_positive_history.empty:
                
                enrollment_count = class_positive_history['enrollment'].values[0]
                daily_class_hours = class_positive_history['daily_class_hours'].values[0]
                
                # if the student was ever positive, when computing positivity (positive person-hour divided by # other students)
                # case 1: if within the active period (hd_date-T_a, hd_date), subtract the student him/herself from the numerator 
                # case 2: if before the active period, i.e., before hd_date-T_a, no need to substract oneself from the numerator 
                if is_positive == 1:
                    # if identified within T_e days of start of study period, only case 1
                    if hd_notify_reg_time <= T_e-1:
                        pre_notify_prev_history = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time+1)]] - 1) / (enrollment_count-1)
                    # otherwise, consider both case 1 and case 2 and concatenate the results
                    else:
                        pre_notify_prev_history_1 = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time-T_a+1)]]) / (enrollment_count-1)
                        pre_notify_prev_history_2 = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time-T_a+1, hd_notify_reg_time+1)]] - 1) / (enrollment_count-1)
                    
                        pre_notify_prev_history = pd.concat([pre_notify_prev_history_1, pre_notify_prev_history_2], axis=1)
                    class_prevalence_history = pre_notify_prev_history
                    class_prevalence_history[class_prevalence_history < 0] = 0
                    class_prevalence_history.replace([np.inf], 0, inplace = True)
                    
                else:
                    class_prevalence_history = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(student_history_length)]]) / (enrollment_count-1)
                    
                agg_class_prevalence = pd.concat([agg_class_prevalence, class_prevalence_history], ignore_index=True)

        # aggregate class positivity over rows (different classes)
        agg_sum = agg_class_prevalence.sum(axis=0).to_frame().reset_index(drop=True)
        # then aggregate over the previous T_e days
        agg_sum_sliding_window = []
        for k in range(len(agg_sum)):
            agg_sum_sliding_window.append(agg_sum[max(0, k-T_e) : k].sum()[0])
        agg_sum_sliding_window = pd.Series(agg_sum_sliding_window)
        agg_daily_class_prevalence = pd.concat([agg_daily_class_prevalence,agg_sum_sliding_window]).reset_index(drop=True)
        agg_daily_class_prevalence_dict[emplid] = (student_history_length, len(agg_sum), len(agg_sum_sliding_window))

    all_students_features.reset_index(inplace=True, drop=True)
    all_students_features["class_positivity"] = agg_daily_class_prevalence

    # drop the non-surveilled and NAP individuals
    all_students_features = all_students_features[all_students_features["include"]==True]
    all_students_features.reset_index(inplace=True, drop=True)

    # NEEDED? compute campus positivity



    all_students_features.to_csv(f"../data/data_fa21/all_students_features_T_e={T_e}_finalized.csv")






def compute_class_positivity_sp22(T_e=7, T_a=7):

    # load student features and class registration data
    all_students_classes = pd.read_csv('../data/data_sp22/class_registration_sp22.csv', index_col = 0)
    all_students_classes.drop_duplicates(inplace = True)
    all_students_features = pd.read_csv('../data/data_sp22/study_population_finalized_sp22.csv', index_col = 0) 
    positive_students = all_students_features[all_students_features["infected_on_this_day"]==1].reset_index(drop=True)

    # load and process class schedule
    class_schedule = pd.read_csv('../data/data_sp22/class_schedule_sp22.csv', index_col = 0)
    class_schedule_enrollment = pd.read_csv('../data/simulated_schedule_data_SP22.csv', index_col = 0)[['SUBJECT','CATALOG_NBR','CLASS_SECTION','CLASS_ENROLL_TOT']]
    class_schedule['Section'] = class_schedule['Section'].astype('string')
    # strip leading zeros
    class_schedule['Section'] = class_schedule['Section'].str.lstrip("0")
    class_schedule_enrollment.rename(columns = {'SUBJECT':'Subject', 'CATALOG_NBR':'Catalog', 'CLASS_SECTION':'Section'}, inplace = True)

    # Create enrollment column
    class_schedule = class_schedule.merge(class_schedule_enrollment, how = 'left', on = ['Subject', 'Catalog', 'Section'])
    class_schedule['CLASS_ENROLL_TOT'] = class_schedule['CLASS_ENROLL_TOT'].fillna(0)
    class_schedule.rename(columns = {'Subject':'SUBJECT', 'Catalog':'CATALOG_NBR', 'Section':'CLASS_SECTION', 'Facil ID': 'room', 'Mtg Start Time': 'mtgstarttime', 'Mtg End Time': 'mtgendtime', 'Meeting Days': 'meetingdays'}, inplace = True)

    # Create a dataframe to store a history of positive hours per class
    reg_length = len(all_students_features['day_idx'].drop_duplicates())
    class_prevalence_columns = ['room', 'mtgstarttime', 'mtgendtime', 'meetingdays', 'daily_class_hours','enrollment']
    class_prevalence_columns.extend([str(t) for t in np.arange(reg_length+1)])
    class_positive_hours = pd.DataFrame(columns = class_prevalence_columns)

    # If a class section ever had a positive, create an array for it
    # if not, no need to keep an array for it
    for i in range(len(positive_students)):
        # Get emplid for positive student (lowercase, without '0x')
        emplid = positive_students['employee_id_hash'][i].lower()[2:]
        
        # Get set of classes this student is registered for
        students_classes = all_students_classes.loc[all_students_classes['EMPLOYEE_ID_STDNT_HASH']==emplid].reset_index(drop=True)
        
        # Obtain notification date of positive test (if null, then ignore)
        if positive_students.loc[i][['hd_notify_date']].isnull().any():
            break
        notify_date = dt.datetime.strptime(positive_students['hd_notify_date'][i][:10], '%Y-%m-%d').date()
        
        # Then, map the notify date to the regression time index and day of the week
        notify_reg_time = date_to_reg_time_sp22(notify_date)
        notify_day_of_week = notify_date.isoweekday()
        
        for j in range(len(students_classes)):
            
            # Get room, meeting time, meeting schedule, and class enrollment for the class
            session_, subject_, catalog_, section_, enrollment_ = students_classes.loc[j][
                ['SESSION_CODE', 'SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION', 'CLASS_ENROLL_TOT']]
            
            if students_classes.loc[j][['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION']].isnull().any():
                continue 
            
            if session_ in ['7W2', '4W2', '4W3', '4W4', '8WCS', '8WCs']:
                continue
            
            # Locate the bucket for this class
            class_ = class_schedule.query(
                'Session == @session_ & SUBJECT == @subject_ & CATALOG_NBR == @catalog_ & CLASS_SECTION == @section_ ')
            # If mapped to multiple buckets, just get the first one (impossible)
            if len(class_)>1:
                class_ = class_.head(1)
            # If mapped to no buckets (online, PE, or 7W2 class), ignore
            if len(class_) == 0:
                continue
            # If daily class hours information exists, use it. Otherwise, impute as 0.5.
            if not class_['daily_class_hours'].empty:
                daily_class_hours_ = class_['daily_class_hours'].values[0]
            else:
                daily_class_hours_ = 0.5        
            
            # Get room, start, end, and meeting days for this bucket
            room_, mtgstarttime_, mtgendtime_, meetingdays_, enrollment_ = class_['room'].values[0], class_['mtgstarttime'].values[0], class_['mtgendtime'].values[0], class_['meetingdays'].values[0], class_['CLASS_ENROLL_TOT'].values[0]
            
            cph_query = class_positive_hours.query('room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')
            if cph_query.empty:
                # Calculate correct enrollment value of all classes that match the room, start, end, and meetingdays.
                # First, get list of other classes that share the same room and time (cross-listed)
                other_classes = class_schedule.query(
                    'room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')[
                ['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION', 'CLASS_ENROLL_TOT']]
                # Drop duplicate subject, catalog, and section combinations
                other_classes.drop_duplicates(subset = ['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION'], inplace = True)
                # Aggregate enrollment values of these classes
                enrollment_ = other_classes['CLASS_ENROLL_TOT'].sum()
                class_positive_hours = pd.concat([class_positive_hours, pd.DataFrame([[room_, mtgstarttime_, mtgendtime_, meetingdays_, daily_class_hours_, enrollment_]], 
                                    columns=['room', 'mtgstarttime', 'mtgendtime', 'meetingdays', 'daily_class_hours','enrollment'])])
                
            class_positive_hours.reset_index(drop=True, inplace = True)
            class_positive_hours.fillna(0, inplace = True)
            class_index = class_positive_hours.index[(class_positive_hours['room']==room_)
                                        & (class_positive_hours['mtgstarttime']==mtgstarttime_)
                                        & (class_positive_hours['mtgendtime'] == mtgendtime_)
                                        & (class_positive_hours['meetingdays'] == meetingdays_)] 
            weekly_meeting_times = class_[['1','2','3','4','5','6','7']].reset_index(drop=True)
            
            if class_.empty:    
                for day_idx in range(1,6):
                    weekly_meeting_times.loc[0, day_idx] = 1
                for day_idx in [6,7]:
                    weekly_meeting_times.loc[0, day_idx] = 0
            
            # distribute to previous T_a days, only to days on which the class meets
            # also log class enrollment
            for tau in range(min(T_a, notify_reg_time)):
                prev_reg_time = notify_reg_time - tau
                prev_day_of_week = (notify_day_of_week - tau) % 7
                if prev_day_of_week == 0:
                    prev_day_of_week = 7
                if weekly_meeting_times[str(prev_day_of_week)].values[0]==1:
                    class_positive_hours.at[class_index.values[0], str(prev_reg_time)] += 1

    # Compute classroom exposure per student per day
    student_ids = all_students_features[['employee_id_hash']].drop_duplicates().reset_index(drop=True)
    agg_daily_class_prevalence = pd.Series([])
    agg_daily_class_prevalence_dict = {}

    for i in range(len(student_ids)):
        is_positive = 0
        emplid = student_ids['employee_id_hash'][i]
        student_classes = all_students_classes.loc[all_students_classes['EMPLOYEE_ID_STDNT_HASH']==emplid.lower()[2:]].reset_index(drop=True)
        student_history_length = len(all_students_features.query('employee_id_hash == @emplid'))
        agg_class_prevalence = pd.DataFrame(columns = [str(t) for t in np.arange(student_history_length)])

        if str(emplid) in positive_students['employee_id_hash'].values:
            is_positive = 1
            hd_notify_date = min(positive_students[positive_students['employee_id_hash']==str(emplid)]['hd_notify_date'])
            hd_notify_reg_time = date_to_reg_time_sp22(string_to_date(hd_notify_date))

        for j in range(len(student_classes)):
            subject_, catalog_, section_ = student_classes.loc[j][
                ['SUBJECT', 'CATALOG_NBR', 'CLASS_SECTION']]
            if subject_ is None or catalog_ is None or section_ is None:
                continue
            class_ = class_schedule.query(
                'SUBJECT == @subject_ & CATALOG_NBR == @catalog_ & CLASS_SECTION == @section_ ')
            if len(class_) == 0:
                continue
            
            room_, mtgstarttime_, mtgendtime_, meetingdays_ = class_['room'].values[0], class_['mtgstarttime'].values[0], class_['mtgendtime'].values[0], class_['meetingdays'].values[0]
            class_positive_history = class_positive_hours.query('room == @room_ & mtgstarttime == @mtgstarttime_ & mtgendtime == @mtgendtime_ & meetingdays == @meetingdays_')
                        
            if not class_positive_history.empty:
                
                enrollment_count = class_positive_history['enrollment'].values[0]
                daily_class_hours = class_positive_history['daily_class_hours'].values[0]
                
                # if the student was ever positive, when computing positivity (positive person-hour divided by # other students)
                # case 1: if within the active period (hd_date-T_a, hd_date), subtract the student him/herself from the numerator 
                # case 2: if before the active period, i.e., before hd_date-T_a, no need to substract oneself from the numerator 
                if is_positive == 1:
                    # if identified within T_e days of start of study period, only case 1
                    if hd_notify_reg_time <= T_e-1:
                        pre_notify_prev_history = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time+1)]] - 1) / (enrollment_count-1)
                    # otherwise, consider both case 1 and case 2 and concatenate the results
                    else:
                        pre_notify_prev_history_1 = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time-T_a+1)]]) / (enrollment_count-1)
                        pre_notify_prev_history_2 = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(hd_notify_reg_time-T_a+1, hd_notify_reg_time+1)]] - 1) / (enrollment_count-1)
                    
                        pre_notify_prev_history = pd.concat([pre_notify_prev_history_1, pre_notify_prev_history_2], axis=1)
                    class_prevalence_history = pre_notify_prev_history
                    class_prevalence_history[class_prevalence_history < 0] = 0
                    class_prevalence_history.replace([np.inf], 0, inplace = True)
                    
                else:
                    class_prevalence_history = daily_class_hours * \
                            (class_positive_history[[str(t) for t in np.arange(student_history_length)]]) / (enrollment_count-1)
                    
                agg_class_prevalence = pd.concat([agg_class_prevalence, class_prevalence_history], ignore_index=True)

        # aggregate class positivity over rows (different classes)
        agg_sum = agg_class_prevalence.sum(axis=0).to_frame().reset_index(drop=True)
        # then aggregate over the previous T_e days
        agg_sum_sliding_window = []
        for k in range(len(agg_sum)):
            agg_sum_sliding_window.append(agg_sum[max(0, k-T_e) : k].sum()[0])
        agg_sum_sliding_window = pd.Series(agg_sum_sliding_window)
        agg_daily_class_prevalence = pd.concat([agg_daily_class_prevalence,agg_sum_sliding_window]).reset_index(drop=True)
        agg_daily_class_prevalence_dict[emplid] = (student_history_length, len(agg_sum), len(agg_sum_sliding_window))

    all_students_features.reset_index(inplace=True, drop=True)
    all_students_features["class_positivity"] = agg_daily_class_prevalence

    # drop the non-surveilled and NAP individuals
    all_students_features = all_students_features[all_students_features["include"]==True]
    all_students_features.reset_index(inplace=True, drop=True)

    # NEEDED? compute campus positivity


    all_students_features.to_csv(f"../data/data_sp22/all_students_features_T_e={T_e}_finalized.csv")
