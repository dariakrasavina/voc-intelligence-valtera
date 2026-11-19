-- Precision / recall / F1 vs. ground truth for each classification method
SELECT method, precision, recall, f1, CAST(tp AS INT) AS tp, CAST(fp AS INT) AS fp, CAST(fn AS INT) AS fn
FROM daria_krasavina.voc_valtera.eval_classification_metrics ORDER BY f1 DESC
