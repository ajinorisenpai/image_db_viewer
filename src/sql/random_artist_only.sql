/* 使用例:
 * 第1引数: target_column = 'artists/' または 'characters'
 * 第2引数: size_type_value = 取得したいsize_typeの値（例: 'original', 'thumbnail'等）
 */

WITH
item_counts AS (
    -- まず各アーティスト/キャラクターの出現回数を計算
    SELECT
        CASE ?1
            WHEN 'artists/' THEN artists
            WHEN 'characters' THEN characters
        END as item_name,
        COUNT(*) as count
    FROM image_relation_view
    WHERE (?2 = '' OR ?2 = 'all' OR size_type = ?2)
    GROUP BY item_name
),
random_items AS (
    -- ランダムなレコードを選択
    SELECT
        i.*,
        CASE ?1
            WHEN 'artists/' THEN i.artists
            WHEN 'characters' THEN i.characters
        END as folder_name
    FROM image_relation_view i
    WHERE (?2 = '' OR ?2 = 'all' OR i.size_type = ?2)
    AND INSTR(
        CASE ?1
            WHEN 'artists/' THEN i.artists
            WHEN 'characters' THEN i.characters
        END,
        ','
    ) = 0
    GROUP BY folder_name
    ORDER BY random()
)
-- 結果とカウントを結合
SELECT
    r.*,
    c.count as folder_image_count
FROM random_items r
LEFT JOIN item_counts c ON r.folder_name = c.item_name
ORDER BY folder_name;  -- folder_nameでソート
