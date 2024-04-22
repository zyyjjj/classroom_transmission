select *
from daily_checkin_surveillance_vw d
where updated_at_date between '2022-02-07' and '2022-02-20 23:59'
and missed_test is null
and cmc_test_id = 'Booster validated'