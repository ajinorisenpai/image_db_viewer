WITH character_folders AS (
  SELECT
    substr(
      path,
      instr(path, 'character/') + 10, -- 'character/'の長さは10
      instr(substr(path, instr(path, 'character/') + 10), '/') - 1
    ) AS character_folder,
    path,
    rowid,
    RANDOM() AS random_value
  FROM
    images
  WHERE
    path LIKE '%character/%'
    AND detail LIKE ?
    AND detail LIKE ?
),

image_counts AS (
  SELECT
    character_folder,
    COUNT(*) AS image_count
  FROM
    character_folders
  GROUP BY
    character_folder
),

random_selections AS (
  SELECT
    character_folder,
    path,
    rowid,
    ROW_NUMBER() OVER (
      PARTITION BY character_folder
      ORDER BY random_value
    ) AS row_num
  FROM
    character_folders
)

SELECT
  images.*,
  ic.image_count AS character_folder_image_count
FROM
  images
JOIN (
  SELECT
    character_folder,
    path
  FROM
    random_selections
  WHERE
    row_num = 1
  ORDER BY
    character_folder ASC
) AS selected_paths
ON images.path = selected_paths.path
JOIN image_counts ic
ON selected_paths.character_folder = ic.character_folder
