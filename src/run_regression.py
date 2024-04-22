import numpy as np
import datetime as dt
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from lifelines import CoxTimeVaryingFitter


def run_cox_regression(semester='fa21', T_e=7, verbose=True):
    all_covariates = pd.read_csv(f'../data/data_{semester}/all_students_features_T_e={T_e}_finalized.csv', index_col = 0)
    df = all_covariates[['current_gender', 'academic_career','employee_id_hash','day_idx','hd_notify_date','class_positivity', 'infected_on_this_day']]
    if semester == 'fa21':
        baseline_date = dt.datetime.strptime('2021-08-26', '%Y-%m-%d').toordinal()
    elif semester == 'sp22':
        baseline_date = dt.datetime.strptime('2022-02-07', '%Y-%m-%d').toordinal()
    df['day_idx'] = df['day_idx'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').toordinal() - baseline_date)
    df.reset_index(drop = True, inplace = True)

    df_cox = df.copy()
    df_cox['day_idx'] = df_cox['day_idx'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').toordinal() - baseline_date)
    df_cox['day_idx_stop'] = df_cox['day_idx'] + 1
    df_cox['employee_id_hash'] = df_cox['employee_id_hash'].apply(lambda x: int(x, 16))
    df_cox = pd.get_dummies(df_cox, columns=['academic_career', 'current_gender'], dtype=int)
    df_cox.drop(
        columns = ['current_gender_F', 'academic_career_UG', 'hd_notify_date'], inplace=True)

    ctv = CoxTimeVaryingFitter()
    ctv.fit(df_cox, id_col='employee_id_hash', event_col='infected_on_this_day', start_col="day_idx", stop_col="day_idx_stop", show_progress = True, fit_options = {'step_size': 0.1})
    
    if verbose:
        ctv.print_summary()

    return ctv


def run_gee_logistic_regression(semester='fa21', T_e=7, verbose=True):

    all_covariates = pd.read_csv(f'../data/data_{semester}/all_students_features_T_e={T_e}_finalized.csv', index_col = 0)
    df = all_covariates[['current_gender', 'academic_career','employee_id_hash','day_idx','hd_notify_date','class_positivity', 'infected_on_this_day']]

    if semester == 'fa21':
        baseline_date = dt.datetime.strptime('2021-08-26', '%Y-%m-%d').toordinal()
    elif semester == 'sp22':
        baseline_date = dt.datetime.strptime('2022-02-07', '%Y-%m-%d').toordinal()
    df['day_idx'] = df['day_idx'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').toordinal() - baseline_date)
    df.reset_index(drop = True, inplace = True)

    fam = sm.families.Binomial()
    ind = sm.cov_struct.Exchangeable()
    mod = smf.gee(
        "infected_on_this_day ~  C(current_gender, Treatment(reference = 'F')) + C(academic_career, Treatment(reference = 'UG')) + class_positivity + C(day_idx, Treatment(reference=0))", 
        "employee_id_hash", 
        df, cov_struct=ind, family=fam)
    res = mod.fit()

    if verbose:
        print(res.summary())

    return res
    

def export_logistic_result(res):

    summary = res.params.to_frame(name='coeff')
    summary['SE'] = res.bse
    summary['p-value'] = res.pvalues
    summary["CI_lower"] = res.conf_int()[0]
    summary["CI_higher"] = res.conf_int()[1]

    return summary


def export_cox_result(ctv):
    
    summary = ctv.params_.rename_axis(None).to_frame(name="coeff")
    summary["SE"] = ctv.standard_errors_
    summary["p-value"] = ctv._compute_p_values()
    summary["CI_lower"] = ctv.confidence_intervals_.values[:,0]
    summary["CI_upper"] = ctv.confidence_intervals_.values[:,1]

    return summary