WITH target_folders AS (
  SELECT
    CASE
      WHEN instr(path, :folder_path) > 0 AND
           instr(substr(path, instr(path, :folder_path) + length(:folder_path)), '/') > 0
      THEN substr(
        path,
        instr(path, :folder_path) + length(:folder_path),
        instr(substr(path, instr(path, :folder_path) + length(:folder_path)), '/') - 1
      )
      ELSE substr(path, instr(path, :folder_path) + length(:folder_path))
    END AS sub_folder,
    path,
    rowid,
    RANDOM() AS random_value
  FROM
    images
  WHERE
    path LIKE '%' || :folder_path || '%'
    AND instr(path, :folder_path) > 0
    AND size_type == ?
),

image_counts AS (
  SELECT
    sub_folder,
    COUNT(*) AS image_count
  FROM
    target_folders
  GROUP BY
    sub_folder
),

random_selections AS (
  SELECT
    sub_folder,
    path,
    rowid,
    ROW_NUMBER() OVER (
      PARTITION BY sub_folder
      ORDER BY random_value
    ) AS row_num
  FROM
    target_folders
)

SELECT
  images.*,
  selected_paths.sub_folder AS folder_name,
  ic.image_count AS folder_image_count
FROM
  images
JOIN (
  SELECT
    sub_folder,
    path
  FROM
    random_selections
  WHERE
    row_num = 1
  ORDER BY
    sub_folder ASC
) AS selected_paths
ON images.path = selected_paths.path
JOIN image_counts ic
ON selected_paths.sub_folder = ic.sub_folder
