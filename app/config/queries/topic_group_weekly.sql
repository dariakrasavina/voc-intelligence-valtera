-- Weekly topic mentions per topic group
SELECT CAST(date_trunc('WEEK', interaction_date) AS DATE) AS week,
       CAST(SUM(CASE WHEN parent_topic = 'Vehicle Safety' THEN interactions ELSE 0 END) AS INT) AS vehicle_safety,
       CAST(SUM(CASE WHEN parent_topic = 'Battery & Charging' THEN interactions ELSE 0 END) AS INT) AS battery_charging,
       CAST(SUM(CASE WHEN parent_topic = 'Software & Connectivity' THEN interactions ELSE 0 END) AS INT) AS software,
       CAST(SUM(CASE WHEN parent_topic = 'Service & Warranty' THEN interactions ELSE 0 END) AS INT) AS service_warranty,
       CAST(SUM(CASE WHEN parent_topic = 'Dealer & Sales Experience' THEN interactions ELSE 0 END) AS INT) AS dealer,
       CAST(SUM(CASE WHEN parent_topic = 'Billing & Financing' THEN interactions ELSE 0 END) AS INT) AS billing,
       CAST(SUM(CASE WHEN parent_topic = 'Positive Feedback' THEN interactions ELSE 0 END) AS INT) AS praise
FROM daria_krasavina.voc_valtera.gold_topic_daily GROUP BY 1 ORDER BY 1
