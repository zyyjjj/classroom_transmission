-- all of this credit to Jiayue
-- For each person, find records where the check in was before Dec 5 2021 and the check out was after.
-- There are some people who have several records meeting this criterion.
-- These include UG who modified their check-out data during the semester.
-- It also includes a few staff who have lived in a dorm for a long time and have updated their record several times.
-- For these people, we use the most recent record (i.e., the latest record_date).

with FA21_housing_max_record(employee_id_hash, min_record_date, max_record_date, room_type_desc, cnt) as (
select employee_id_hash, min(record_date), max(record_date), max(room_type_desc), count(*) from housing_vw
where check_in_date < '2021-12-05'
and check_out_date >= '2021-12-05'
group by employee_id_hash
),

FA21_housing_staging(employee_id_hash,room_type_desc, building) as (
select h.employee_id_hash, h.room_type_desc,
case when building like 'Low Rise%' then 'Low Rise' else 
case when building like 'High Rise%' then 'High Rise' else
case when building like 'Bethe House%' then 'Bethe House' else
case when building like 'Cook House%' then 'Cook House' else
case when building like 'Rose House%' then 'Rose House' else
case when building like '%McGraw Place' then 'McGraw Place' else
case when building like '%Wait%' then 'Wait Ave' else
case when building in ('Kay Hall', 'Court Hall', 'Bauer Hall') then 'Court-Kay-Bauer Hall' else
building
end end end end end end end end
from housing_vw h
inner join FA21_housing_max_record m on h.employee_id_hash = m.employee_id_hash and h.record_date = m.max_record_date
where h.check_in_date < '2021-12-05'
and h.check_out_date >= '2021-12-05'
),

FA21_housing(employee_id_hash,building,building_type) as (
select employee_id_hash, building, 
case when building like '%Wait%' or building = 'Prospect of Whitby' or building like '% Coop' or building = 'Watermargin' or building = 'Von Cramm Hall' or building = '660 Stewart' then 'Cooperative' else
case when building in ('Risley', 'Veteran Program House', 'Loving House', 'Akwe:kon', 'Equity & Engagement LLC', 'McLLU', 'Latino Living Center', 'Ecology House', 'Ujamaa', 'Just About Music', 'Holland International LC') then 'Program House' else
case when building in ('Court-Kay-Bauer Hall', '112 Edgemoor', 'Cascadilla Hall', 'Ganedago: Hall', 'Toni Morrison Hall', 'Low Rise', 'High Rise', 'Townhouse', 'McGraw Place', 'Schuyler House',
					'Sheldon Court', 'Toni Morrison Hall', 'Jameson Hall', 'Mews Hall', 'Mary Donlon Hall', 'Clara Dickson Hall') then 'Residence Hall' else
case when building in ('Bethe House', 'Rose House', 'Cook House', 'Keeton House', 'Becker House') then 'West Campus' else
case when building = 'Hasbrouck Apts' then 'Grad Housing' else NULL
end end end end end
from FA21_housing_staging
)

--- Useful to make sure that there are no netids that show up twice in FA21_housing.
--- This could happen if there is a netid with two records with the same record_date.
--- This returns 0 rows, as it should
-- select employee_id_hash, count(*) from FA21_housing group by employee_id_hash having count(*)>1

--- Useful for seeing how many buildings there are
--- select building, building_type, count(employee_id_hash) as num_residents from FA21_housing group by building, building_type order by count(employee_id_hash)

select employee_id_hash, building from FA21_housing
where building_type in ('Residence Hall', 'West Campus', 'Program House')

