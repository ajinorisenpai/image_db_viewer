SELECT *
FROM images
WHERE path LIKE '%' || ? || '%'
ORDER BY RANDOM()
LIMIT 100;
