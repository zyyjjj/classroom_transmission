import pandas as pd
import numpy as np
import datetime as dt
from utils import string_to_date

def generate_study_population_fa21():

    oncampus_fa21 = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_fa21/on_campus_student_days_fa21.csv")

    # drop individuals with unknown sex
    study_population = oncampus_fa21[(oncampus_fa21["current_gender"]!="U")]
    
    # drop individuals not enrolled in classes
    class_registrations = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_fa21/class_registration_fa21.csv")
    class_registrations.drop_duplicates(inplace=True, ignore_index=True)
    enrolled_ids = class_registrations[
        (~class_registrations["subject"].isna())
        & (class_registrations["subject"]!="PE")
    ]["employee_id_hash"].unique()
    study_population = study_population[study_population["employee_id_hash"].isin(enrolled_ids)].reset_index(drop=True)

    # mark individuals who (1) participate in surveillance testing and
    # (2) are not no-action-positive as to be included;
    # we do not drop them for now because they contribute to class_positivity
    surv_tests_fa21_raw = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_fa21/surveillance_tests_fa21.csv")
    cmc_test_ids_to_drop = [
        'CHANGE_LEVEL', 'NAPPED-EXCLUDE', 'NITH', 'RESET DEPARTURE', 'NOT_TESTED',
        'EXEMPT-CH', 'testing-pause-workday', 'EXEMPT-red', 'EXEMPT-NITH',
        'EXEMPT-access issue', 'EXEMPT-house fire', 'EXEMPT-SUPPLEMENTAL',
        'EXEMPT-hospital', 'TRAV-EXMP', 'TRVLEXMPT', 'EXEMPT', 'EXEMPT-ISO',
        'Exempt Did Test', 'Exemption to Change Test', 'EXEMPTION TESTING',
        'EXEMPT-CIW', 'EXEMPT -Travel', 'EXEMPT-LOA', 'Exemption',
        'Exemption Travel', 'EXEMPT-NAP',
    ]
    surv_tests_fa21 = surv_tests_fa21_raw[~surv_tests_fa21_raw["cmc_test_id"].isin(cmc_test_ids_to_drop)].reset_index(drop=True)
    surveilled_ids = surv_tests_fa21["emplid_id_hash"].unique()
    study_population["include"] = (study_population["employee_id_hash"].isin(surveilled_ids)) & (study_population["nap"]!=1)
    study_population.reset_index(drop=True, inplace=True)

    # truncate the person-days after a person's first identification date
    study_population['day_idx']=study_population['day_idx'].apply(lambda x: string_to_date(str(x)))
    study_population_ = study_population.copy()
    for emplid in study_population_['employee_id_hash'].unique():
        notify_dates = study_population_[study_population_["employee_id_hash"]==emplid]["hd_notify_date"].unique()
        if type(notify_dates[0]) == str: # str if nonempty, float(nan) if empty
            if len(notify_dates) > 1:
                notify_date = min(notify_dates)
                ind_drop_extra_dates = study_population_[(study_population_.employee_id_hash == emplid) &
                                        (study_population_.hd_notify_date>notify_date)].index
                study_population_.drop(ind_drop_extra_dates, inplace = True)
            student_history = study_population_.query('employee_id_hash == @emplid')
            last_day_pos = student_history.loc[student_history[student_history['infected_on_this_day']==1].last_valid_index()]['day_idx']
            last_day = student_history.loc[student_history.tail(1).index.item()]['day_idx']
            ind_drop_extra_records = study_population_[(study_population_.employee_id_hash == emplid) &
                                                        (study_population_.day_idx > last_day_pos) & 
                                                        (study_population_.day_idx <= last_day)].index
            study_population_.drop(ind_drop_extra_records, inplace = True)

    study_population_.reset_index(drop=True, inplace=True)

    # add academic_career info, including Greek/athlete membership
    old_features = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_fa21/1110_all_covariates_finalized.csv", index_col=0)
    academic_careers = old_features[["employee_id_hash","academic_career"]].drop_duplicates()
    study_population_ = study_population_.merge(
        academic_careers, 
        how = "left", 
        on = "employee_id_hash")
    greek_empids = pd.read_csv('G:/Data_Peter/classroom_transmission/data/data_fa21/hashed_greek_empIDs_fa21.csv', header=None)
    greek_empids = set(greek_empids[0])
    athlete_empids = pd.read_csv('G:/Data_Peter/classroom_transmission/data/data_fa21/hashed_athlete_empIDs_fa21.csv', header=None)
    athlete_empids = set(athlete_empids[0])
    for i in range(len(study_population_)):
        if study_population_.loc[i, 'employee_id_hash'] in greek_empids:
            study_population_.loc[i, 'academic_career'] = 'UG_G'
        elif study_population_.loc[i, 'employee_id_hash'] in athlete_empids:
            study_population_.loc[i, 'academic_career'] = 'UG_A'
        elif study_population_.at[i, 'academic_career'] in ('UG_G', 'UG_A', 'UG'):
            study_population_.at[i, 'academic_career'] = 'UG'
        else:
            continue

    # save data
    study_population_.to_csv("G:/Data_Peter/classroom_transmission/data/data_fa21/study_population_finalized_fa21.csv")


