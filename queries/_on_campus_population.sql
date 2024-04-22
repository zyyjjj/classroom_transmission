declare @dates table(day_idx datetime)
declare @start_date datetime = '2021-08-26'
declare @datefrom datetime = '2021-08-25'
declare @dateto datetime = '2021-12-07'

SET NOCOUNT ON;

while (@datefrom < @dateto)
begin
	select @datefrom = dateadd(day, 1, @datefrom)
	insert into @dates
	select @datefrom
end;

with checklist_plan as(
	select emplid_hash, plans
	from daily_checklist_fall2021_vw
),

t_students as (
	select p.employee_id_hash, p.netid_hash, p.academic_plan1, p.academic_career, p.current_gender
	from early_warn.irp_pandemic_stdnt_enrl_vw p
	left join checklist_plan c
		on p.employee_id_hash = c.emplid_hash
	where academic_term_sdescr = '2021FA'
	and p.enrolled_flag = 'Y'
		-- exclude students not subject to regular surveillance testing; criteria could be ruling out students more than once
	and charindex('QATAR', p.academic_plan1) = 0 -- not Qatar program [QATARFND, QATAR]
	and charindex('NY', p.academic_plan1) = 0 -- not NYC program [NYOR-MENG, NYMBA-MBA, NYLAW-LLM, NYEE-MENG, NYCS-MENG, NYINFO-MS, NYLAWE-LLM]
	and p.college <> 'NYC Tech' -- same as above, not NYC Tech program
	-- exclude (some) EMBA programs, non-degree programs, distance learning programs, and other programs not subject to surveillance
	and p.academic_plan1 not in ('CQEMBA-MBA', 'CTEMBA-MBA', 'WJMBA-MBA', 'CTUG-NONC', 'CT-NONC', 'LAW-NON', 'DIET-NONC', 'ENMDL-MENG', 'LEGALDL-MS', 'HUMRES-MPS', 'MATRISE-JD', 'HUMRES-MPS', 'EMBA-MBA')  
	and charindex('conti', academic_program1_ldescr) = 0 -- not continuing education program
	and p.withdraw_date is null -- not withdrawn
	-- exclude students whose `form of study` is not `ENRL` (e.g., `INAB`, `PRTU`)
	and p.form_of_study = 'ENRL'
	-- exclude students that indicated that they would be `away` in the fall 2021 checklist
	and (c.plans <> 'away' or c.plans is null)
),

t_positives as (
	select distinct r.employee_id_hash, r.hd_notify_date
	from redcap_positives_official_vw r
	left join t_students s on r.employee_id_hash = s.employee_id_hash
--	where r.fac_staff = 'N'
	where s.employee_id_hash is not null
	and r.hd_notify_date >= @start_date 
	and r.hd_notify_date <= @dateto
),



NAPs as (
	select distinct employee_id_hash
	from early_warn.redcap_positives_official_vw
	where spurious is NULL
	and cast(hd_notify_date as date) between '2021-05-28' and '2021-08-26'
),

positives_by_day as (
	select hd_notify_date, count(*) as positives_on_this_day from t_positives
	group by hd_notify_date
),

positives_by_day_full as (
	select d.day_idx, 
	isnull(p.positives_on_this_day, 0) as positives_identified_on_this_day
	from positives_by_day p
	full outer join @dates d on p.hd_notify_date = d.day_idx
),

student_features as (
-- select CONVERT(VARCHAR(1000), ts.employee_id_hash, 1) employee_id_hash, 
select ts.employee_id_hash, ts.netid_hash,
ts.academic_plan1,
ts.academic_career,
ts.current_gender,
tp.hd_notify_date from t_students ts
left join t_positives tp on ts.employee_id_hash = tp.employee_id_hash
),

all_students_features as (
select st.employee_id_hash, st.netid_hash, st.academic_plan1, st.academic_career, st.current_gender, st.hd_notify_date, p.day_idx, p.positives_identified_on_this_day,
case when datediff(day, day_idx, hd_notify_date) = 0 then 1 else 0 end as infected_on_this_day,
-- case when hd_notify_date is not null and datediff(day, hd_notify_date, day_idx) >= 7 then 1 else 0 end as previous_infection,
datediff(day, @start_date, day_idx)/7 as week_idx,
datediff(day, @start_date, day_idx)/14 as biweek_idx,
case when n.employee_id_hash is null then 0 else 1 end as nap
from student_features st
left join NAPs n on st.employee_id_hash = n.employee_id_hash
cross join positives_by_day_full p
)
--where employee_id_hash = '0xDAFE5A62C2ED7146DC420A05834847CB' -- this person was infected 9/1 and 12/1


select * from all_students_features 
--where nap = 1
order by employee_id_hash, day_idx


-- select * from t_students t left join NAPs n on t.employee_id_hash = n.employee_id_hash
-- select * from student_features t left join NAPs n on t.employee_id_hash = n.employee_id_hash