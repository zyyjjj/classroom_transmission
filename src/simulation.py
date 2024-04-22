import numpy as np
import datetime as dt
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from lifelines import CoxTimeVaryingFitter


class Simulation():

    """
    Run extended Cox regression and logistic regression on simulated datasets
    to investigate how the trends in baseline hazard and covariates affect
    inference. Based on Spring 2022 study period, length 14 days.
    """

    def __init__(self, student_features):

        self.df = student_features[['current_gender','academic_career','employee_id_hash','day_idx', 'week_idx', 'class_positivity', 'campus_positivity', 'infected_on_this_day']]
                   
        baseline_date = dt.datetime.strptime('2022-02-07', '%Y-%m-%d').toordinal()
        self.df['day_idx'] = self.df['day_idx'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').toordinal() - baseline_date)
        self.df['day_idx_stop'] = self.df['day_idx'] + 1

        self.campus_positivity = self.df[self.df["employee_id_hash"]=="0x0001CEED0A3584312155FD3B695D2EB6"][["campus_positivity"]]

        self.students = self.df[["employee_id_hash", "current_gender", "academic_career"]].drop_duplicates().reset_index(drop=True)

        self.df_stats = {
            "byday": self.df[["class_positivity","campus_positivity","day_idx"]].groupby(["day_idx"]).aggregate(["mean","sem","std","median"]),
            "aggregate": self.df.describe()
        }


    def fit_logistic(self, data):

        data = data.astype({"infected_on_this_day": int})

        fam = sm.families.Binomial()
        ind = sm.cov_struct.Exchangeable()
        mod = smf.gee(
            "infected_on_this_day ~ C(current_gender, Treatment(reference = 'F')) + C(academic_career, Treatment(reference = 'UG')) + class_positivity + campus_positivity + C(week_idx, Treatment(reference=0))", 
            "employee_id_hash", 
            data, 
            cov_struct=ind, family=fam)
        logistic_res = mod.fit()
        logistic_res.summary()

        return logistic_res 


    def fit_logistic_on_original_data(self):
        return self.fit_logistic(self.df)
    

    def process_data_for_cox(self, data):
        data = data.astype(
            {
                "day_idx": int,
                "day_idx_stop": int,
            }
        )
        if "infected_on_this_day" in data.columns:
            data = data.astype({"infected_on_this_day": int})

        data = pd.get_dummies(data, columns=['current_gender','academic_career'], dtype=int)
        data = data.drop(columns = ['current_gender_F','campus_positivity', 'academic_career_UG'])
        if "week_idx" in data.columns:
            data = data.drop(columns=["week_idx"])

        return data
    
    def process_simulated_data_for_cox(self, data):
        data = data.astype(
            {
                "day_idx": int,
                "day_idx_stop": int,
            }
        )
        if data.iloc[0]["current_gender"] == "M":
            data["current_gender_M"] = 1
        else:
            data["current_gender_M"] = 0
        
        academic_career_vals = ["GM", "GR", "LA", "UG_A", "UG_G", "VM"]

        for ac in academic_career_vals:
            if data.iloc[0]["academic_career"] == ac:
                data["academic_career_"+ac] = 1
            else:
                data["academic_career_"+ac] = 0
        
        data = data.drop(columns = ["current_gender", "academic_career", "campus_positivity"])
        if "week_idx" in data.columns:
            data = data.drop(columns=["week_idx"])

        return data


    def fit_cox(self, data, id_col = "employee_id_hash"):

        data_cox = self.process_data_for_cox(data)

        ctv = CoxTimeVaryingFitter()
        ctv.fit(
            data_cox, 
            id_col=id_col, 
            event_col="infected_on_this_day", 
            start_col="day_idx", stop_col="day_idx_stop", 
            show_progress = False, 
            fit_options = {'step_size': 0.1}
        )

        return ctv


    def fit_cox_on_original_data(self):

        return self.fit_cox(self.df)


    def generate_event_prob(self, prob_seq):
        n = len(prob_seq)
        res = [prob_seq[0]]
        partial_product = 1-prob_seq[0]
        for p in prob_seq[1:]:
            res.append(partial_product * p)
            partial_product *= (1-p)
        res.append(partial_product)
        return res
    

    def generate_baseline_hazard(self, baseline_hazard_options):
        """
        Compute discrete-time baseline hazard function so that survival time 
        follows a Weibull distribution, parameterized by scale and shape. 
        When shape=1, hazard is constant and we recover the Exponential.
        https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3546387/
        https://onlinelibrary.wiley.com/doi/abs/10.1002/sim.2059 
        """

        scale = baseline_hazard_options.get("scale", 0.01)
        shape = baseline_hazard_options.get("shape", 1)
        num_days = baseline_hazard_options.get("num_days", 14)
        
        res = []
        for t in range(1, num_days+1):
            res.append(scale*shape*t**(shape-1))
        
        return res


    def generate_simulated_data(
        self, batch_idx_range = [0,1,2], 
        simulate_from = "logistic", 
        simulate_longitudinal_features = ["class_positivity"], # "campus_positivity"
        simulate_crosssec_features = [], # "current_gender", "academic_career"
        baseline_hazard_options = {}, 
        feature_options = {}
    ):
        
        retain_crosssec_features = ["employee_id_hash", "current_gender", "academic_career"]
        for scf in simulate_crosssec_features:
            retain_crosssec_features.remove(scf)

        base_students = self.df[retain_crosssec_features].drop_duplicates().reset_index(drop=True)

        if simulate_from == "logistic":
            predictor = self.fit_logistic_on_original_data()
        elif simulate_from == "cox":
            # predict partial hazard from model; specify baseline hazard ourselves
            predictor = self.fit_cox_on_original_data() # TODO: allow predefined effects
            baseline_hazard = self.generate_baseline_hazard(baseline_hazard_options)
        else:
            raise NotImplementedError("Specified simulation method has not been implemented")

        if "campus_positivity" in simulate_longitudinal_features:
            temporal_option = feature_options.get("campus_positivity", "byday")
            sim_campus_positivity = np.clip(
                    np.random.normal(
                        self.df_stats[temporal_option]["campus_positivity"]["mean"],
                        self.df_stats[temporal_option]["campus_positivity"]["std"],
                    ), 0, 200)
        else:
            sim_campus_positivity = self.campus_positivity.values

        simulated_data_by_batch = {}

        sim_employee_id = 0

        for batch_idx in batch_idx_range:

            np.random.seed(batch_idx)
            
            simulated_data = pd.DataFrame(
                [], 
                columns=[
                    "employee_id_hash", "current_gender", "academic_career", 
                    "class_positivity", "campus_positivity", "day_idx", "day_idx_stop",
                    "infected_on_this_day",
                ]
            )

            for idx, row in base_students.iterrows():

                df_tmp = row.to_frame().T
                df_tmp = df_tmp.iloc[np.arange(len(df_tmp)).repeat(14)]

                df_tmp["employee_id_hash"] = sim_employee_id

                if "class_positivity" in simulate_longitudinal_features:
                    temporal_option = feature_options.get("class_positivity", "byday")
                    sim_cp = np.clip(
                        np.random.normal( # TODO: consider more skewed distributions; try constant mean over time
                            self.df_stats[temporal_option]["class_positivity"]["mean"],
                            self.df_stats[temporal_option]["class_positivity"]["std"],
                        ), 0, 10)
                    df_tmp["class_positivity"] = sim_cp
                else:
                    # use original features in the data
                    df_tmp["class_positivity"] = self.df[self.df["employee_id_hash"]==row["employee_id_hash"]]["class_positivity"].values

                df_tmp["campus_positivity"] = sim_campus_positivity

                df_tmp["day_idx"] = np.arange(14)
                df_tmp["day_idx_stop"] = np.arange(1,15)

                if simulate_from == "logistic":
                    predicted_prob = predictor.predict(df_tmp).values
                elif simulate_from == "cox":
                    df_tmp_cox = self.process_simulated_data_for_cox(df_tmp)
                    predicted_partial_hazard = predictor.predict_partial_hazard(df_tmp_cox)
                    predicted_prob = baseline_hazard * predicted_partial_hazard

                event_prob_vals = self.generate_event_prob(predicted_prob)
                event_time = np.random.multinomial(1, event_prob_vals)

                if event_time[-1]==1: #censored
                    df_tmp["infected_on_this_day"]=0
                else:
                    survival_length = np.argwhere(event_time==1)[0][0]+1
                    df_tmp = df_tmp[:survival_length]
                    df_tmp["infected_on_this_day"] = event_time[:survival_length]
                    print(f"positive, identified on day {survival_length}")

                simulated_data = pd.concat([simulated_data, df_tmp]).reset_index(drop=True)
                sim_employee_id += 1
            
            simulated_data_by_batch[batch_idx] = simulated_data
        
        return simulated_data_by_batch