def generate_study_population_sp22():

    oncampus_sp22 = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_sp22/on_campus_student_days_sp22.csv")
    oncampus_sp22 = oncampus_sp22[oncampus_sp22["day_idx"] != '2022-02-21 00:00:00.000']

    # drop individuals with unknown sex
    study_population = oncampus_sp22[(oncampus_sp22["current_gender"]!="U")]

    # drop individuals not enrolled in classes
    class_registrations = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_sp22/class_registration_sp22.csv", index_col=0)
    class_registrations.drop_duplicates(inplace=True, ignore_index=True)
    class_registrations["EMPLOYEE_ID_STDNT_HASH"] = class_registrations["EMPLOYEE_ID_STDNT_HASH"].apply(lambda x: "0x"+x.upper())
    class_registrations_clean_1 = class_registrations.loc[
        (~class_registrations["SSR_COMPONENT"].isin(["RSC", "IND", "FLD"]))
        & (~class_registrations["SUBJ_OF_CRSE_OFFER_NBR1"].isin(["PE"]))
    ]
    enrolled_ids_1 = class_registrations_clean_1["EMPLOYEE_ID_STDNT_HASH"].unique()
    study_population = study_population[study_population["employee_id_hash"].isin(enrolled_ids_1)].reset_index(drop=True)

    # mark individuals who (1) participate in surveillance testing and
    # (2) are not no-action-positive as to be included;
    # we do not drop them for now because they contribute to class_positivity
    surv_tests_sp22_raw = pd.read_csv("G:/Data_Peter/classroom_transmission/data/data_sp22/surveillance_tests_sp22.csv")
    cmc_test_ids_to_drop = [
        'CHANGE_LEVEL', 'NAPPED-EXCLUDE', 'ARRIVAL-DATE-CHANGE', 'NITH', 
        'RESET DEPARTURE', 'CHNG TEST DAY', 'CHNG TST DAY', 'NOT_TESTED', 
        'EXEMPT-CH', 'testing-pause-workday', 'EXEMPT-red', 'EXEMPT-NITH', 
        'EXEMPT-access issue', 'EXEMPT-house fire', 'EXEMPT-SUPPLEMENTAL', 
        'EXEMPT-hospital', 'TRAV-EXMP', 'TRVLEXMPT', 'EXEMPT', 'EXEMPT-ISO', 
        'Exempt Did Test', 'Exemption to Change Test', 'EXEMPTION TESTING', 
        'EXEMPT-CIW', 'EXEMPT -Travel', 'EXEMPT-LOA', 'Exemption', 
        'Exemption Travel', 'EXEMPT-NAP', 
    ]
    surv_tests_sp22 = surv_tests_sp22_raw[~surv_tests_sp22_raw["cmc_test_id"].isin(cmc_test_ids_to_drop)].reset_index()
    surveilled_ids = surv_tests_sp22["emplid_id_hash"].unique()
    study_population["include"] = (study_population["employee_id_hash"].isin(surveilled_ids)) & (study_population["nap"]!=1)

    # truncate the person-days after a person's first identification date
    study_population['day_idx']=study_population['day_idx'].apply(lambda x: string_to_date(str(x)))
    study_population.loc[study_population["hd_notify_date"] == "2022-02-21 00:00:00.0000000", "hd_notify_date"] = np.nan
    for emplid in study_population['employee_id_hash'].unique():
        notify_dates = study_population[study_population["employee_id_hash"]==emplid]["hd_notify_date"].unique()
        
        if type(notify_dates[0]) == str: # str if nonempty, float(nan) if empty
            if len(notify_dates) > 1:
                notify_date = min(notify_dates)
                notify_dates.remove(notify_date)
                ind_drop_extra_dates = study_population[(study_population.employee_id_hash == emplid) &
                                        (study_population.hd_notify_date.isin(notify_dates))].index
                study_population.drop(ind_drop_extra_dates, inplace = True)
            student_history = study_population.query('employee_id_hash == @emplid')
            last_day_pos = student_history.loc[student_history[student_history['infected_on_this_day']==1].last_valid_index()]['day_idx']
            last_day = student_history.loc[student_history.tail(1).index.item()]['day_idx']   
            ind_drop_extra_records = study_population[(study_population.employee_id_hash == emplid) &
                                                        (study_population.day_idx > last_day_pos) & 
                                                        (study_population.day_idx <= last_day)].index
            study_population.drop(ind_drop_extra_records, inplace = True)
            
    study_population['class_prevalence_on_this_day'] = ''
    study_population.reset_index(drop=True, inplace=True)

    # add academic_career info, including Greek/athlete membership
    student_academic_careers = class_registrations[["EMPLOYEE_ID_STDNT_HASH", "STDNT_TERM_ACADEMIC_CAREER"]].drop_duplicates()
    student_academic_careers.rename(
        columns={
            "EMPLOYEE_ID_STDNT_HASH": "employee_id_hash",
            "STDNT_TERM_ACADEMIC_CAREER": "academic_career"
        }, 
        inplace=True
    )
    student_academic_careers.reset_index(drop=True, inplace=True)
    study_population = study_population.merge(student_academic_careers, on = "employee_id_hash")
    greek_empids = pd.read_csv('G:/Data_Peter/classroom_transmission/data/data_sp22/hashed_greek_empIDs_sp22.csv', header=None)
    greek_empids = set(greek_empids[0])
    athlete_empids = pd.read_csv('G:/Data_Peter/classroom_transmission/data/data_sp22/hashed_athlete_empIDs_sp22.csv', header=None)
    athlete_empids = set(athlete_empids[0])
    for i in range(len(study_population)):
        if study_population.loc[i, 'employee_id_hash'] in greek_empids:
            study_population.loc[i, 'academic_career'] = 'UG_G'
        elif study_population.loc[i, 'employee_id_hash'] in athlete_empids:
            study_population.loc[i, 'academic_career'] = 'UG_A'

    # save data
    study_population.to_csv("G:/Data_Peter/classroom_transmission/data/data_sp22/study_population_finalized_sp22.csv")
