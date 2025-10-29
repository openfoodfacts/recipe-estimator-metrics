# Known Percentage Input Sets

The known-percent input sets are where all top level ingredient percentages are known and add up to 100.

The full list of products was obtained with this SQL in off-query:

```sql
copy (select 
(select count(*) from product_ingredient pi2 where pi2.product_id = pi.product_id and pi2.parent_sequence is null) ingredient_count,
sequence::int,
percent::float,
(select sum(percent::float) from product_ingredient pi2 where pi2.product_id = pi.product_id and pi2.parent_sequence is null) total_percent,
code
from product_ingredient pi
join product p on p.id = pi.product_id
where parent_sequence is null
and "percent" is not null
and (select count(*) from product_ingredient pi2 where pi2.product_id = pi.product_id and pi2.parent_sequence is null) > 1
and not exists (select * from product_ingredient pi2 where pi2.product_id = pi.product_id and pi2.parent_sequence is null and pi2."percent" is null)
and (select sum(percent::float) from product_ingredient pi2 where pi2.product_id = pi.product_id and pi2.parent_sequence is null) between 95 and 105)
to '/tmp/ingredient_stats.csv' with (FORMAT CSV, HEADER);
```

The script `add_product_codes_to_test_set.py` fetches the products and filters only those with nutrients and more than one country.

The results were split into sub-folders by country. The `rename.sh` script moved these into separate parent-level folders.

So far only united-kingdom and france have been cleaned with percent estimates added.
