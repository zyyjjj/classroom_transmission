-- select distinct cmc_test_id
--select cast(updated_at_date as date), count(*)
select *
from daily_checkin_surveillance_vw d
where updated_at_date between '2021-08-26' and '2021-12-07 23:59'
and missed_test is null
--and cmc_test_id = 'TRAVEL'
--group by cast(updated_at_date as date)
--order by cast(updated_at_date as date)
--and (isnumeric(cmc_test_id)=0 and cmc_test_id is not null and cmc_test_id = 'SDS Accommodation')


-- include: travel, ch test, ch-test, dc-red supplemental, test, 
-- exclude: travel-exmp, trvlexmpt, exempt, nap, nith, not here yet, not_tested
-- not sure: adj, PEOPLESOFT_FEEDRM (1), WORKDAY_FEEDRM (175), RESET DEPARTURE (17), SDS Accommodation (1)